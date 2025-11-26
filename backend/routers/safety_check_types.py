"""
安全检查类型管理路由
仅管理员可以管理检查类型
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models import SafetyCheckType, User
from schemas import (
    SafetyCheckTypeCreate, 
    SafetyCheckTypeUpdate, 
    SafetyCheckTypeResponse
)
from auth import get_current_admin_user
import json

router = APIRouter()


@router.get("/", response_model=List[SafetyCheckTypeResponse])
async def get_check_types(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """获取所有检查类型列表（仅管理员）"""
    check_types = db.query(SafetyCheckType).order_by(SafetyCheckType.created_at.desc()).all()
    result = []
    for ct in check_types:
        ct_dict = SafetyCheckTypeResponse.model_validate(ct).model_dump()
        # 解析check_items JSON
        if ct.check_items:
            try:
                ct_dict["check_items"] = json.loads(ct.check_items)
            except:
                ct_dict["check_items"] = []
        else:
            ct_dict["check_items"] = []
        result.append(SafetyCheckTypeResponse(**ct_dict))
    return result


@router.get("/{check_type_id}", response_model=SafetyCheckTypeResponse)
async def get_check_type(
    check_type_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """获取指定检查类型"""
    check_type = db.query(SafetyCheckType).filter(SafetyCheckType.id == check_type_id).first()
    if not check_type:
        raise HTTPException(status_code=404, detail="检查类型不存在")
    
    ct_dict = SafetyCheckTypeResponse.model_validate(check_type).model_dump()
    # 解析check_items JSON
    if check_type.check_items:
        try:
            ct_dict["check_items"] = json.loads(check_type.check_items)
        except:
            ct_dict["check_items"] = []
    else:
        ct_dict["check_items"] = []
    return SafetyCheckTypeResponse(**ct_dict)


@router.post("/", response_model=SafetyCheckTypeResponse)
async def create_check_type(
    check_type_data: SafetyCheckTypeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """创建检查类型"""
    # 检查名称是否已存在
    existing = db.query(SafetyCheckType).filter(SafetyCheckType.name == check_type_data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="检查类型名称已存在")
    
    # 创建检查类型
    db_check_type = SafetyCheckType(
        name=check_type_data.name,
        description=check_type_data.description,
        is_active=check_type_data.is_active,
        created_by_id=current_user.id
    )
    
    # 设置检查项列表（转换为JSON）
    if check_type_data.check_items:
        items_list = [{"item": item.item, "required": item.required} for item in check_type_data.check_items]
        db_check_type.set_check_items(items_list)
    
    db.add(db_check_type)
    db.commit()
    db.refresh(db_check_type)
    
    # 返回结果
    ct_dict = SafetyCheckTypeResponse.model_validate(db_check_type).model_dump()
    if db_check_type.check_items:
        try:
            ct_dict["check_items"] = json.loads(db_check_type.check_items)
        except:
            ct_dict["check_items"] = []
    else:
        ct_dict["check_items"] = []
    return SafetyCheckTypeResponse(**ct_dict)


@router.put("/{check_type_id}", response_model=SafetyCheckTypeResponse)
async def update_check_type(
    check_type_id: int,
    check_type_data: SafetyCheckTypeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """更新检查类型"""
    check_type = db.query(SafetyCheckType).filter(SafetyCheckType.id == check_type_id).first()
    if not check_type:
        raise HTTPException(status_code=404, detail="检查类型不存在")
    
    # 如果更新名称，检查是否重复
    if check_type_data.name and check_type_data.name != check_type.name:
        existing = db.query(SafetyCheckType).filter(
            SafetyCheckType.name == check_type_data.name,
            SafetyCheckType.id != check_type_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="检查类型名称已存在")
        check_type.name = check_type_data.name
    
    if check_type_data.description is not None:
        check_type.description = check_type_data.description
    if check_type_data.is_active is not None:
        check_type.is_active = check_type_data.is_active
    if check_type_data.check_items is not None:
        items_list = [{"item": item.item, "required": item.required} for item in check_type_data.check_items]
        check_type.set_check_items(items_list)
    
    db.commit()
    db.refresh(check_type)
    
    # 返回结果
    ct_dict = SafetyCheckTypeResponse.model_validate(check_type).model_dump()
    if check_type.check_items:
        try:
            ct_dict["check_items"] = json.loads(check_type.check_items)
        except:
            ct_dict["check_items"] = []
    else:
        ct_dict["check_items"] = []
    return SafetyCheckTypeResponse(**ct_dict)


@router.delete("/{check_type_id}")
async def delete_check_type(
    check_type_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """删除检查类型（软删除：设置为停用）"""
    check_type = db.query(SafetyCheckType).filter(SafetyCheckType.id == check_type_id).first()
    if not check_type:
        raise HTTPException(status_code=404, detail="检查类型不存在")
    
    # 检查是否有任务使用此类型
    from models import SafetyCheckTask
    task_count = db.query(SafetyCheckTask).filter(SafetyCheckTask.check_type_id == check_type_id).count()
    if task_count > 0:
        raise HTTPException(status_code=400, detail="该检查类型已被使用，无法删除。请先停用。")
    
    # 软删除：设置为停用
    check_type.is_active = False
    db.commit()
    
    return {"message": "检查类型已停用"}

