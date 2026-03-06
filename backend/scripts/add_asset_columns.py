"""
为 assets 表添加扩展字段（件数、所在团队、购置日期等）。
SQLite 不支持 ADD COLUMN IF NOT EXISTS，已存在的列会跳过。
在 backend 目录下执行：python scripts/add_asset_columns.py
"""
import sys
from pathlib import Path

# 保证可导入 backend 模块
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database import engine
from sqlalchemy import text

NEW_COLUMNS = [
    ("quantity", "INTEGER DEFAULT 1"),
    ("team", "VARCHAR(100)"),
    ("purchase_date", "DATE"),
    ("card_number", "VARCHAR(100)"),
    ("safety_check_executor_id", "INTEGER"),
    ("safety_check_executor_name", "VARCHAR(100)"),
    ("computer_type", "VARCHAR(100)"),
    ("computer_usage", "VARCHAR(200)"),
    ("computer_name", "VARCHAR(200)"),
    ("monitor1_model", "VARCHAR(200)"),
    ("monitor1_asset_number", "VARCHAR(100)"),
    ("monitor1_serial", "VARCHAR(100)"),
    ("monitor2_model", "VARCHAR(200)"),
    ("monitor2_asset_number", "VARCHAR(100)"),
    ("monitor2_serial", "VARCHAR(100)"),
    ("asset_contact", "VARCHAR(200)"),
    ("reserve_1", "VARCHAR(200)"),
    ("reserve_2", "VARCHAR(200)"),
    ("reserve_3", "VARCHAR(200)"),
    ("reserve_4", "VARCHAR(200)"),
    ("reserve_5", "VARCHAR(200)"),
    ("reserve_6", "VARCHAR(200)"),
]


def main():
    with engine.connect() as conn:
        for col_name, col_type in NEW_COLUMNS:
            try:
                conn.execute(text(f"ALTER TABLE assets ADD COLUMN {col_name} {col_type}"))
                conn.commit()
                print(f"  added column: {col_name}")
            except Exception as e:
                if "duplicate column name" in str(e).lower():
                    print(f"  skip (exists): {col_name}")
                else:
                    raise
    print("Done.")


if __name__ == "__main__":
    main()
