from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import pandas_market_calendars as mcal

_NYSE = mcal.get_calendar("NYSE")


def now_korea() -> datetime:
    KST = ZoneInfo("Asia/Seoul")
    new_kst = datetime.now(KST)
    return new_kst


def _nyse_schedule_of(now: datetime) -> pd.DataFrame:
    """now(KST) 시각이 속한 거래일의 NYSE(뉴욕증권거래소) 스케줄(개장/마감 시각)을 조회한다."""
    trading_date = (now - timedelta(hours=9)).date()
    return _NYSE.schedule(start_date=trading_date, end_date=trading_date)


def is_us_trading_session(now: datetime) -> bool:
    """now 시각이 미국장 개장일 세션(KST 09:00~익일 08:59)에 해당하는지"""
    return not _nyse_schedule_of(now).empty


def or_zero(value: float | None) -> float:
    return value if value is not None else 0.0


def is_end_of_investing_time(now: datetime) -> bool:
    """now(KST) 시각 기준으로, 해당 거래일의 미국장이 실제로 마감됐는지 확인한다.

    서머타임(EDT/EST) 전환뿐 아니라 조기 폐장일(半장)까지 pandas_market_calendars가
    제공하는 실제 마감 시각을 기준으로 판단하므로, "오전 5시"처럼 하드코딩된 값에
    의존하지 않는다. 그날 장이 아예 없었던 경우(휴장일)는 마감 이후로 취급한다.
    """
    schedule = _nyse_schedule_of(now)
    if schedule.empty:
        return True

    market_close = schedule.iloc[0]["market_close"]
    return now >= market_close
