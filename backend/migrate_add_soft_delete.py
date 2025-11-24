"""
迁移脚本：为 assets 表添加软删除字段
"""
import sqlite3
import os

def migrate():
    db_path = 'assets.db'
    if not os.path.exists(db_path):
        print(f"数据库文件不存在: {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 检查列是否已存在
        cursor.execute('PRAGMA table_info(assets)')
        columns = [col[1] for col in cursor.fetchall()]
        
        changes = False
        
        if 'deleted_at' not in columns:
            # 添加 deleted_at 列
            cursor.execute('''
                ALTER TABLE assets 
                ADD COLUMN deleted_at DATETIME
            ''')
            conn.commit()
            print("✓ 成功添加 deleted_at 列")
            changes = True
        else:
            print("✓ deleted_at 列已存在")
        
        if 'deleted_by_id' not in columns:
            # 添加 deleted_by_id 列
            cursor.execute('''
                ALTER TABLE assets 
                ADD COLUMN deleted_by_id INTEGER REFERENCES users(id)
            ''')
            conn.commit()
            print("✓ 成功添加 deleted_by_id 列")
            changes = True
        else:
            print("✓ deleted_by_id 列已存在")
        
        if not changes:
            print("所有字段已存在，无需迁移")
        
    except Exception as e:
        print(f"迁移失败: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()

迁移脚本：为 assets 表添加软删除字段
"""
import sqlite3
import os

def migrate():
    db_path = 'assets.db'
    if not os.path.exists(db_path):
        print(f"数据库文件不存在: {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 检查列是否已存在
        cursor.execute('PRAGMA table_info(assets)')
        columns = [col[1] for col in cursor.fetchall()]
        
        changes = False
        
        if 'deleted_at' not in columns:
            # 添加 deleted_at 列
            cursor.execute('''
                ALTER TABLE assets 
                ADD COLUMN deleted_at DATETIME
            ''')
            conn.commit()
            print("✓ 成功添加 deleted_at 列")
            changes = True
        else:
            print("✓ deleted_at 列已存在")
        
        if 'deleted_by_id' not in columns:
            # 添加 deleted_by_id 列
            cursor.execute('''
                ALTER TABLE assets 
                ADD COLUMN deleted_by_id INTEGER REFERENCES users(id)
            ''')
            conn.commit()
            print("✓ 成功添加 deleted_by_id 列")
            changes = True
        else:
            print("✓ deleted_by_id 列已存在")
        
        if not changes:
            print("所有字段已存在，无需迁移")
        
    except Exception as e:
        print(f"迁移失败: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()



