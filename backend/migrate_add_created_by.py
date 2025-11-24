"""
迁移脚本：为 transfer_requests 表添加 created_by_id 字段
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
        cursor.execute('PRAGMA table_info(transfer_requests)')
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'created_by_id' in columns:
            print("✓ created_by_id 列已存在")
        else:
            # 添加 created_by_id 列
            cursor.execute('''
                ALTER TABLE transfer_requests 
                ADD COLUMN created_by_id INTEGER REFERENCES users(id)
            ''')
            conn.commit()
            print("✓ 成功添加 created_by_id 列")
            
            # 对于现有记录，将 created_by_id 设置为 from_user_id（假设是原使用人创建的）
            cursor.execute('''
                UPDATE transfer_requests 
                SET created_by_id = from_user_id 
                WHERE created_by_id IS NULL
            ''')
            conn.commit()
            print("✓ 已更新现有记录的 created_by_id")
        
    except Exception as e:
        print(f"迁移失败: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()

迁移脚本：为 transfer_requests 表添加 created_by_id 字段
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
        cursor.execute('PRAGMA table_info(transfer_requests)')
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'created_by_id' in columns:
            print("✓ created_by_id 列已存在")
        else:
            # 添加 created_by_id 列
            cursor.execute('''
                ALTER TABLE transfer_requests 
                ADD COLUMN created_by_id INTEGER REFERENCES users(id)
            ''')
            conn.commit()
            print("✓ 成功添加 created_by_id 列")
            
            # 对于现有记录，将 created_by_id 设置为 from_user_id（假设是原使用人创建的）
            cursor.execute('''
                UPDATE transfer_requests 
                SET created_by_id = from_user_id 
                WHERE created_by_id IS NULL
            ''')
            conn.commit()
            print("✓ 已更新现有记录的 created_by_id")
        
    except Exception as e:
        print(f"迁移失败: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()



