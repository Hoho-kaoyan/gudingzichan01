"""
迁移脚本：为 assets 表添加 seat_number 和 remark 字段
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
    cursor.execute("PRAGMA table_info(assets)")
    columns = [row[1] for row in cursor.fetchall()]
    
    # 添加 seat_number 字段
    if 'seat_number' not in columns:
        print("添加 seat_number 字段到 assets 表...")
        cursor.execute("ALTER TABLE assets ADD COLUMN seat_number VARCHAR(50)")
        print("✓ seat_number 字段已添加")
    else:
        print("seat_number 字段已存在")
    
    # 添加 remark 字段
    if 'remark' not in columns:
        print("添加 remark 字段到 assets 表...")
        cursor.execute("ALTER TABLE assets ADD COLUMN remark TEXT")
        print("✓ remark 字段已添加")
    else:
        print("remark 字段已存在")
    
    conn.commit()
    print("迁移完成！")
    
except Exception as e:
    conn.rollback()
    print(f"迁移失败: {e}")
    raise
finally:
    conn.close()
