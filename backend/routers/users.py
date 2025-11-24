"""
用户管理路由
包括用户的增删改查、批量导入等
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional
from database import get_db
from models import User
from schemas import UserCreate, UserUpdate, UserResponse, ImportResponse
from auth import get_current_user, get_current_admin_user, get_password_hash
import pandas as pd
import io

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
    limit: int = 100,
    search: Optional[str] = Query(None, description="搜索关键词，支持模糊搜索所有字段"),
    role: Optional[str] = Query(None, description="按角色筛选"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取用户列表（所有已登录用户可访问，用于选择转入用户等场景），支持搜索"""
    query = db.query(User)
    
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
    
    users = query.offset(skip).limit(limit).all()
    return [UserResponse.model_validate(user) for user in users]


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取指定用户信息"""
    user = db.query(User).filter(User.id == user_id).first()
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
    # 检查EHR号是否已存在
    existing_user = db.query(User).filter(User.ehr_number == user_data.ehr_number).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="EHR号已存在")
    
    # 创建新用户
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        ehr_number=user_data.ehr_number,
        real_name=user_data.real_name,
        group=user_data.group,
        role=user_data.role,
        password_hash=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return UserResponse.model_validate(db_user)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """更新用户信息（仅管理员）"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 更新字段
    if user_data.real_name is not None:
        user.real_name = user_data.real_name
    if user_data.group is not None:
        user.group = user_data.group
    if user_data.role is not None:
        user.role = user_data.role
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
    """删除用户（仅管理员）"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 禁止删除"仓库"用户（EHR号为1000000）
    if user.ehr_number == "1000000":
        raise HTTPException(status_code=400, detail="不能删除仓库用户")
    
    db.delete(user)
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
        
        for index, row in df.iterrows():
            try:
                ehr_number = str(row['EHR号']).strip()
                real_name = str(row['姓名']).strip()
                group = str(row['组别']).strip()
                role = str(row.get('角色', 'user')).strip() if '角色' in df.columns else 'user'
                password = str(row.get('密码', '123456')).strip() if '密码' in df.columns else '123456'
                
                # 验证EHR号
                if len(ehr_number) != 7 or not ehr_number.isdigit():
                    error_count += 1
                    errors.append(f"第{index+2}行：EHR号格式错误（必须为7位数字）")
                    continue
                
                # 检查EHR号是否已存在
                existing_user = db.query(User).filter(User.ehr_number == ehr_number).first()
                if existing_user:
                    error_count += 1
                    errors.append(f"第{index+2}行：EHR号{ehr_number}已存在")
                    continue
                
                # 创建用户
                hashed_password = get_password_hash(password)
                db_user = User(
                    ehr_number=ehr_number,
                    real_name=real_name,
                    group=group,
                    role=role,
                    password_hash=hashed_password
                )
                db.add(db_user)
                success_count += 1
                
            except Exception as e:
                error_count += 1
                errors.append(f"第{index+2}行：{str(e)}")
        
        db.commit()
        
        return ImportResponse(
            success_count=success_count,
            error_count=error_count,
            errors=errors[:50]  # 最多返回50个错误
        )
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"导入失败：{str(e)}")



