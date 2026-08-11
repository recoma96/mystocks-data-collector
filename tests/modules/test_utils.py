from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from mystocks_data_collector.modules.utils import is_us_trading_session

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
