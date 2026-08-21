import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from mystocks_data_collector.config import Config
from mystocks_data_collector.modules.logics.storage import fetch_latest_view_before
from mystocks_data_collector.modules.storage import S3Storage

KEY_FORMAT = "view/histories/{}.json"
NOW = datetime(2026, 8, 20)


def _make_mock_s3(existing: dict) -> MagicMock:
    """existing: {"YYYY-MM-DD": data_dict} 형태로 존재하는 날짜와 그 내용을 지정"""
    mock_s3 = MagicMock(spec=S3Storage)
    existing_keys = {KEY_FORMAT.format(d): data for d, data in existing.items()}

    mock_s3.exists.side_effect = lambda key: key in existing_keys
    mock_s3.get_object.side_effect = (
        lambda key: json.dumps(existing_keys[key]).encode("utf-8") if key in existing_keys else None
    )
    return mock_s3


def test_fetch_latest_view_before_returns_yesterday_when_exists():
    mock_s3 = _make_mock_s3({"2026-08-19": {"value": "yesterday"}})

    result = fetch_latest_view_before(mock_s3, KEY_FORMAT, NOW)

    assert result == {"value": "yesterday"}


def test_fetch_latest_view_before_skips_gap_and_finds_older_file():
    mock_s3 = _make_mock_s3({
        # 1, 2일 전은 없음 (갭)
        "2026-08-17": {"value": "3-days-ago"},  # 가장 최근 후보
        "2026-08-16": {"value": "4-days-ago"},
        "2026-08-15": {"value": "5-days-ago"},
    })

    result = fetch_latest_view_before(mock_s3, KEY_FORMAT, NOW)

    # 과거 후보가 여러 개 있어도 그중 가장 최근(3일 전) 것을 가져와야 한다
    assert result == {"value": "3-days-ago"}
    # 3일 전에서 찾았으면 그보다 더 먼 4일 전, 5일 전은 아예 확인하지 않아야 한다
    assert mock_s3.exists.call_count == 3
    assert mock_s3.get_object.call_count == 1


def test_fetch_latest_view_before_returns_none_when_nothing_within_window():
    mock_s3 = _make_mock_s3({})

    result = fetch_latest_view_before(mock_s3, KEY_FORMAT, NOW)

    assert result is None
    assert mock_s3.exists.call_count == Config.MAX_VIEW_LOOKBACK_DAYS


def test_fetch_latest_view_before_does_not_look_beyond_max_lookback_days():
    too_old_date = NOW - timedelta(days=Config.MAX_VIEW_LOOKBACK_DAYS + 1)
    mock_s3 = _make_mock_s3({too_old_date.strftime("%Y-%m-%d"): {"value": "too-old"}})

    result = fetch_latest_view_before(mock_s3, KEY_FORMAT, NOW)

    assert result is None
