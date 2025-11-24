"""
迁移脚本：创建asset_edit_requests表
"""
import sqlite3
import os

def migrate():
    db_path = os.path.join(os.path.dirname(__file__), 'assets.db')
    
    if not os.path.exists(db_path):
        print(f"数据库文件不存在: {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 检查表是否已存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='asset_edit_requests'")
        if cursor.fetchone():
            print("asset_edit_requests表已存在，跳过迁移")
            conn.close()
            return
        
        # 创建asset_edit_requests表
        cursor.execute("""
            CREATE TABLE asset_edit_requests (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                asset_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                approver_id INTEGER,
                approval_comment TEXT,
                created_at DATETIME,
                updated_at DATETIME,
                approved_at DATETIME,
                edit_data TEXT NOT NULL,
                FOREIGN KEY(asset_id) REFERENCES assets (id),
                FOREIGN KEY(user_id) REFERENCES users (id),
                FOREIGN KEY(approver_id) REFERENCES users (id)
            )
        """)
        
        # 创建索引
        cursor.execute("CREATE INDEX ix_asset_edit_requests_asset_id ON asset_edit_requests (asset_id)")
        cursor.execute("CREATE INDEX ix_asset_edit_requests_user_id ON asset_edit_requests (user_id)")
        cursor.execute("CREATE INDEX ix_asset_edit_requests_status ON asset_edit_requests (status)")
        
        conn.commit()
        print("已创建asset_edit_requests表")
        
    except Exception as e:
        print(f"迁移失败: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()


