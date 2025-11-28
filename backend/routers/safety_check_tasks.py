"""
安全检查任务管理路由
管理员可以创建和管理任务，普通用户可以查看分配给自己的任务
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import List, Optional
from datetime import datetime
from database import get_db
from models import (
    SafetyCheckTask, SafetyCheckType, TaskAsset, Asset, User
)
from schemas import (
    SafetyCheckTaskCreate, SafetyCheckTaskUpdate, SafetyCheckTaskResponse,
    TaskAssetResponse
)
from auth import get_current_user, get_current_admin_user
import json

router = APIRouter()


def generate_task_number(db: Session) -> str:
    """生成任务编号：SAFETY-YYYY-NNN"""
    year = datetime.now().year
    # 查询今年已有的任务数量
    count = db.query(SafetyCheckTask).filter(
        SafetyCheckTask.task_number.like(f"SAFETY-{year}-%")
    ).count()
    number = f"SAFETY-{year}-{str(count + 1).zfill(3)}"
    return number


@router.post("/", response_model=SafetyCheckTaskResponse)
async def create_task(
    task_data: SafetyCheckTaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """创建安全检查任务（仅管理员）"""
    # 验证检查类型是否存在且启用
    check_type = db.query(SafetyCheckType).filter(
        SafetyCheckType.id == task_data.check_type_id,
        SafetyCheckType.is_active == True
    ).first()
    if not check_type:
        raise HTTPException(status_code=404, detail="检查类型不存在或已停用")
    
    # 验证资产是否存在且未删除
    assets = db.query(Asset).filter(
        Asset.id.in_(task_data.asset_ids),
        Asset.deleted_at.is_(None)
    ).all()
    if len(assets) != len(task_data.asset_ids):
        raise HTTPException(status_code=400, detail="部分资产不存在或已删除")
    
    # 生成任务编号
    task_number = generate_task_number(db)
    
    # 创建任务
    db_task = SafetyCheckTask(
        task_number=task_number,
        check_type_id=task_data.check_type_id,
        title=task_data.title,
        description=task_data.description,
        deadline=task_data.deadline,
        created_by_id=current_user.id,
        status="pending"
    )
    db.add(db_task)
    db.flush()  # 获取任务ID
    
    # 为每个资产创建任务资产关联记录
    created_count = 0
    skipped_count = 0
    for asset in assets:
        # 如果资产没有使用人，跳过该资产
        if not asset.user_id:
            skipped_count += 1
            continue
        
        # 创建任务资产关联
        task_asset = TaskAsset(
            task_id=db_task.id,
            asset_id=asset.id,
            assigned_user_id=asset.user_id,
            status="pending"
        )
        db.add(task_asset)
        created_count += 1
    
    if created_count == 0:
        db.rollback()
        raise HTTPException(status_code=400, detail="所选资产都没有使用人，无法创建任务")
    
    db.commit()
    db.refresh(db_task)
    
    # 返回任务详情
    return await get_task_detail(db_task.id, db, current_user)


@router.get("/", response_model=dict)
async def get_tasks(
    status: Optional[str] = Query(None, description="任务状态筛选"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取任务列表"""
    query = db.query(SafetyCheckTask)
    
    # 普通用户只能查看分配给自己的任务
    if current_user.role != "admin":
        # 查询分配给当前用户的任务
        query = query.join(TaskAsset).filter(
            TaskAsset.assigned_user_id == current_user.id
        ).distinct()
    
    # 状态筛选
    if status:
        query = query.filter(SafetyCheckTask.status == status)
    
    # 总数
    total = query.count()
    
    # 分页
    tasks = query.order_by(SafetyCheckTask.created_at.desc()).offset((page - 1) * limit).limit(limit).all()
    
    items = []
    tasks_to_update = []  # 需要更新状态的任务列表
    
    for task in tasks:
        task_dict = SafetyCheckTaskResponse.model_validate(task).model_dump()
        
        # 统计资产数量
        if current_user.role == "admin":
            # 管理员：显示所有资产统计（已退库的资产不纳入进度统计）
            completed_assets = db.query(TaskAsset).filter(
                TaskAsset.task_id == task.id,
                TaskAsset.status == "checked"
            ).count()
            returned_assets = db.query(TaskAsset).filter(
                TaskAsset.task_id == task.id,
                TaskAsset.status == "returned"
            ).count()
            pending_assets = db.query(TaskAsset).filter(
                TaskAsset.task_id == task.id,
                TaskAsset.status == "pending"
            ).count()
            # 总资产数 = 已完成 + 待检查（排除已退库的）
            total_assets = completed_assets + pending_assets
            task_dict["total_assets"] = total_assets
            task_dict["completed_assets"] = completed_assets
            task_dict["pending_assets"] = pending_assets
            task_dict["returned_assets"] = returned_assets
            
            # 如果进度为100%，标记需要更新任务状态为"已完成"
            if total_assets > 0 and completed_assets == total_assets and task.status != "completed":
                tasks_to_update.append(task)
                task_dict["status"] = "completed"
                if task.completed_at:
                    task_dict["completed_at"] = task.completed_at
                else:
                    task_dict["completed_at"] = datetime.now()
        else:
            # 普通用户：显示自己的资产统计（排除已退库的）
            my_assets = db.query(TaskAsset).filter(
                TaskAsset.task_id == task.id,
                TaskAsset.assigned_user_id == current_user.id,
                TaskAsset.status != "returned"  # 排除已退库的资产
            ).all()
            my_assets_count = len(my_assets)
            my_completed_count = len([ta for ta in my_assets if ta.status == "checked"])
            task_dict["my_assets_count"] = my_assets_count
            task_dict["my_completed_count"] = my_completed_count
        
        items.append(SafetyCheckTaskResponse(**task_dict))
    
    # 批量更新任务状态
    if tasks_to_update:
        for task in tasks_to_update:
            task.status = "completed"
            if not task.completed_at:
                task.completed_at = datetime.now()
        db.commit()
    
    return {
        "total": total,
        "page": page,
        "limit": limit,
        "items": items
    }


