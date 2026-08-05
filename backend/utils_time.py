"""
后端统一使用东八区（中国时区）时间
"""
from datetime import datetime, timezone, timedelta
from typing import Optional

# 东八区
TZ_EAST_8 = timezone(timedelta(hours=8))


def now_east8() -> datetime:
    """当前时间（东八区），用于写入数据库等"""
    return datetime.now(TZ_EAST_8)


def now_utc_naive() -> datetime:
    """
    当前时间（UTC，无时区信息）。
    用于写入数据库，与 func.now()（UTC）保持一致。
    注意：序列化时 datetime_to_east8_iso 会把 naive 视为 UTC 再转东八区，
    因此入库时间必须存 UTC naive，避免出现「东八区时间被再次 +8」的问题。
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def datetime_to_east8_iso(dt: Optional[datetime]) -> Optional[str]:
    """
    将 datetime 转为东八区后的 ISO 字符串（带 +08:00），用于 API 序列化。
    - 若为 None 返回 None。
    - 若为 naive，视为 UTC 并转为东八区。
    - 若为 aware，先转为东八区再输出。
    这样前端收到的始终是「东八区时间」字符串，显示与所处地区一致。
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        # 无时区视为 UTC（与 SQLite server_default=func.now() 等一致）
        dt = dt.replace(tzinfo=timezone.utc)
    east8 = dt.astimezone(TZ_EAST_8)
    return east8.isoformat()
