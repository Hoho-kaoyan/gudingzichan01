"""
为 transfer_requests 表增加 linked_safety_task_id 字段（B4/B5：交接单关联联动安检任务）。
在 backend 目录下执行：python scripts/migrate_add_linked_safety_task_id.py
执行前请备份数据库。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text
from database import engine


def main():
    with engine.connect() as conn:
        # SQLite 不支持 IF NOT EXISTS for ADD COLUMN，先检查列是否已存在
        try:
            conn.execute(text(
                "ALTER TABLE transfer_requests ADD COLUMN linked_safety_task_id INTEGER NULL"
            ))
            conn.commit()
            print("已为 transfer_requests 表添加 linked_safety_task_id 列。迁移完成。")
        except Exception as e:
            err = str(e).lower()
            if "duplicate column name" in err or "already exists" in err:
                print("linked_safety_task_id 列已存在，无需重复迁移。")
            else:
                raise


if __name__ == "__main__":
    main()
