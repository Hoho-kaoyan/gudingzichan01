"""
资产交接路由
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from typing import List, Optional
from database import get_db
from models import TransferRequest, Asset, User, SafetyCheckTask
from schemas import TransferRequestCreate, TransferRequestResponse, TransferConfirmationRequest
from auth import get_current_user
from logger import logger
from utils_time import now_east8, now_utc_naive
# 延迟导入避免循环依赖
def get_create_history_record():
    from routers import asset_history
    return asset_history.create_history_record

def check_unfinished_tasks_for_asset_user(db: Session, asset_id: int, user_id: int):
    """
    检查指定资产的当前持有人是否存在未完成的安全检查任务。
    如果有状态为 pending 或 overdue 的任务，则抛出 HTTPException 400。
    """
    from models import TaskAsset
    unfinished = db.query(TaskAsset).filter(
        TaskAsset.asset_id == asset_id,
        TaskAsset.assigned_user_id == user_id,
        TaskAsset.status.in_(["pending", "overdue"])
    ).first()

    if unfinished:
        raise HTTPException(
            status_code=400, 
            detail="请先由当前所有人完成数据安全检查"
        )

def check_any_unfinished_tasks_for_user(db: Session, user_id: int):
    """
    全局检查：只要该用户在名下任何资产中存在任意一笔未完成的安检单（pending/overdue），
    直接判定不合规并抛出拦截。
    """
    from models import TaskAsset
    unfinished = db.query(TaskAsset).filter(
        TaskAsset.assigned_user_id == user_id,
        TaskAsset.status.in_(["pending", "overdue"])
    ).first()
    if unfinished:
        raise HTTPException(
            status_code=400, 
            detail="您有未完成的数据安检要求，请先处理后重试"
        )


def _pending_linked_safety_check(db: Session, req: TransferRequest) -> bool:
    """若该交接单关联的联动安检任务存在且未完成（pending/overdue），返回 True"""
    task_id = getattr(req, "linked_safety_task_id", None)
    if not task_id:
        return False
    task = db.query(SafetyCheckTask).filter(SafetyCheckTask.id == task_id).first()
    return bool(task and task.status in ("pending", "overdue"))


def _build_transfer_response(db: Session, req: TransferRequest) -> TransferRequestResponse:
    """构建交接单响应（含 pending_linked_safety_check）"""
    data = TransferRequestResponse.model_validate(req).model_dump()
    data["pending_linked_safety_check"] = _pending_linked_safety_check(db, req)
    return TransferRequestResponse(**data)


router = APIRouter()


@router.get("/", response_model=List[TransferRequestResponse])
async def get_transfer_requests(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    search: Optional[str] = Query(None, description="搜索关键词,支持模糊搜索所有字段"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取交接申请列表,支持搜索"""
    query = db.query(TransferRequest)
    
    # 普通用户/组长权限过滤
    if current_user.role == "leader":
        # 组长可以看到本组用户作为转出人或转入人的所有申请
        # 简化逻辑：获取本组所有用户的ID列表，然后过滤
        user_ids_in_group = [u[0] for u in db.query(User.id).filter(User.group == current_user.group).all()]
        query = query.filter(
            or_(
                TransferRequest.from_user_id.in_(user_ids_in_group),
                TransferRequest.to_user_id.in_(user_ids_in_group)
            )
        )
    elif current_user.role == "user":

        # 普通用户只能看到自己相关的申请
        query = query.filter(
            (TransferRequest.from_user_id == current_user.id) |
            (TransferRequest.to_user_id == current_user.id)
        )
    
    if status:
        query = query.filter(TransferRequest.status == status)
    
    # 支持模糊搜索所有字段
    if search:
        # 先获取所有相关的资产ID
        asset_results = db.query(Asset.id).filter(
            or_(
                Asset.asset_number.contains(search),
                Asset.name.contains(search),
                Asset.specification.contains(search),
                Asset.mac_address.contains(search),
                Asset.ip_address.contains(search),
                Asset.office_location.contains(search),
                Asset.floor.contains(search)
            )
        ).all()
        asset_ids = [row[0] for row in asset_results]
        
        # 获取匹配的用户ID（不含已逻辑删除用户）
        user_results = db.query(User.id).filter(
            User.deleted_at.is_(None),
            or_(
                User.real_name.contains(search),
                User.ehr_number.contains(search),
                User.group.contains(search)
            )
        ).all()
        user_ids = [row[0] for row in user_results]
        
        # 构建搜索条件
        search_conditions = [TransferRequest.reason.contains(search)]
        
        if asset_ids:
            search_conditions.append(TransferRequest.asset_id.in_(asset_ids))
        if user_ids:
            search_conditions.append(
                or_(
                    TransferRequest.from_user_id.in_(user_ids),
                    TransferRequest.to_user_id.in_(user_ids)
                )
            )
        
        if search_conditions:
            query = query.filter(or_(*search_conditions))
    
    requests = query.options(
        joinedload(TransferRequest.asset),
        joinedload(TransferRequest.from_user),
        joinedload(TransferRequest.to_user),
        joinedload(TransferRequest.approver)
    ).order_by(TransferRequest.created_at.desc()).offset(skip).limit(limit).all()
    return [_build_transfer_response(db, req) for req in requests]


