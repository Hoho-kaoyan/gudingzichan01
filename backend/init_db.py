"""
数据库初始化脚本
用于创建初始管理员账户和资产大类
"""
from database import SessionLocal, engine, Base
from models import User, AssetCategory
from auth import get_password_hash

def init_database():
    """初始化数据库"""
    # 创建所有表
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    try:
        # 检查是否已有管理员
        admin = db.query(User).filter(User.role == "admin").first()
        if not admin:
            # 创建默认管理员账户
            admin_user = User(
                ehr_number="0000001",
                real_name="系统管理员",
                group="管理组",
                role="admin",
                password_hash=get_password_hash("admin123")
            )
            db.add(admin_user)
            print("✓ 创建默认管理员账户")
            print("  EHR号: 0000001")
            print("  密码: admin123")
        else:
            print("✓ 管理员账户已存在")
        
        # 检查是否已有"仓库"用户
        warehouse_user = db.query(User).filter(User.ehr_number == "1000000").first()
        if not warehouse_user:
            # 创建"仓库"用户
            warehouse = User(
                ehr_number="1000000",
                real_name="仓库",
                group="仓库",
                role="user",
                password_hash=get_password_hash("warehouse")  # 设置一个默认密码，但通常不需要登录
            )
            db.add(warehouse)
            print("✓ 创建仓库用户")
            print("  EHR号: 1000000")
            print("  姓名: 仓库")
        else:
            print("✓ 仓库用户已存在")
        
        # 创建默认资产大类
        categories = ["办公用品", "电子设备配件", "家具", "其他"]
        for cat_name in categories:
            existing = db.query(AssetCategory).filter(AssetCategory.name == cat_name).first()
            if not existing:
                category = AssetCategory(name=cat_name)
                db.add(category)
                print(f"✓ 创建资产大类: {cat_name}")
        
        db.commit()
        print("\n数据库初始化完成！")
        
    except Exception as e:
        print(f"初始化失败: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    init_database()



用于创建初始管理员账户和资产大类
"""
from database import SessionLocal, engine, Base
from models import User, AssetCategory
from auth import get_password_hash

def init_database():
    """初始化数据库"""
    # 创建所有表
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    try:
        # 检查是否已有管理员
        admin = db.query(User).filter(User.role == "admin").first()
        if not admin:
            # 创建默认管理员账户
            admin_user = User(
                ehr_number="0000001",
                real_name="系统管理员",
                group="管理组",
                role="admin",
                password_hash=get_password_hash("admin123")
            )
            db.add(admin_user)
            print("✓ 创建默认管理员账户")
            print("  EHR号: 0000001")
            print("  密码: admin123")
        else:
            print("✓ 管理员账户已存在")
        
        # 检查是否已有"仓库"用户
        warehouse_user = db.query(User).filter(User.ehr_number == "1000000").first()
        if not warehouse_user:
            # 创建"仓库"用户
            warehouse = User(
                ehr_number="1000000",
                real_name="仓库",
                group="仓库",
                role="user",
                password_hash=get_password_hash("warehouse")  # 设置一个默认密码，但通常不需要登录
            )
            db.add(warehouse)
            print("✓ 创建仓库用户")
            print("  EHR号: 1000000")
            print("  姓名: 仓库")
        else:
            print("✓ 仓库用户已存在")
        
        # 创建默认资产大类
        categories = ["办公用品", "电子设备配件", "家具", "其他"]
        for cat_name in categories:
            existing = db.query(AssetCategory).filter(AssetCategory.name == cat_name).first()
            if not existing:
                category = AssetCategory(name=cat_name)
                db.add(category)
                print(f"✓ 创建资产大类: {cat_name}")
        
        db.commit()
        print("\n数据库初始化完成！")
        
    except Exception as e:
        print(f"初始化失败: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    init_database()


