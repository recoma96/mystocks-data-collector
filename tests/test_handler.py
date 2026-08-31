from contextlib import contextmanager
from datetime import datetime
from unittest.mock import MagicMock, patch

from mystocks_data_collector.handler import generate_view

# 일요일 - 당일 포트폴리오 데이터는 없지만(휴장) 전날(토요일) 체결 내역은 반영돼야 하는 시나리오
NOW = datetime(2026, 8, 23)


@contextmanager
def _fake_duckdb_conn():
    yield MagicMock()


def test_generate_view_runs_transactions_view_even_when_position_view_returns_none():
    with patch("mystocks_data_collector.handler.S3Storage"), \
         patch("mystocks_data_collector.handler.connect_s3_duckdb", _fake_duckdb_conn), \
         patch("mystocks_data_collector.handler.upload_position_view", return_value=None), \
         patch("mystocks_data_collector.handler.upload_histories_view") as mock_histories, \
         patch("mystocks_data_collector.handler.upload_transactions_view") as mock_transactions:
        generate_view(NOW)

    mock_transactions.assert_called_once()
    mock_histories.assert_not_called()


def test_generate_view_runs_histories_and_transactions_when_position_view_succeeds():
    portfolio_data = {"portfolio": {"totalValue": 10000}, "stocks": []}
    portfolio_id = "portfolio-1"

    with patch("mystocks_data_collector.handler.S3Storage"), \
         patch("mystocks_data_collector.handler.connect_s3_duckdb", _fake_duckdb_conn), \
         patch("mystocks_data_collector.handler.upload_position_view", return_value=(portfolio_data, portfolio_id)), \
         patch("mystocks_data_collector.handler.upload_histories_view") as mock_histories, \
         patch("mystocks_data_collector.handler.upload_transactions_view") as mock_transactions:
        generate_view(NOW)

    mock_transactions.assert_called_once()
    mock_histories.assert_called_once()
    args = mock_histories.call_args.args
    assert args[2] == portfolio_data
    assert args[3] == portfolio_id


def test_generate_view_runs_transactions_view_even_when_position_view_raises():
    """S3 파일 부재 등으로 upload_position_view가 예외를 던져도 upload_transactions_view는
    실행돼야 한다. 
    TODO 아직 예외처리가 구현되지 않아 현재는 실패하는 게 정상 - 다음 작업에서 해결 예정.
    """
    with patch("mystocks_data_collector.handler.S3Storage"), \
         patch("mystocks_data_collector.handler.connect_s3_duckdb", _fake_duckdb_conn), \
         patch("mystocks_data_collector.handler.upload_position_view", side_effect=Exception("S3 file not found")), \
         patch("mystocks_data_collector.handler.upload_histories_view"), \
         patch("mystocks_data_collector.handler.upload_transactions_view") as mock_transactions:
        generate_view(NOW)

    mock_transactions.assert_called_once()
