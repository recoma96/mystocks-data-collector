from datetime import datetime
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

import duckdb
import pytest

from mystocks_data_collector.modules.duckdb_client import (
    fetch_latest_benchmark_price_snapshot,
    fetch_latest_portfolio_snapshot,
    fetch_positions_snapshot,
    fetch_transactions_single_day_snapshot,
)


def _mock_conn_with_result(columns: list, rows: list) -> MagicMock:
    conn = MagicMock()
    result = MagicMock()
    result.description = [(col,) for col in columns]
    result.fetchall.return_value = rows
    conn.execute.return_value = result
    return conn


def test_fetch_transactions_single_day_snapshot_returns_rows_on_success(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("S3_BUCKET", "test-bucket")
    conn = _mock_conn_with_result(
        ["type", "ticker", "quantity", "amount", "filledAt"],
        [("BUY", "AAPL", 10, 1785.0, "2026-08-29 10:00:00")],
    )

    rows = fetch_transactions_single_day_snapshot(conn, datetime(2026, 8, 29))

    assert rows == [{
        "type": "BUY",
        "ticker": "AAPL",
        "quantity": 10,
        "amount": 1785.0,
        "filledAt": "2026-08-29 10:00:00",
    }]

    # datetime -> YYYYmmdd 변환이 실제로 S3 경로에 반영됐는지 확인
    executed_sql = conn.execute.call_args[0][0]
    assert "date=20260829/data.parquet" in executed_sql


def test_fetch_transactions_single_day_snapshot_returns_default_on_404(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("S3_BUCKET", "test-bucket")
    conn = MagicMock()
    conn.execute.side_effect = duckdb.HTTPException(
        "HTTP Error: HTTP GET error reading "
        "'s3://mystocks-prod/data/transactions/date=20260830/data.parquet' "
        "in region 'ap-northeast-2' (HTTP 404 Not Found)"
    )

    result = fetch_transactions_single_day_snapshot(conn, datetime(2026, 8, 30))

    # fetch_transactions_single_day_snapshot는 @_duckdb_file_not_found_exception(default=[])로
    # 선언돼 있어, 404일 때 빈 목록을 반환한다.
    assert result == []


def test_fetch_transactions_single_day_snapshot_reraises_non_404_http_errors(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("S3_BUCKET", "test-bucket")
    conn = MagicMock()
    conn.execute.side_effect = duckdb.HTTPException(
        "HTTP Error: HTTP GET error reading "
        "'s3://mystocks-prod/data/transactions/date=20260830/data.parquet' "
        "in region 'ap-northeast-2' (HTTP 403 Forbidden)"
    )

    with pytest.raises(duckdb.HTTPException):
        fetch_transactions_single_day_snapshot(conn, datetime(2026, 8, 30))


def test_fetch_latest_portfolio_snapshot_queries_correct_date_partition(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("S3_BUCKET", "test-bucket")
    conn = _mock_conn_with_result([], [])

    fetch_latest_portfolio_snapshot(conn, datetime(2026, 8, 29))

    executed_sql = conn.execute.call_args[0][0]
    assert "date=20260829/data.parquet" in executed_sql


def test_fetch_latest_portfolio_snapshot_binds_actual_market_close(monkeypatch: pytest.MonkeyPatch):
    """오전 5시 고정값이 아니라, 그날 실제 NYSE 마감 시각(nyse_trading_hours_kst)을 WHERE 절의
    바인딩 파라미터로 넘겨야 한다. 2026-01-20(겨울/EST)의 마감은 KST 2026-01-21 06:00이다.
    """
    monkeypatch.setenv("S3_BUCKET", "test-bucket")
    conn = _mock_conn_with_result([], [])

    fetch_latest_portfolio_snapshot(conn, datetime(2026, 1, 21))

    executed_sql, params = conn.execute.call_args[0]
    assert "WHERE log_date >= ?" in executed_sql
    assert params == [datetime(2026, 1, 21, 6, 0, 0, tzinfo=ZoneInfo("Asia/Seoul"))]


def test_fetch_latest_portfolio_snapshot_binds_actual_market_close_during_dst(monkeypatch: pytest.MonkeyPatch):
    """서머타임(EDT) 적용 기간에도 마감 시각이 올바르게 바인딩되는지 확인한다.
    2026-07-02(여름/EDT)의 마감은 KST 2026-07-03 05:00이다.
    """
    monkeypatch.setenv("S3_BUCKET", "test-bucket")
    conn = _mock_conn_with_result([], [])

    fetch_latest_portfolio_snapshot(conn, datetime(2026, 7, 3))

    executed_sql, params = conn.execute.call_args[0]
    assert "WHERE log_date >= ?" in executed_sql
    assert params == [datetime(2026, 7, 3, 5, 0, 0, tzinfo=ZoneInfo("Asia/Seoul"))]


def test_fetch_latest_portfolio_snapshot_returns_none_when_no_trading_session(monkeypatch: pytest.MonkeyPatch):
    """date가 속한 거래일 자체가 휴장일이면, DB 조회 없이 바로 None을 반환해야 한다.
    2026-01-25(일요일) 03:00은 (date - 9h) 기준 거래일이 토요일(2026-01-24)이라 장이 없다.
    """
    monkeypatch.setenv("S3_BUCKET", "test-bucket")
    conn = MagicMock()

    result = fetch_latest_portfolio_snapshot(conn, datetime(2026, 1, 25, 3, 0, 0))

    assert result is None
    conn.execute.assert_not_called()


def test_fetch_positions_snapshot_queries_correct_date_partition(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("S3_BUCKET", "test-bucket")
    conn = _mock_conn_with_result([], [])

    fetch_positions_snapshot(conn, "portfolio-1", datetime(2026, 8, 29))

    executed_sql = conn.execute.call_args[0][0]
    assert "date=20260829/data.parquet" in executed_sql


def test_fetch_latest_benchmark_price_snapshot_queries_correct_date_partition(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("S3_BUCKET", "test-bucket")
    conn = _mock_conn_with_result([], [])

    fetch_latest_benchmark_price_snapshot(conn, "portfolio-1", datetime(2026, 8, 29))

    executed_sql = conn.execute.call_args[0][0]
    assert "date=20260829/data.parquet" in executed_sql
