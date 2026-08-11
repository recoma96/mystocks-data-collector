import io
from datetime import date
from unittest.mock import MagicMock

import pandas as pd

from mystocks_data_collector.modules.logics.upload import DataUpdater
from mystocks_data_collector.modules.storage import S3Storage
from mystocks_data_collector.modules.types import Transaction, TransactionType
from mystocks_data_collector.modules.utils import now_korea


def _make_updater() -> tuple[DataUpdater, MagicMock]:
    mock_s3 = MagicMock(spec=S3Storage)
    return DataUpdater(mock_s3), mock_s3


def _uploaded_df(mock_s3: MagicMock) -> pd.DataFrame:
    key, body = mock_s3.put_bytes.call_args.args
    return pd.read_parquet(io.BytesIO(body), engine="pyarrow")


def _sample_transaction() -> Transaction:
    return Transaction(
        id="tx-1",
        order_id="order-1",
        ticker="AAPL",
        type=TransactionType.BUY,
        order_amount=1785.0,
        order_quantity=10,
        filled_amount=1785.0,
        avg_price=178.5,
        filled_at=now_korea(),
        log_date=now_korea(),
    )


def test_update_topic_skips_when_no_data():
    updater, mock_s3 = _make_updater()

    updater.update_topic("positions", [], date(2026, 8, 12))

    mock_s3.put_bytes.assert_not_called()


def test_update_topic_creates_new_file_when_none_exists():
    updater, mock_s3 = _make_updater()
    mock_s3.get_object.return_value = None

    updater.update_topic("positions", [{"ticker": "AAPL", "price": 178.5}], date(2026, 8, 12))

    df = _uploaded_df(mock_s3)
    assert df.to_dict("records") == [{"ticker": "AAPL", "price": 178.5}]


def test_update_topic_accumulates_onto_existing_file():
    updater, mock_s3 = _make_updater()
    existing_df = pd.DataFrame([{"ticker": "AAPL", "price": 178.5}])
    mock_s3.get_object.return_value = updater._pandas_to_bytes(existing_df)

    updater.update_topic("positions", [{"ticker": "GOOG", "price": 141.2}], date(2026, 8, 12))

    df = _uploaded_df(mock_s3)
    assert df.to_dict("records") == [
        {"ticker": "AAPL", "price": 178.5},
        {"ticker": "GOOG", "price": 141.2},
    ]


def test_update_transaction_skips_when_yesterday_already_uploaded():
    updater, mock_s3 = _make_updater()
    mock_s3.exists.return_value = True

    updater.update_transaction([_sample_transaction()], date(2026, 8, 12))

    mock_s3.put_bytes.assert_not_called()


def test_update_transaction_uploads_when_not_yet_uploaded():
    updater, mock_s3 = _make_updater()
    mock_s3.exists.return_value = False

    updater.update_transaction([_sample_transaction()], date(2026, 8, 12))

    key, _ = mock_s3.put_bytes.call_args.args
    assert key == "data/transactions/date=20260811/data.parquet"


def test_pandas_bytes_roundtrip():
    updater, _ = _make_updater()
    df = pd.DataFrame([{"a": 1, "b": "x"}, {"a": 2, "b": "y"}])

    restored = updater._bytes_to_pandas(updater._pandas_to_bytes(df))

    pd.testing.assert_frame_equal(df, restored)