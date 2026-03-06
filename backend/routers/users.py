"""
用户管理路由
包括用户的增删改查、批量导入等
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional
from database import get_db
from models import User, Asset, SafetyCheckTask, TaskAsset, SafetyCheckAutoConfig, SafetyCheckAssetTypeMapping
from schemas import UserCreate, UserUpdate, UserResponse, ImportResponse
from auth import get_current_user, get_current_admin_user, get_password_hash
import pandas as pd
import io
from datetime import datetime

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """获取当前登录用户信息"""
    return UserResponse.model_validate(current_user)


@router.get("/", response_model=List[UserResponse])
async def get_users(
    skip: int = 0,
    limit: int = 500,
    search: Optional[str] = Query(None, description="搜索关键词，支持模糊搜索所有字段"),
    role: Optional[str] = Query(None, description="按角色筛选"),
    status: Optional[str] = Query(None, description="按状态筛选"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取用户列表（所有已登录用户可访问，用于选择转入用户等场景），支持搜索；不含已逻辑删除用户"""
    query = db.query(User).filter(User.deleted_at.is_(None))
    
    # 支持模糊搜索所有字段
    if search:
        query = query.filter(
            or_(
                User.ehr_number.contains(search),
                User.real_name.contains(search),
                User.group.contains(search)
            )
        )
    
    # 按角色筛选
    if role:
        query = query.filter(User.role == role)
    
    # 按状态筛选
    if status:
        query = query.filter(User.status == status)
    
    users = query.offset(skip).limit(limit).all()
    return [UserResponse.model_validate(user) for user in users]


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取指定用户信息"""
    user = db.query(User).filter(User.id == user_id, User.deleted_at.is_(None)).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return UserResponse.model_validate(user)


@router.post("/", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """创建新用户（仅管理员）"""
    # 检查EHR号是否已存在（未删除用户）
    existing_user = db.query(User).filter(
        User.ehr_number == user_data.ehr_number,
        User.deleted_at.is_(None)
    ).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="EHR号已存在")
    
    # 创建新用户
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        ehr_number=user_data.ehr_number,
        real_name=user_data.real_name,
        group=user_data.group,
        role=user_data.role,
        status=user_data.status if hasattr(user_data, 'status') and user_data.status else "在岗",
        password_hash=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return UserResponse.model_validate(db_user)


@router.put("/{user_id}/mark-resignation", response_model=UserResponse)
async def mark_user_resignation(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """标记用户离职，并根据资产配置自动触发安全检查任务（仅管理员）"""
    user = db.query(User).filter(User.id == user_id, User.deleted_at.is_(None)).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    if user.status == "离职":
        raise HTTPException(status_code=400, detail="该用户已经是离职状态")

    print(f"DEBUG: 收到离职请求, 用户ID={user_id}")
    # 1. 查找名下资产
    assets = db.query(Asset).filter(Asset.user_id == user_id, Asset.deleted_at == None).all()
    print(f"DEBUG: 用户 {user_id} 名下资产数量: {len(assets)}")
    
    if assets:
        # 获取自动配置
        auto_config = db.query(SafetyCheckAutoConfig).first()
        print(f"DEBUG: 全局配置={auto_config.default_check_type_id if auto_config else '未配置'}")
        default_type_id = auto_config.default_check_type_id if auto_config else None
        
        # 获取所有映射
        mappings = {m.asset_type: m.check_type_id for m in db.query(SafetyCheckAssetTypeMapping).all()}
        print(f"DEBUG: 映射数量={len(mappings)}")
        
        # 按类型对资产分类
        tasks_to_create = {} # {type_id: [asset_ids]}
        
        for asset in assets:
            # 优先匹配映射，否则使用全局默认
            type_id = mappings.get(asset.name) or default_type_id
            print(f"DEBUG: 资产 {asset.name} 匹配到的类型ID={type_id}")
            if type_id:
                if type_id not in tasks_to_create:
                    tasks_to_create[type_id] = []
                tasks_to_create[type_id].append(asset.id)
        
        print(f"DEBUG: 计划创建的任务数={len(tasks_to_create)}")
        
        # 创建安全检查任务
        for type_id, asset_ids in tasks_to_create.items():
            # 生成任务编号: SC-RESIGN-日期-用户ID-类型ID-随机数
            import random
            ts_str = datetime.now().strftime('%Y%m%d%H%M%S')
            task_number = f"SC-RESIGN-{ts_str}-{user_id}-{type_id}-{random.randint(100, 999)}"
            
            task = SafetyCheckTask(
                task_number=task_number,
                check_type_id=type_id,
                title=f"离职安全检查 - {user.real_name}",
                description=f"用户 {user.real_name} 离职触发的自动安全检查任务",
                status="pending",
                source="resignation",
                created_by_id=current_user.id
            )
            db.add(task)
            db.flush() # 确保获取到 task.id
            
            for aid in asset_ids:
                ta = TaskAsset(
                    task_id=task.id,
                    asset_id=aid,
                    assigned_user_id=user_id,
                    status="pending"
                )
                db.add(ta)
    
    # 2. 更新用户状态
    user.status = "离职"
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """更新用户信息（仅管理员）"""
    user = db.query(User).filter(User.id == user_id, User.deleted_at.is_(None)).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 更新字段
    if user_data.real_name is not None:
        user.real_name = user_data.real_name
    if user_data.group is not None:
        user.group = user_data.group
    if user_data.role is not None:
        user.role = user_data.role
    if user_data.status is not None:
        user.status = user_data.status
    if user_data.password is not None:
        user.password_hash = get_password_hash(user_data.password)
    
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """删除用户（仅管理员，软删除）"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.deleted_at is not None:
        raise HTTPException(status_code=400, detail="用户已被删除")
    
    # 禁止删除"仓库"用户（EHR号为1000000）
    if user.ehr_number == "1000000":
        raise HTTPException(status_code=400, detail="不能删除仓库用户")
    
    from datetime import datetime, timezone
    user.deleted_at = datetime.now(timezone.utc)
    user.deleted_by_id = current_user.id
    db.commit()
    return {"message": "用户已删除"}




