"""
安全检查结果提交路由
普通用户提交检查结果
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from database import get_db
from models import (
    TaskAsset, SafetyCheckTask, SafetyCheckType, SafetyCheckHistory, Asset, User
)
from schemas import (
    SafetyCheckResultSubmit, SafetyCheckHistoryResponse, TaskAssetResponse
)
from auth import get_current_user
import json

router = APIRouter()


@router.get("/my-tasks", response_model=dict)
async def get_my_tasks(
    status: Optional[str] = Query(None, description="状态筛选：pending/checked"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取我的待检查任务"""
    query = db.query(SafetyCheckTask).join(TaskAsset).filter(
        TaskAsset.assigned_user_id == current_user.id,
        SafetyCheckTask.status != "cancelled"
    ).distinct()
    
    if status:
        if status == "pending":
            query = query.filter(TaskAsset.status == "pending")
        elif status == "checked":
            query = query.filter(TaskAsset.status == "checked")
    
    tasks = query.order_by(SafetyCheckTask.created_at.desc()).all()
    
    items = []
    for task in tasks:
        # 统计当前用户在此任务中的资产数量（排除已退库的）
        my_assets = db.query(TaskAsset).filter(
            TaskAsset.task_id == task.id,
            TaskAsset.assigned_user_id == current_user.id,
            TaskAsset.status != "returned"  # 排除已退库的资产
        ).all()
        
        pending_count = len([ta for ta in my_assets if ta.status == "pending"])
        
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
        
        items.append({
            "task_id": task.id,
            "task_number": task.task_number,
            "task_title": task.title,
            "check_type": check_type_dict,
            "pending_count": pending_count,
            "deadline": task.deadline
        })
    
    return {
        "total": len(items),
        "items": items
    }


@router.get("/task/{task_id}/assets", response_model=dict)
async def get_task_assets_for_user(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取任务中分配给当前用户的资产"""
    task = db.query(SafetyCheckTask).filter(SafetyCheckTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 验证用户是否有权限访问此任务
    has_access = db.query(TaskAsset).filter(
        TaskAsset.task_id == task_id,
        TaskAsset.assigned_user_id == current_user.id
    ).first()
    if not has_access:
        raise HTTPException(status_code=403, detail="无权访问此任务")
    
    # 获取分配给当前用户的资产（排除已退库的）
    task_assets = db.query(TaskAsset).filter(
        TaskAsset.task_id == task_id,
        TaskAsset.assigned_user_id == current_user.id,
        TaskAsset.status != "returned"  # 排除已退库的资产
    ).all()
    
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
        "task": {
            "id": task.id,
            "task_number": task.task_number,
            "title": task.title,
            "description": task.description,
            "deadline": task.deadline
        },
        "check_type": check_type_dict,
        "assets": assets
    }


@router.post("/submit")
async def submit_check_result(
    result_data: SafetyCheckResultSubmit,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """提交检查结果"""
    # 验证任务资产关联是否存在
    task_asset = db.query(TaskAsset).filter(TaskAsset.id == result_data.task_asset_id).first()
    if not task_asset:
        raise HTTPException(status_code=404, detail="任务资产关联不存在")
    
    # 验证是否分配给当前用户
    if task_asset.assigned_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权提交此资产的检查结果")
    
    # 验证任务状态
    task = db.query(SafetyCheckTask).filter(SafetyCheckTask.id == task_asset.task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    if task.status == "completed":
        raise HTTPException(status_code=400, detail="任务已完成，无法提交检查结果")
    if task.status == "cancelled":
        raise HTTPException(status_code=400, detail="任务已取消，无法提交检查结果")
    
    # 验证检查结果
    if result_data.check_result not in ["yes", "no"]:
        raise HTTPException(status_code=400, detail="检查结果必须是yes或no")
    
    # 获取检查类型，验证必填项
    check_type = db.query(SafetyCheckType).filter(SafetyCheckType.id == task.check_type_id).first()
    if check_type and check_type.check_items:
        try:
            check_items = json.loads(check_type.check_items)
            required_items = [item["item"] for item in check_items if item.get("required", False)]
            submitted_items = [item.item for item in result_data.check_items_result]
            
            # 检查必填项是否都已提交
            for required_item in required_items:
                if required_item not in submitted_items:
                    raise HTTPException(status_code=400, detail=f"必填检查项'{required_item}'未填写")
        except json.JSONDecodeError:
            pass
    
    # 验证检查项结果
    for item_result in result_data.check_items_result:
        if item_result.result not in ["yes", "no"]:
            raise HTTPException(status_code=400, detail="检查项结果必须是yes或no")
    
    # 更新任务资产关联记录
    task_asset.status = "checked"
    task_asset.check_result = result_data.check_result
    task_asset.check_comment = result_data.check_comment
    task_asset.checked_at = datetime.now()
    
    # 保存检查项结果
    items_result = [
        {
            "item": item.item,
            "result": item.result,
            "comment": item.comment
        }
        for item in result_data.check_items_result
    ]
    task_asset.set_check_items_result(items_result)
    
    db.flush()
    
    # 创建检查历史记录
    history = SafetyCheckHistory(
        task_id=task.id,
        task_asset_id=task_asset.id,
        asset_id=task_asset.asset_id,
        check_type_id=task.check_type_id,
        checked_by_id=current_user.id,
        check_result=result_data.check_result,
        check_comment=result_data.check_comment,
        checked_at=datetime.now()
    )
    history.set_check_items_result(items_result)
    db.add(history)
    
    # 检查任务是否全部完成（排除已退库的资产）
    # 只有当所有非退库的资产都完成时，任务才算完成
    pending_count = db.query(TaskAsset).filter(
        TaskAsset.task_id == task.id,
        TaskAsset.status == "pending"
    ).count()
    
    if pending_count == 0:
        task.status = "completed"
        task.completed_at = datetime.now()
    
    db.commit()
    
    return {"message": "检查结果提交成功"}


@router.get("/asset/{asset_id}/history", response_model=dict)
async def get_asset_check_history(
    asset_id: int,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取资产检查历史"""
    # 验证资产是否存在
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="资产不存在")
    
    # 普通用户只能查看自己资产的检查历史
    if current_user.role != "admin" and asset.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权查看此资产的检查历史")
    
    # 查询检查历史
    query = db.query(SafetyCheckHistory).filter(SafetyCheckHistory.asset_id == asset_id)
    total = query.count()
    
    histories = query.order_by(SafetyCheckHistory.checked_at.desc()).offset((page - 1) * limit).limit(limit).all()
    
    items = []
    for history in histories:
        # 获取任务编号
        task = db.query(SafetyCheckTask).filter(SafetyCheckTask.id == history.task_id).first()
        task_number = task.task_number if task else None
        
        # 获取检查类型
        check_type = db.query(SafetyCheckType).filter(SafetyCheckType.id == history.check_type_id).first()
        check_type_dict = None
        if check_type:
            from schemas import SafetyCheckTypeResponse
            check_type_dict = SafetyCheckTypeResponse.model_validate(check_type).model_dump()
        
        history_dict = SafetyCheckHistoryResponse.model_validate(history).model_dump()
        history_dict["task_number"] = task_number
        history_dict["check_type"] = check_type_dict
        
        # 解析检查项结果
        if history.check_items_result:
            try:
                history_dict["check_items_result"] = json.loads(history.check_items_result)
            except:
                history_dict["check_items_result"] = []
        else:
            history_dict["check_items_result"] = []
        
        items.append(SafetyCheckHistoryResponse(**history_dict))
    
    return {
        "total": total,
        "page": page,
        "limit": limit,
        "items": items
    }

