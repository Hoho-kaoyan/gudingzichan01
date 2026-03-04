"""
数据库初始化脚本
用于创建初始管理员账户和资产大类
"""
from database import SessionLocal, engine, Base
from models import User, AssetCategory
from auth import get_password_hash

# 初始用户配置
INITIAL_USERS = [
    {
        "ehr_number": "0000001",
        "real_name": "系统管理员",
        "group": "管理组",
        "role": "admin",
        "password": "1234567"
    },
    {
        "ehr_number": "1000000",
        "real_name": "仓库",
        "group": "仓库",
        "role": "user",
        "password": "1234567"
    },
    {
        "ehr_number": "1234567",
        "real_name": "测试组长1",
        "group": "测试组",
        "role": "leader",
        "password": "1234567"
    },
    {
        "ehr_number": "1234568",
        "real_name": "测试用户1",
        "group": "测试组",
        "role": "user",
        "password": "1234567"
    }
]

def init_database():
    """初始化数据库"""
    # 创建所有表
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    try:
        # 创建初始用户
        for user_config in INITIAL_USERS:
            # 检查用户是否已存在（按EHR号检查）
            existing_user = db.query(User).filter(User.ehr_number == user_config["ehr_number"]).first()
            if not existing_user:
                # 创建新用户
                new_user = User(
                    ehr_number=user_config["ehr_number"],
                    real_name=user_config["real_name"],
                    group=user_config["group"],
                    role=user_config["role"],
                    password_hash=get_password_hash(user_config["password"])
                )
                db.add(new_user)
                print(f"✓ 创建用户: {user_config['real_name']}")
                print(f"  EHR号: {user_config['ehr_number']}")
                print(f"  角色: {user_config['role']}")
                print(f"  密码: {user_config['password']}")
            else:
                print(f"✓ 用户已存在: {user_config['real_name']} (EHR号: {user_config['ehr_number']})")
        
        # 创建默认资产大类
        categories = ["办公用品", "电子设备配件", "家具", "其他"]
        for cat_name in categories:
            existing = db.query(AssetCategory).filter(AssetCategory.name == cat_name).first()
            if not existing:
                category = AssetCategory(name=cat_name)
                db.add(category)
                print(f"[OK] 创建资产大类: {cat_name}")
        
        db.commit()
        print("\n数据库初始化完成！")
        
    except Exception as e:
        print(f"初始化失败: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    init_database()