@router.post("/import", response_model=ImportResponse)
async def import_users(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    批量导入用户（仅管理员）
    Excel格式要求：
    - 列名：EHR号、姓名、组别、角色（可选，默认为user）、密码（可选，默认为123456）
    """
    try:
        # 读取Excel文件
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents))
        
        # 验证必需的列
        required_columns = ['EHR号', '姓名', '组别']
        for col in required_columns:
            if col not in df.columns:
                raise HTTPException(
                    status_code=400,
                    detail=f"Excel文件缺少必需的列：{col}"
                )
        
        success_count = 0
        error_count = 0
        errors = []
        error_details = []
        
        for index, row in df.iterrows():
            row_number = index + 2  # Excel行号（从2开始，第1行是表头）
            row_data = row.to_dict()  # 保存原始行数据
            
            try:
                # 处理可能被 pandas 识别为浮点数的 EHR 号 (例如 1234561.0 -> 1234561)
                raw_ehr = str(row['EHR号']).strip()
                if raw_ehr.endswith('.0'):
                    ehr_number = raw_ehr[:-2]
                else:
                    ehr_number = raw_ehr
                    
                real_name = str(row['姓名']).strip()
                group = str(row['组别']).strip()
                role = str(row.get('角色', 'user')).strip() if '角色' in df.columns else 'user'
                status = str(row.get('状态', '在岗')).strip() if '状态' in df.columns else '在岗'
                password = str(row.get('密码', '123456')).strip() if '密码' in df.columns else '123456'
                
                # 验证EHR号
                if len(ehr_number) != 7 or not ehr_number.isdigit():
                    error_count += 1
                    error_msg = "EHR号格式错误（必须为7位数字）"
                    errors.append(f"第{row_number}行：{error_msg}")
                    # 转换行数据为字典，处理NaN值
                    row_data_dict = {}
                    for k, v in row_data.items():
                        if pd.isna(v) or v is None:
                            row_data_dict[k] = ''
                        else:
                            row_data_dict[k] = str(v)
                    error_details.append({
                        "row_number": row_number,
                        "error_message": error_msg,
                        "row_data": row_data_dict
                    })
                    continue
                
                # 按EHR号查库（含已逻辑删除）：未删除则报已存在，已删除则恢复并更新
                existing_user = db.query(User).filter(User.ehr_number == ehr_number).first()
                if existing_user and existing_user.deleted_at is None:
                    error_count += 1
                    error_msg = f"EHR号{ehr_number}已存在"
                    errors.append(f"第{row_number}行：{error_msg}")
                    row_data_dict = {k: '' if pd.isna(v) or v is None else str(v) for k, v in row_data.items()}
                    error_details.append({"row_number": row_number, "error_message": error_msg, "row_data": row_data_dict})
                    continue
                
                if existing_user and existing_user.deleted_at is not None:
                    # 存在且已逻辑删除：恢复并用本行 Excel 更新
                    existing_user.deleted_at = None
                    existing_user.deleted_by_id = None
                    existing_user.real_name = real_name
                    existing_user.group = group
                    existing_user.role = role
                    existing_user.status = status
                    existing_user.password_hash = get_password_hash(password)
                    success_count += 1
                    continue
                
                # 不存在：创建用户
                hashed_password = get_password_hash(password)
                db_user = User(
                    ehr_number=ehr_number,
                    real_name=real_name,
                    group=group,
                    role=role,
                    status=status,
                    password_hash=hashed_password
                )
                db.add(db_user)
                success_count += 1
                
            except Exception as e:
                error_count += 1
                error_msg = str(e)
                errors.append(f"第{row_number}行：{error_msg}")
                # 转换行数据为字典，处理NaN值
                row_data_dict = {}
                for k, v in row_data.items():
                    if pd.isna(v) or v is None:
                        row_data_dict[k] = ''
                    else:
                        row_data_dict[k] = str(v)
                error_details.append({
                    "row_number": row_number,
                    "error_message": error_msg,
                    "row_data": row_data_dict
                })
        
        db.commit()
        
        # 限制返回的错误数量
        max_errors = 100
        limited_errors = errors[:max_errors]
        limited_error_details = error_details[:max_errors]
        
        return ImportResponse(
            success_count=success_count,
            error_count=error_count,
            errors=limited_errors,
            error_details=limited_error_details
        )
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"导入失败：{str(e)}")
