from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from mystocks_data_collector.modules.utils import is_end_of_investing_time, is_us_trading_session

KST = ZoneInfo("Asia/Seoul")


@pytest.mark.parametrize(
    ("when", "expected"),
    [
        pytest.param(datetime(2026, 1, 5, 10, 0, tzinfo=KST), True, id="평일 오전"),
        pytest.param(datetime(2026, 1, 1, 10, 0, tzinfo=KST), False, id="신정(미국 휴장일)"),
        pytest.param(datetime(2026, 1, 3, 10, 0, tzinfo=KST), False, id="토요일"),
        pytest.param(datetime(2026, 1, 5, 3, 0, tzinfo=KST), False, id="월요일 새벽 3시(전날=일요일 세션)"),
        pytest.param(datetime(2026, 1, 5, 8, 59, 59, tzinfo=KST), False, id="경계값 08:59:59(전날 세션)"),
        pytest.param(datetime(2026, 1, 5, 9, 0, 0, tzinfo=KST), True, id="경계값 09:00:00(당일 세션)"),
    ],
)
def test_is_us_trading_session(when: datetime, expected: bool):
    assert is_us_trading_session(when) is expected


@pytest.mark.parametrize(
    ("when", "expected"),
    [
        # 겨울(EST, UTC-5): 2026-01-20 마감 21:00 UTC = 다음날 06:00 KST
        pytest.param(datetime(2026, 1, 21, 5, 59, 59, tzinfo=KST), False, id="겨울 마감 직전(05:59:59)"),
        pytest.param(datetime(2026, 1, 21, 6, 0, 0, tzinfo=KST), True, id="겨울 마감 경계값(06:00:00)"),
        # 여름(EDT, UTC-4): 2026-07-02 마감 20:00 UTC = 다음날 05:00 KST
        pytest.param(datetime(2026, 7, 3, 4, 59, 59, tzinfo=KST), False, id="여름 마감 직전(04:59:59)"),
        pytest.param(datetime(2026, 7, 3, 5, 0, 0, tzinfo=KST), True, id="여름 마감 경계값(05:00:00)"),
        # 휴장일(토요일 세션) - 그날 장이 아예 없으면 마감 이후로 취급
        pytest.param(datetime(2026, 1, 4, 6, 0, 0, tzinfo=KST), True, id="휴장일(토요일 세션)"),
    ],
)
def test_is_end_of_investing_time(when: datetime, expected: bool):
    assert is_end_of_investing_time(when) is expected
