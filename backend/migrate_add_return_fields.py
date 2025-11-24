"""
迁移脚本：为return_requests表添加申请人修改的字段
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
        # 检查表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='return_requests'")
        if not cursor.fetchone():
            print("return_requests表不存在，跳过迁移")
            conn.close()
            return
        
        # 添加新字段
        new_columns = [
            ('mac_address', 'VARCHAR(50)'),
            ('ip_address', 'VARCHAR(50)'),
            ('office_location', 'VARCHAR(200)'),
            ('floor', 'VARCHAR(50)'),
            ('seat_number', 'VARCHAR(50)'),
            ('new_user_id', 'INTEGER'),
            ('remark', 'TEXT')
        ]
        
        for column_name, column_type in new_columns:
            try:
                # 检查列是否已存在
                cursor.execute(f"PRAGMA table_info(return_requests)")
                columns = [row[1] for row in cursor.fetchall()]
                
                if column_name not in columns:
                    if column_name == 'new_user_id':
                        # 添加外键列
                        cursor.execute(f"""
                            ALTER TABLE return_requests 
                            ADD COLUMN {column_name} {column_type} 
                            REFERENCES users(id)
                        """)
                    else:
                        cursor.execute(f"""
                            ALTER TABLE return_requests 
                            ADD COLUMN {column_name} {column_type}
                        """)
                    print(f"已添加列: {column_name}")
                else:
                    print(f"列 {column_name} 已存在，跳过")
            except sqlite3.OperationalError as e:
                print(f"添加列 {column_name} 失败: {e}")
        
        conn.commit()
        print("迁移完成")
        
    except Exception as e:
        print(f"迁移失败: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()

迁移脚本：为return_requests表添加申请人修改的字段
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
        # 检查表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='return_requests'")
        if not cursor.fetchone():
            print("return_requests表不存在，跳过迁移")
            conn.close()
            return
        
        # 添加新字段
        new_columns = [
            ('mac_address', 'VARCHAR(50)'),
            ('ip_address', 'VARCHAR(50)'),
            ('office_location', 'VARCHAR(200)'),
            ('floor', 'VARCHAR(50)'),
            ('seat_number', 'VARCHAR(50)'),
            ('new_user_id', 'INTEGER'),
            ('remark', 'TEXT')
        ]
        
        for column_name, column_type in new_columns:
            try:
                # 检查列是否已存在
                cursor.execute(f"PRAGMA table_info(return_requests)")
                columns = [row[1] for row in cursor.fetchall()]
                
                if column_name not in columns:
                    if column_name == 'new_user_id':
                        # 添加外键列
                        cursor.execute(f"""
                            ALTER TABLE return_requests 
                            ADD COLUMN {column_name} {column_type} 
                            REFERENCES users(id)
                        """)
                    else:
                        cursor.execute(f"""
                            ALTER TABLE return_requests 
                            ADD COLUMN {column_name} {column_type}
                        """)
                    print(f"已添加列: {column_name}")
                else:
                    print(f"列 {column_name} 已存在，跳过")
            except sqlite3.OperationalError as e:
                print(f"添加列 {column_name} 失败: {e}")
        
        conn.commit()
        print("迁移完成")
        
    except Exception as e:
        print(f"迁移失败: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()



