"""
迁移脚本：为 return_requests 表添加字段
"""
import sqlite3
import os

# 数据库文件路径（项目根目录）
db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets.db')

if not os.path.exists(db_path):
    print(f"数据库文件不存在: {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    # 检查字段是否已存在
    cursor.execute("PRAGMA table_info(return_requests)")
    columns = [row[1] for row in cursor.fetchall()]
    
    fields_to_add = [
        ('mac_address', 'VARCHAR(50)'),
        ('ip_address', 'VARCHAR(50)'),
        ('office_location', 'VARCHAR(200)'),
        ('floor', 'VARCHAR(50)'),
        ('seat_number', 'VARCHAR(50)'),
        ('new_user_id', 'INTEGER'),
        ('remark', 'TEXT')
    ]
    
    for field_name, field_type in fields_to_add:
        if field_name not in columns:
            print(f"添加 {field_name} 字段到 return_requests 表...")
            cursor.execute(f"ALTER TABLE return_requests ADD COLUMN {field_name} {field_type}")
            print(f"✓ {field_name} 字段已添加")
        else:
            print(f"{field_name} 字段已存在")
    
    # 添加外键约束（如果 new_user_id 存在但外键不存在）
    if 'new_user_id' in columns:
        cursor.execute("PRAGMA foreign_key_list(return_requests)")
        foreign_keys = [row[3] for row in cursor.fetchall()]
        if 'new_user_id' not in foreign_keys:
            # SQLite 不支持直接添加外键，需要重建表
            # 这里先跳过，因为外键约束在创建表时已经定义
            pass
    
    conn.commit()
    print("迁移完成！")
    
except Exception as e:
    conn.rollback()
    print(f"迁移失败: {e}")
    raise
finally:
    conn.close()
