from datetime import datetime
from unittest.mock import MagicMock

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
    conn = MagicMock()
    conn.execute.return_value.fetchone.return_value = None

    fetch_latest_portfolio_snapshot(conn, datetime(2026, 8, 29))

    executed_sql = conn.execute.call_args[0][0]
    assert "date=20260829/data.parquet" in executed_sql


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
