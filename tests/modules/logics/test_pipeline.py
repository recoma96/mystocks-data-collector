import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from mystocks_data_collector.modules.logics.pipeline import upload_histories_view
from mystocks_data_collector.modules.storage import S3Storage

VIEW_KEY_FORMAT = "view/histories/{}.json"
NOW = datetime(2026, 8, 20)


def _make_mock_s3(existing: dict) -> MagicMock:
    """existing: {"YYYY-MM-DD": data_dict} 형태로 존재하는 날짜와 그 내용을 지정. 오늘자는 기본적으로 미존재."""
    mock_s3 = MagicMock(spec=S3Storage)
    existing_keys = {VIEW_KEY_FORMAT.format(d): data for d, data in existing.items()}

    mock_s3.exists.side_effect = lambda key: key in existing_keys
    mock_s3.get_object.side_effect = (
        lambda key: json.dumps(existing_keys[key]).encode("utf-8") if key in existing_keys else None
    )
    return mock_s3


def _portfolio_data(*, total_value, profit_amount, cash_balance, positions_market_value, sgov_value=0) -> dict:
    return {
        "stocks": [{"ticker": "SGOV", "marketValueExcludingFees": sgov_value}] if sgov_value else [],
        "portfolio": {
            "totalValue": total_value,
            "profitAmountExcludingFees": profit_amount,
            "cashBalance": cash_balance,
            "positionsMarketValue": positions_market_value,
        },
    }


def _uploaded_data(mock_s3: MagicMock) -> dict:
    key, body = mock_s3.put_object.call_args.args
    assert key == VIEW_KEY_FORMAT.format("2026-08-20")
    return json.loads(body)


def test_upload_histories_view_skips_when_today_already_exists():
    mock_s3 = _make_mock_s3({"2026-08-20": {"histories": []}})
    duck_conn = MagicMock()

    upload_histories_view(mock_s3, duck_conn, _portfolio_data(
        total_value=1, profit_amount=0, cash_balance=1, positions_market_value=0,
    ), "portfolio-1", NOW)

    mock_s3.put_object.assert_not_called()


def test_upload_histories_view_accumulates_over_gap_without_resetting():
    previous_view = {
        "myPortfolio": {},
        "histories": [
            {"date": "2026-08-14", "cash": 1000, "sgov": 0, "investments": 5000, "profitRateExcludingFees": 3.0},
            {"date": "2026-08-15", "cash": 1000, "sgov": 0, "investments": 5100, "profitRateExcludingFees": 3.5},
        ],
        "benchMarks": [
            {
                "ticker": "VOO",
                "name": "S&P500",
                "histories": [
                    {"date": "2026-08-14", "price": 500.0, "profitRate": 0},
                    {"date": "2026-08-15", "price": 505.0, "profitRate": 1.0},
                ],
            }
        ],
    }
    # 어제/그제(2026-08-18, 19)는 없고 3일 전(2026-08-17)에만 존재 - 주말/휴장일 갭 상황
    mock_s3 = _make_mock_s3({"2026-08-17": previous_view})
    duck_conn = MagicMock()

    with patch(
        "mystocks_data_collector.modules.logics.pipeline.fetch_latest_benchmark_price_snapshot",
        return_value=[{"ticker": "VOO", "current_price": 510.0}],
    ):
        upload_histories_view(mock_s3, duck_conn, _portfolio_data(
            total_value=10500, profit_amount=500, cash_balance=1000, positions_market_value=9500,
        ), "portfolio-1", NOW)

    uploaded = _uploaded_data(mock_s3)

    # 기존 histories 2건이 초기화되지 않고 그대로 남아있고, 오늘자 1건만 추가돼야 한다
    assert len(uploaded["histories"]) == 3
    assert uploaded["histories"][:2] == previous_view["histories"]
    assert uploaded["histories"][2]["date"] == "2026-08-20"

    # benchMarks도 기존 2건의 히스토리가 유지된 채 오늘자 1건만 추가돼야 한다
    assert len(uploaded["benchMarks"]) == 1
    voo = uploaded["benchMarks"][0]
    assert voo["histories"][:2] == previous_view["benchMarks"][0]["histories"]
    assert len(voo["histories"]) == 3
    assert voo["histories"][2]["date"] == "2026-08-20"


def test_upload_histories_view_starts_fresh_when_no_previous_view_within_window(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("PEER_STOCKS_TICKER", "QQQ")
    monkeypatch.setenv("PEER_STOCKS_NAME", "나스닥100추종")

    mock_s3 = _make_mock_s3({})  # 15일 이내 아무 파일도 없음
    duck_conn = MagicMock()

    with patch(
        "mystocks_data_collector.modules.logics.pipeline.fetch_latest_benchmark_price_snapshot",
        return_value=[{"ticker": "QQQ", "current_price": 400.0}],
    ):
        upload_histories_view(mock_s3, duck_conn, _portfolio_data(
            total_value=10000, profit_amount=500, cash_balance=2000, positions_market_value=8000,
        ), "portfolio-1", NOW)

    uploaded = _uploaded_data(mock_s3)

    assert len(uploaded["histories"]) == 1
    assert uploaded["histories"][0]["date"] == "2026-08-20"

    assert len(uploaded["benchMarks"]) == 1
    assert uploaded["benchMarks"][0]["ticker"] == "QQQ"
    assert uploaded["benchMarks"][0]["histories"] == [{"date": "2026-08-20", "price": 400.0, "profitRate": 0}]


def test_upload_histories_view_adds_new_benchmark_ticker_not_in_previous_data(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("PEER_STOCKS_TICKER", "VOO,QLD")
    monkeypatch.setenv("PEER_STOCKS_NAME", "S&P500추종,나스닥100추종2배")

    previous_view = {
        "myPortfolio": {},
        "histories": [
            {"date": "2026-08-19", "cash": 1000, "sgov": 0, "investments": 5000, "profitRateExcludingFees": 3.0},
        ],
        "benchMarks": [
            {
                "ticker": "VOO",
                "name": "S&P500추종",
                "histories": [{"date": "2026-08-19", "price": 500.0, "profitRate": 0}],
            }
        ],
    }
    mock_s3 = _make_mock_s3({"2026-08-19": previous_view})
    duck_conn = MagicMock()

    with patch(
        "mystocks_data_collector.modules.logics.pipeline.fetch_latest_benchmark_price_snapshot",
        return_value=[{"ticker": "VOO", "current_price": 510.0}, {"ticker": "QLD", "current_price": 80.0}],
    ):
        upload_histories_view(mock_s3, duck_conn, _portfolio_data(
            total_value=10500, profit_amount=500, cash_balance=1000, positions_market_value=9500,
        ), "portfolio-1", NOW)

    uploaded = _uploaded_data(mock_s3)

    tickers = {b["ticker"] for b in uploaded["benchMarks"]}
    assert tickers == {"VOO", "QLD"}

    voo = next(b for b in uploaded["benchMarks"] if b["ticker"] == "VOO")
    assert len(voo["histories"]) == 2  # 기존 1건 + 오늘 1건

    qld = next(b for b in uploaded["benchMarks"] if b["ticker"] == "QLD")
    assert qld["histories"] == [{"date": "2026-08-20", "price": 80.0, "profitRate": 0}]
