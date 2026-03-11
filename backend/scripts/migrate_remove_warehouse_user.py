"""
移除仓库用户：将原「使用人=仓库用户」的资产改为 user_id=NULL、status=在库，并删除仓库用户记录。
在 backend 目录下执行：python scripts/migrate_remove_warehouse_user.py
执行前请备份数据库。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database import SessionLocal
from models import User, Asset


def main():
    db = SessionLocal()
    try:
        warehouse = db.query(User).filter(User.ehr_number == "1000000").first()
        if not warehouse:
            print("未找到仓库用户（EHR 1000000），无需迁移。")
            return

        assets = db.query(Asset).filter(Asset.user_id == warehouse.id).all()
        count = len(assets)
        for a in assets:
            a.user_id = None
            a.user_group = None
            a.status = "在库"
        if count > 0:
            db.commit()
            print(f"已将 {count} 条资产的使用人置空、状态设为在库。")
        else:
            print("没有资产使用人为仓库用户，无需更新资产。")

        db.delete(warehouse)
        db.commit()
        print("已删除仓库用户（EHR 1000000）。迁移完成。")
    except Exception as e:
        db.rollback()
        print(f"迁移失败: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
