"""
迁移脚本：为 assets 表添加 seat_number 和 remark 字段
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
        
        if 'seat_number' not in columns:
            # 添加 seat_number 列
            cursor.execute('''
                ALTER TABLE assets 
                ADD COLUMN seat_number VARCHAR(50)
            ''')
            conn.commit()
            print("✓ 成功添加 seat_number 列")
            changes = True
        else:
            print("✓ seat_number 列已存在")
        
        if 'remark' not in columns:
            # 添加 remark 列
            cursor.execute('''
                ALTER TABLE assets 
                ADD COLUMN remark TEXT
            ''')
            conn.commit()
            print("✓ 成功添加 remark 列")
            changes = True
        else:
            print("✓ remark 列已存在")
        
        if not changes:
            print("所有字段已存在，无需迁移")
        
    except Exception as e:
        print(f"迁移失败: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()

迁移脚本：为 assets 表添加 seat_number 和 remark 字段
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
        
        if 'seat_number' not in columns:
            # 添加 seat_number 列
            cursor.execute('''
                ALTER TABLE assets 
                ADD COLUMN seat_number VARCHAR(50)
            ''')
            conn.commit()
            print("✓ 成功添加 seat_number 列")
            changes = True
        else:
            print("✓ seat_number 列已存在")
        
        if 'remark' not in columns:
            # 添加 remark 列
            cursor.execute('''
                ALTER TABLE assets 
                ADD COLUMN remark TEXT
            ''')
            conn.commit()
            print("✓ 成功添加 remark 列")
            changes = True
        else:
            print("✓ remark 列已存在")
        
        if not changes:
            print("所有字段已存在，无需迁移")
        
    except Exception as e:
        print(f"迁移失败: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()



