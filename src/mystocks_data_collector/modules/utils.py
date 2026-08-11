from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas_market_calendars as mcal

_NYSE = mcal.get_calendar("NYSE")


def now_korea() -> datetime:
    KST = ZoneInfo("Asia/Seoul")
    new_kst = datetime.now(KST)
    return new_kst


def is_us_trading_session(now: datetime) -> bool:
    """now 시각이 미국장 개장일 세션(KST 09:00~익일 08:59)에 해당하는지"""
    trading_date = (now - timedelta(hours=9)).date()
    schedule = _NYSE.schedule(start_date=trading_date, end_date=trading_date)
    return not schedule.empty