@router.get("/{request_id}", response_model=TransferRequestResponse)
async def get_transfer_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取指定交接申请"""
    request = db.query(TransferRequest).filter(TransferRequest.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="交接申请不存在")
    
    # 权限检查：普通用户只能查看自己相关的申请
    if current_user.role != "admin":
        if request.from_user_id != current_user.id and request.to_user_id != current_user.id:
            raise HTTPException(status_code=403, detail="无权查看此申请")
    
    return _build_transfer_response(db, request)


@router.post("/", response_model=TransferRequestResponse)
async def create_transfer_request(
    transfer_data: TransferRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建资产交接申请"""
    # 检查资产是否存在（只查询未删除的）
    asset = db.query(Asset).filter(
        Asset.id == transfer_data.asset_id,
        Asset.deleted_at.is_(None)
    ).first()
    if not asset:
        raise HTTPException(status_code=404, detail="资产不存在")
    
    # 检查资产是否在使用中
    if asset.status != "在用":
        raise HTTPException(status_code=400, detail="只能交接在用状态的资产")
    
    # 检查转入用户是否存在
    to_user = db.query(User).filter(User.id == transfer_data.to_user_id).first()
    if not to_user:
        raise HTTPException(status_code=404, detail="转入用户不存在")
    
    # 确定转出用户（资产的使用人或当前用户）
    from_user_id = asset.user_id or current_user.id
    
    # 检查不能转给自己
    if from_user_id == transfer_data.to_user_id:
        raise HTTPException(status_code=400, detail="不能将资产转给自己")
    
    # 检查权限：
    # 1. 管理员：可以代任何人发起
    # 2. 组长：交接自己名下资产时与普通用户一致，可转给所有用户（含管理员）；交接组内他人资产时，接收人须为本组成员
    # 3. 普通用户：只能为自己发起
    if current_user.role == "admin":
        pass 
    elif current_user.role == "leader":
        # 验证转出资产是否属于本组
        if asset.user_group != current_user.group:
            raise HTTPException(status_code=403, detail="组长只能交接本组关联的资产")
        # 组长交接自己名下资产：与普通用户一致，可转给任何人（含管理员）；交接组内他人资产时，接收人须为本组
        if asset.user_id != current_user.id:
            if to_user.group != current_user.group:
                raise HTTPException(status_code=403, detail="组长只能将资产交接给本组人员")
    else:
        # 普通用户只能交接自己的资产
        if asset.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="只能交接自己名下的资产")

    # 【创建交接前：只查本单资产是否已完成安检】
    check_unfinished_tasks_for_asset_user(db, asset.id, from_user_id)
    
    # 创建交接申请，初始状态为待转入人确认
    db_request = TransferRequest(
        asset_id=transfer_data.asset_id,
        from_user_id=from_user_id,
        to_user_id=transfer_data.to_user_id,
        created_by_id=current_user.id,  # 记录实际创建申请的用户
        reason=transfer_data.reason,
        status="waiting_confirmation"  # 初始状态：待转入人确认
    )
    db.add(db_request)
    db.flush()  # 先flush获取ID
    
    # 获取转出和转入用户信息
    from_user = db.query(User).filter(User.id == from_user_id).first()
    to_user = db.query(User).filter(User.id == transfer_data.to_user_id).first()
    
    logger.info(f"用户 {current_user.ehr_number}({current_user.real_name}) 创建资产交接申请: 资产ID {asset.id}({asset.asset_number}), 从 {from_user.real_name if from_user else ''} 转给 {to_user.real_name if to_user else ''}")
    
    # 【干预点1 发放：顺利建单后（此刻没有未完成任务），自动下发一份针对本次交接的专属检查任务（优先使用资产的检查执行人ID，否则转出人）】
    try:
        from safety_check_linkage import create_system_allocated_task
        assigned_id = getattr(asset, "safety_check_executor_id", None) or from_user_id
        task = create_system_allocated_task(
            db=db,
            asset_id=asset.id,
            assigned_user_id=assigned_id,
            source="transfer"
        )
        if task:
            db_request.linked_safety_task_id = task.id
    except Exception as e:
        logger.error(f"下发交接核验任务失败: {e}", exc_info=True)

    # 记录交接申请历史
    try:
        create_history = get_create_history_record()
        create_history(
            db=db,
            asset_id=transfer_data.asset_id,
            action_type="transfer",
            action_description=f"申请资产交接：从 {from_user.real_name if from_user else ''} 转给 {to_user.real_name if to_user else ''}",
            operator_id=current_user.id,
            old_value={"user_id": from_user_id, "user_name": from_user.real_name if from_user else ""},
            new_value={"user_id": transfer_data.to_user_id, "user_name": to_user.real_name if to_user else ""},
            related_request_id=db_request.id,
            related_request_type="transfer"
        )
    except Exception as e:
        logger.error(f"记录交接历史失败: {e}", exc_info=True)
    
    db.commit()
    db.refresh(db_request)
    return _build_transfer_response(db, db_request)


