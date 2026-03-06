"""
为 users 表添加逻辑删除字段 deleted_at, deleted_by_id。
在 backend 目录下执行：python3 scripts/add_user_deleted_columns.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database import engine
from sqlalchemy import text

COLUMNS = [
    ("deleted_at", "DATETIME"),
    ("deleted_by_id", "INTEGER"),
]


def main():
    with engine.connect() as conn:
        for col_name, col_type in COLUMNS:
            try:
                conn.execute(text(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}"))
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
