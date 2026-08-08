from datetime import datetime
from zoneinfo import ZoneInfo


def now_korea() -> datetime:
    KST = ZoneInfo("Asia/Seoul")
    new_kst = datetime.now(KST)
    return new_kst

