"""
后端统一使用东八区（中国时区）时间
"""
from datetime import datetime, timezone, timedelta

# 东八区
TZ_EAST_8 = timezone(timedelta(hours=8))


def now_east8() -> datetime:
    """当前时间（东八区），用于写入数据库等"""
    return datetime.now(TZ_EAST_8)
