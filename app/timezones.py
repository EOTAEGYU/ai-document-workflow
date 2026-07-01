from datetime import datetime
from datetime import timezone as dt_timezone
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")


def to_kst(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=dt_timezone.utc)
    return dt.astimezone(KST)