@router.delete("/{request_id}")
async def cancel_transfer_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """撤回资产交接申请（仅转出用户可以撤回,且只能撤回待确认或待审批状态的申请）"""
    request = db.query(TransferRequest).filter(TransferRequest.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="交接申请不存在")
    
    # 检查申请状态,只能撤回待确认或待审批的申请
    if request.status not in ["waiting_confirmation", "pending"]:
        raise HTTPException(status_code=400, detail="只能撤回待确认或待审批状态的申请")
    
    # 检查权限：只有创建申请的用户可以撤回（管理员也可以）
    # 如果是管理员代为申请,created_by_id 是管理员；否则是转出用户
    can_cancel = (
        current_user.role == "admin" or 
        request.created_by_id == current_user.id or 
        (not request.created_by_id and request.from_user_id == current_user.id)
    )
    if not can_cancel:
        raise HTTPException(status_code=403, detail="只有申请创建人可以撤回申请")
    
    asset = db.query(Asset).filter(Asset.id == request.asset_id).first()
    logger.info(f"用户 {current_user.ehr_number}({current_user.real_name}) 撤回资产交接申请: 资产ID {request.asset_id}({asset.asset_number if asset else 'N/A'}), 申请ID {request.id}")
    
    # 【B5】若存在联动下发的安检任务，先将其置为已取消，再删除交接单
    linked_task_id = getattr(request, "linked_safety_task_id", None)
    if linked_task_id:
        linked_task = db.query(SafetyCheckTask).filter(SafetyCheckTask.id == linked_task_id).first()
        if linked_task and linked_task.status in ("pending", "overdue"):
            linked_task.status = "cancelled"
            logger.info(f"撤回交接时同步取消联动安检任务: task_id={linked_task_id}")
    
    # 记录撤回历史
    try:
        create_history = get_create_history_record()
        create_history(
            db=db,
            asset_id=request.asset_id,
            action_type="transfer",
            action_description="撤回资产交接申请",
            operator_id=current_user.id,
            related_request_id=request.id,
            related_request_type="transfer"
        )
    except Exception as e:
        logger.error(f"记录撤回历史失败: {e}", exc_info=True)
    
    # 删除申请
    db.delete(request)
    db.commit()
    return {"message": "申请已撤回"}


@router.post("/{request_id}/confirm", response_model=TransferRequestResponse)
async def confirm_transfer_request(
    request_id: int,
    confirmation_data: TransferConfirmationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """转入人确认或拒绝交接申请"""
    request = db.query(TransferRequest).filter(TransferRequest.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="交接申请不存在")
    
    # 检查权限：只有转入人可以确认
    if request.to_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="只有转入人可以确认此申请")
    
    # 检查申请状态，只能确认待确认状态的申请
    if request.status != "waiting_confirmation":
        raise HTTPException(status_code=400, detail="只能确认待确认状态的申请")
    
    # 【干预点2：如果是确认接收（而不是拒绝接收），转入人确认前必须确保原所有人做完了安检】
    if confirmation_data.confirmed:
        check_unfinished_tasks_for_asset_user(db, request.asset_id, request.from_user_id)

    # 更新确认信息
    request.to_user_confirmed = 1 if confirmation_data.confirmed else 0
    request.to_user_confirm_comment = confirmation_data.comment
    request.to_user_confirmed_at = now_utc_naive()
    
    if confirmation_data.confirmed:
        # 转入人确认，状态改为待审批
        request.status = "pending"
        action_description = f"转入人确认资产交接申请"
        logger.info(f"用户 {current_user.ehr_number}({current_user.real_name}) 确认资产交接申请: 申请ID {request.id}")
    else:
        # 转入人拒绝，状态改为确认拒绝
        request.status = "confirmation_rejected"
        action_description = f"转入人拒绝资产交接申请"
        logger.info(f"用户 {current_user.ehr_number}({current_user.real_name}) 拒绝资产交接申请: 申请ID {request.id}")
    
    # 记录确认历史
    try:
        create_history = get_create_history_record()
        from_user = db.query(User).filter(User.id == request.from_user_id).first()
        to_user = db.query(User).filter(User.id == request.to_user_id).first()
        
        create_history(
            db=db,
            asset_id=request.asset_id,
            action_type="transfer",
            action_description=action_description,
            operator_id=current_user.id,
            old_value={"user_id": request.from_user_id, "user_name": from_user.real_name if from_user else ""},
            new_value={"user_id": request.to_user_id, "user_name": to_user.real_name if to_user else ""},
            related_request_id=request.id,
            related_request_type="transfer"
        )
    except Exception as e:
        logger.error(f"记录确认历史失败: {e}", exc_info=True)
    
    db.commit()
    db.refresh(request)
    return _build_transfer_response(db, request)
