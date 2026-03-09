"""
Excel 单元格解析：先把单元格统一成字符串（空/NaN → 空字符串），再按数据库字段类型转换。
避免 pandas 将数字读成浮点、空值读成 NaN 导致的 .0 和类型问题。
"""
from typing import Optional, Any
from datetime import date
import pandas as pd


def cell_to_str(cell: Any) -> str:
    """
    单元格 → 字符串。空/NaN → ''；整数浮点(如 123.0) → 无 .0 的字符串；否则 str(cell).strip()。
    """
    if cell is None:
        return ""
    if getattr(cell, "__iter__", None) and not isinstance(cell, str) and pd.isna(cell):
        return ""
    s = str(cell).strip()
    if s.lower() == "nan" or not s:
        return ""
    # 数字浮点写成 123.0 时，转为 "123"
    try:
        f = float(s)
        if f == int(f):
            return str(int(f))
    except (ValueError, TypeError):
        pass
    return s


def row_cell_str(row: Any, df_cols: Any, *col_names: str, default: str = "") -> str:
    """从行中取第一个存在的列，用 cell_to_str 转成字符串；无匹配列或空返回 default。"""
    for c in col_names:
        if c in df_cols:
            s = cell_to_str(row.get(c, default))
            return s if s else default
    return default


def str_to_str(s: str, nullable: bool = True) -> Optional[str]:
    """字符串 → DB 字符串：空串且 nullable 则返回 None，否则返回 s。"""
    if not s:
        return None if nullable else ""
    return s


def str_to_int(s: str, default: Optional[int] = None) -> Optional[int]:
    """字符串 → DB 整数：空串返回 default；否则 int(float(s))。"""
    if not s:
        return default
    try:
        return int(float(s))
    except (ValueError, TypeError):
        return default


def str_to_date(s: str) -> Optional[date]:
    """字符串 → DB 日期；空串或解析失败返回 None。"""
    if not s:
        return None
    s = s.strip()[:10]
    if not s:
        return None
    if hasattr(s, "date"):
        return getattr(s, "date")()
    try:
        from datetime import datetime as _dt
        return _dt.strptime(s, "%Y-%m-%d").date()
    except Exception:
        try:
            return pd.to_datetime(s).date()
        except Exception:
            return None


def cell_to_date(cell: Any) -> Optional[date]:
    """单元格 → 日期：datetime 用 .date()；Excel 序列数(float) 按天转；否则按字符串解析。"""
    if cell is None or pd.isna(cell):
        return None
    if hasattr(cell, "date") and callable(getattr(cell, "date", None)):
        try:
            return cell.date()
        except Exception:
            pass
    if isinstance(cell, (int, float)):
        try:
            return pd.to_datetime(cell, unit="D", origin="1899-12-30").date()
        except Exception:
            return None
    s = cell_to_str(cell)
    return str_to_date(s) if s else None


def row_to_error_dict(row_data: Any) -> dict:
    """把行字典里每个值转为可展示的字符串（NaN/None → ''），用于导入错误详情。"""
    return {k: cell_to_str(v) or "" for k, v in row_data.items()}