@router.get("/{task_id}", response_model=SafetyCheckTaskResponse)
async def get_task_detail(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取任务详情"""
    task = db.query(SafetyCheckTask).filter(SafetyCheckTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 普通用户只能查看分配给自己的任务
    if current_user.role != "admin":
        has_access = db.query(TaskAsset).filter(
            TaskAsset.task_id == task_id,
            TaskAsset.assigned_user_id == current_user.id
        ).first()
        if not has_access:
            raise HTTPException(status_code=403, detail="无权访问此任务")
    
    task_dict = SafetyCheckTaskResponse.model_validate(task).model_dump()
    
    # 统计资产数量
    if current_user.role == "admin":
        # 管理员：显示所有资产统计（已退库的资产不纳入进度统计）
        completed_assets = db.query(TaskAsset).filter(
            TaskAsset.task_id == task_id,
            TaskAsset.status == "checked"
        ).count()
        returned_assets = db.query(TaskAsset).filter(
            TaskAsset.task_id == task_id,
            TaskAsset.status == "returned"
        ).count()
        pending_assets = db.query(TaskAsset).filter(
            TaskAsset.task_id == task_id,
            TaskAsset.status == "pending"
        ).count()
        # 总资产数 = 已完成 + 待检查（排除已退库的）
        total_assets = completed_assets + pending_assets
        task_dict["total_assets"] = total_assets
        task_dict["completed_assets"] = completed_assets
        task_dict["pending_assets"] = pending_assets
        task_dict["returned_assets"] = returned_assets
        
        # 如果进度为100%，自动更新任务状态为"已完成"
        if total_assets > 0 and completed_assets == total_assets and task.status != "completed":
            task.status = "completed"
            if not task.completed_at:
                task.completed_at = datetime.now()
            db.commit()
            task_dict["status"] = "completed"
            task_dict["completed_at"] = task.completed_at
    else:
        my_assets = db.query(TaskAsset).filter(
            TaskAsset.task_id == task_id,
            TaskAsset.assigned_user_id == current_user.id,
            TaskAsset.status != "returned"  # 排除已退库的资产
        ).all()
        my_assets_count = len(my_assets)
        my_completed_count = len([ta for ta in my_assets if ta.status == "checked"])
        task_dict["my_assets_count"] = my_assets_count
        task_dict["my_completed_count"] = my_completed_count
    
    return SafetyCheckTaskResponse(**task_dict)


@router.get("/{task_id}/assets", response_model=dict)
async def get_task_assets(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取任务资产列表"""
    task = db.query(SafetyCheckTask).filter(SafetyCheckTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 普通用户只能查看分配给自己的资产（排除已退库的）
    query = db.query(TaskAsset).filter(TaskAsset.task_id == task_id)
    if current_user.role != "admin":
        query = query.filter(
            TaskAsset.assigned_user_id == current_user.id,
            TaskAsset.status != "returned"  # 排除已退库的资产
        )
    
    task_assets = query.all()
    
    assets = []
    for ta in task_assets:
        # 先手动构建字典，解析 JSON 字符串，避免 Pydantic 验证错误
        ta_dict = {
            "id": ta.id,
            "task_id": ta.task_id,
            "asset_id": ta.asset_id,
            "assigned_user_id": ta.assigned_user_id,
            "status": ta.status,
            "check_result": ta.check_result,
            "check_comment": ta.check_comment,
            "checked_at": ta.checked_at,
            "created_at": ta.created_at,
            "updated_at": ta.updated_at,
            "asset": ta.asset,
            "assigned_user": ta.assigned_user
        }
        # 解析检查项结果
        if ta.check_items_result:
            try:
                ta_dict["check_items_result"] = json.loads(ta.check_items_result)
            except:
                ta_dict["check_items_result"] = []
        else:
            ta_dict["check_items_result"] = []
        assets.append(TaskAssetResponse(**ta_dict))
    
    # 获取检查类型信息
    check_type = db.query(SafetyCheckType).filter(SafetyCheckType.id == task.check_type_id).first()
    check_type_dict = None
    if check_type:
        from schemas import SafetyCheckTypeResponse
        check_type_dict = SafetyCheckTypeResponse.model_validate(check_type).model_dump()
        if check_type.check_items:
            try:
                check_type_dict["check_items"] = json.loads(check_type.check_items)
            except:
                check_type_dict["check_items"] = []
        else:
            check_type_dict["check_items"] = []
    
    return {
        "task": SafetyCheckTaskResponse.model_validate(task).model_dump(),
        "check_type": check_type_dict,
        "assets": assets
    }


@router.put("/{task_id}", response_model=SafetyCheckTaskResponse)
async def update_task(
    task_id: int,
    task_data: SafetyCheckTaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """更新任务（仅管理员）"""
    task = db.query(SafetyCheckTask).filter(SafetyCheckTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    if task_data.title:
        task.title = task_data.title
    if task_data.description is not None:
        task.description = task_data.description
    if task_data.deadline is not None:
        task.deadline = task_data.deadline
    if task_data.status:
        task.status = task_data.status
        if task_data.status == "completed":
            task.completed_at = datetime.now()
    
    db.commit()
    db.refresh(task)
    
    return await get_task_detail(task_id, db, current_user)


@router.delete("/{task_id}")
async def cancel_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """取消任务（仅管理员）"""
    task = db.query(SafetyCheckTask).filter(SafetyCheckTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    if task.status == "completed":
        raise HTTPException(status_code=400, detail="已完成的任务不能取消")
    
    task.status = "cancelled"
    db.commit()
    
    return {"message": "任务已取消"}

