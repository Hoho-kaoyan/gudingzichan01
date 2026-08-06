"""
审批管理路由
包括交接和退回申请的审批
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import TransferRequest, ReturnRequest, AssetEditRequest, Asset, User, TaskAsset
from schemas import ApprovalRequest
from auth import get_current_admin_user
from routers.transfers import check_unfinished_tasks_for_asset_user
from logger import logger
# 延迟导入避免循环依赖
def get_create_history_record():
    from routers import asset_history
    return asset_history.create_history_record
from utils_time import now_east8, now_utc_naive

router = APIRouter()


@router.post("/approve")
async def approve_request(
    approval_data: ApprovalRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """
    审批申请（仅管理员）
    request_type: "transfer"、"return" 或 "edit"
    """
    if approval_data.request_type == "transfer":
        # 审批交接申请
        request = db.query(TransferRequest).filter(
            TransferRequest.id == approval_data.request_id
        ).first()
        if not request:
            raise HTTPException(status_code=404, detail="交接申请不存在")
        
        # 检查申请状态，必须是待审批状态
        if request.status != "pending":
            raise HTTPException(status_code=400, detail="该申请已处理或尚未确认")
        
        # 检查转入人是否已确认
        if request.to_user_confirmed is None or request.to_user_confirmed != 1:
            raise HTTPException(status_code=400, detail="转入人尚未确认，无法审批")

        # 【干预点3：如果管理员点的是通过（approved），审批前必须确保原所有人做完了安检】
        if approval_data.approved:
            # 【Bug 1.1 修复 v5.1】审批前重校验：资产必须存在、未删除、状态为"在用"、持有人未变
            asset = db.query(Asset).filter(Asset.id == request.asset_id).first()
            if not asset or asset.deleted_at is not None:
                raise HTTPException(status_code=400, detail="资产已被删除,无法审批")
            if asset.status != "在用":
                raise HTTPException(
                    status_code=400,
                    detail=f"资产当前状态为「{asset.status}」,无法完成交接审批(应先处理其它进行中流程)"
                )
            if asset.user_id != request.from_user_id:
                raise HTTPException(status_code=400, detail="资产持有人已变更,请刷新后重试")

            check_unfinished_tasks_for_asset_user(db, request.asset_id, request.from_user_id)
        
        # 更新申请状态
        request.status = "approved" if approval_data.approved else "rejected"
        request.approver_id = current_user.id
        request.approval_comment = approval_data.comment
        request.approved_at = now_utc_naive()
        
        # 如果批准，更新资产信息
        if approval_data.approved:
            # 查询资产，包括已删除的（因为审批时资产可能已被删除，但仍需要处理审批）
            asset = db.query(Asset).filter(Asset.id == request.asset_id).first()
            if asset and asset.deleted_at is None:
                to_user = db.query(User).filter(User.id == request.to_user_id).first()
                if not to_user:
                    raise HTTPException(status_code=404, detail="转入用户不存在")
                # 需求1：允许管理员名下可有资产，交接可转给管理员，不再限制 to_user.role == "admin"
                old_user_id = asset.user_id
                old_user = db.query(User).filter(User.id == old_user_id).first() if old_user_id else None
                
                asset.user_id = request.to_user_id
                # 【Bug 1.1 修复 v5.1】同步写 status="在用"，避免被退回流程覆盖
                asset.status = "在用"
                # 更新使用人组别
                if to_user:
                    asset.user_group = to_user.group
                    # 同步更新执行人：默认与新使用人保持一致
                    asset.safety_check_executor_id = to_user.id
                    asset.safety_check_executor_name = to_user.real_name

                # 获取转出用户信息
                from_user = db.query(User).filter(User.id == request.from_user_id).first()

                # 【Bug 1.4 修复 v5.1】不切换 task_assets.assigned_user_id
                # 原逻辑会把 pending 任务的归属从 from_user 切到 to_user，
                # 导致转入人莫名其妙收到不属于他的安检任务。
                # v5.1 决策：交接流程的联动安检任务保持原使用人（转出人），
                # 后续年度/入库/调拨等任务按新使用人/安全检查执行人重新生成。
                logger.info(
                    f"资产交接：安检任务保持归属原使用人 "
                    f"from={request.from_user_id} to={request.to_user_id}, "
                    f"asset_id={asset.id}, 不切换 task_assets.assigned_user_id(按 v5.1 需求)"
                )

                logger.info(f"管理员 {current_user.ehr_number}({current_user.real_name}) 审批通过资产交接申请: 资产ID {asset.id}({asset.asset_number}), 从 {from_user.real_name if from_user else ''} 转给 {to_user.real_name if to_user else ''}, 申请ID {request.id}")
                
                # 记录审批通过历史
                # operator_id 应该是实际发起申请的用户，而不是转出用户
                # 如果管理员代为申请，应该显示管理员；否则显示转出用户
                operator_id = request.created_by_id if request.created_by_id else request.from_user_id
                
                try:
                    create_history = get_create_history_record()
                    create_history(
                        db=db,
                        asset_id=request.asset_id,
                        action_type="approve",
                        action_description=f"审批通过资产交接：从 {from_user.real_name if from_user else ''} 转给 {to_user.real_name if to_user else ''}",
                        operator_id=operator_id,
                        approver_id=current_user.id,
                        old_value={"user_id": old_user_id, "user_name": old_user.real_name if old_user else ""},
                        new_value={"user_id": request.to_user_id, "user_name": to_user.real_name if to_user else ""},
                        related_request_id=request.id,
                        related_request_type="transfer"
                    )
                except Exception as e:
                    logger.error(f"记录审批历史失败: {e}", exc_info=True)
        else:
            # 记录审批拒绝历史
            # operator_id 应该是实际发起申请的用户
            operator_id = request.created_by_id if request.created_by_id else request.from_user_id

            logger.info(f"管理员 {current_user.ehr_number}({current_user.real_name}) 拒绝资产交接申请: 资产ID {request.asset_id}, 申请ID {request.id}")

            # 【缺陷 4 修复 v5.1】审批拒绝时取消联动安检任务（避免幽灵任务）
            linked_task_id = getattr(request, "linked_safety_task_id", None)
            if linked_task_id:
                linked_task = db.query(SafetyCheckTask).filter(SafetyCheckTask.id == linked_task_id).first()
                if linked_task and linked_task.status in ("pending", "overdue"):
                    linked_task.status = "cancelled"
                    logger.info(f"审批拒绝交接：联动安检任务 #{linked_task_id} 已取消")

            try:
                create_history = get_create_history_record()
                create_history(
                    db=db,
                    asset_id=request.asset_id,
                    action_type="approve",
                    action_description="审批拒绝资产交接申请",
                    operator_id=operator_id,
                    approver_id=current_user.id,
                    related_request_id=request.id,
                    related_request_type="transfer"
                )
            except Exception as e:
                logger.error(f"记录审批历史失败: {e}", exc_info=True)
        
        db.commit()
        return {"message": "审批完成"}
    
    elif approval_data.request_type == "return":
        # 审批退回申请
        request = db.query(ReturnRequest).filter(
            ReturnRequest.id == approval_data.request_id
        ).first()
        if not request:
            raise HTTPException(status_code=404, detail="退回申请不存在")
        
        if request.status != "pending":
            raise HTTPException(status_code=400, detail="该申请已处理")
        
        # 更新申请状态
        request.status = "approved" if approval_data.approved else "rejected"
        request.approver_id = current_user.id
        request.approval_comment = approval_data.comment
        request.approved_at = now_utc_naive()
        
        # 如果批准，根据申请人修改的内容更新资产信息
        if approval_data.approved:
            # 查询资产，包括已删除的（因为审批时资产可能已被删除，但仍需要处理审批）
            asset = db.query(Asset).filter(Asset.id == request.asset_id).first()
            if asset and asset.deleted_at is None:
                # 记录旧值
                old_values = {
                    "user_id": asset.user_id,
                    "user_group": asset.user_group,
                    "status": asset.status,
                    "mac_address": asset.mac_address,
                    "ip_address": asset.ip_address,
                    "office_location": asset.office_location,
                    "floor": asset.floor,
                    "seat_number": asset.seat_number,
                    "remark": asset.remark
                }
                old_user = db.query(User).filter(User.id == asset.user_id).first() if asset.user_id else None
                
                # 审批通过后资产状态为"在库"，使用人置空（退回仓库）
                asset.user_id = None
                asset.user_group = None
                asset.safety_check_executor_id = None
                asset.safety_check_executor_name = None
                asset.status = "在库"
                asset.mac_address = request.mac_address
                asset.ip_address = request.ip_address
                asset.office_location = request.office_location
                asset.floor = request.floor
                asset.seat_number = request.seat_number
                asset.remark = request.remark
                
                # 将该资产未完成的安全检查任务标记为已退库
                pending_task_assets = db.query(TaskAsset).filter(
                    TaskAsset.asset_id == asset.id,
                    TaskAsset.status == "pending"
                ).all()
                
                for task_asset in pending_task_assets:
                    task_asset.status = "returned"  # 标记为已退库
                    logger.info(f"资产退回：安全检查任务资产关联ID {task_asset.id} 已标记为已退库")
                
                # 记录审批通过历史
                logger.info(f"管理员 {current_user.ehr_number}({current_user.real_name}) 审批通过资产退回申请: 资产ID {asset.id}({asset.asset_number}), 申请ID {request.id}")

                try:
                    create_history = get_create_history_record()
                    new_values = {
                        "user_id": None,
                        "user_name": "在库",
                        "user_group": None,
                        "status": asset.status,
                        "mac_address": asset.mac_address,
                        "ip_address": asset.ip_address,
                        "office_location": asset.office_location,
                        "floor": asset.floor,
                        "seat_number": asset.seat_number,
                        "remark": asset.remark
                    }

                    create_history(
                        db=db,
                        asset_id=request.asset_id,
                        action_type="approve",
                        action_description="审批通过资产退回：资产退回仓库，状态改为在库",
                        operator_id=request.user_id,
                        approver_id=current_user.id,
                        old_value=old_values,
                        new_value=new_values,
                        related_request_id=request.id,
                        related_request_type="return"
                    )
                except Exception as e:
                    logger.error(f"记录审批历史失败: {e}", exc_info=True)
        else:
            # 记录审批拒绝历史
            asset = db.query(Asset).filter(Asset.id == request.asset_id).first()
            logger.info(f"管理员 {current_user.ehr_number}({current_user.real_name}) 拒绝资产退回申请: 资产ID {request.asset_id}({asset.asset_number if asset else 'N/A'}), 申请ID {request.id}")
            
            try:
                create_history = get_create_history_record()
                create_history(
                    db=db,
                    asset_id=request.asset_id,
                    action_type="approve",
                    action_description="审批拒绝资产退回申请",
                    operator_id=request.user_id,
                    approver_id=current_user.id,
                    related_request_id=request.id,
                    related_request_type="return"
                )
            except Exception as e:
                logger.error(f"记录审批历史失败: {e}", exc_info=True)
        
        db.commit()
        return {"message": "审批完成"}
    
    elif approval_data.request_type == "edit":
        # 审批编辑申请
        request = db.query(AssetEditRequest).filter(
            AssetEditRequest.id == approval_data.request_id
        ).first()
        if not request:
            raise HTTPException(status_code=404, detail="编辑申请不存在")
        
        if request.status != "pending":
            raise HTTPException(status_code=400, detail="该申请已处理")
        
        # 更新申请状态
        request.status = "approved" if approval_data.approved else "rejected"
        request.approver_id = current_user.id
        request.approval_comment = approval_data.comment
        request.approved_at = now_utc_naive()
        
        # 如果批准，更新资产信息
        if approval_data.approved:
            # 查询资产，包括已删除的（因为审批时资产可能已被删除，但仍需要处理审批）
            asset = db.query(Asset).filter(Asset.id == request.asset_id).first()
            if asset and asset.deleted_at is None:
                # 解析编辑数据
                import json
                edit_data = json.loads(request.edit_data) if request.edit_data else {}
                # 使用人不能是管理员
                if edit_data.get("user_id") is not None:
                    edit_user = db.query(User).filter(User.id == edit_data["user_id"]).first()
                    if edit_user and edit_user.role == "admin":
                        raise HTTPException(status_code=400, detail="使用人不能是管理员")
                
                # 记录旧值
                old_values = {
                    "name": asset.name,
                    "specification": asset.specification,
                    "status": asset.status,
                    "mac_address": asset.mac_address,
                    "ip_address": asset.ip_address,
                    "office_location": asset.office_location,
                    "floor": asset.floor,
                    "seat_number": asset.seat_number,
                    "user_id": asset.user_id,
                    "user_group": asset.user_group,
                    "remark": asset.remark
                }
                
                # 更新字段
                changed_fields = []
                for field, value in edit_data.items():
                    old_val = getattr(asset, field, None)
                    if old_val != value:
                        setattr(asset, field, value)
                        changed_fields.append(field)
                
                # 如果更新了使用人，自动更新组别与执行人
                old_user_id = old_values.get("user_id")
                if "user_id" in edit_data and edit_data["user_id"] is not None:
                    user = db.query(User).filter(User.id == edit_data["user_id"]).first()
                    if user:
                        asset.user_group = user.group
                        # 同步更新执行人：默认与新使用人保持一致
                        asset.safety_check_executor_id = user.id
                        asset.safety_check_executor_name = user.real_name
                
                # 处理安全检查任务
                # 如果修改了使用人，更新未完成的安全检查任务到新接收人
                if "user_id" in changed_fields and edit_data.get("user_id") is not None and edit_data.get("user_id") != old_user_id:
                    pending_task_assets = db.query(TaskAsset).filter(
                        TaskAsset.asset_id == asset.id,
                        TaskAsset.status == "pending"
                    ).all()
                    
                    new_user = db.query(User).filter(User.id == edit_data["user_id"]).first()
                    for task_asset in pending_task_assets:
                        task_asset.assigned_user_id = edit_data["user_id"]
                        logger.info(f"资产编辑审批：安全检查任务资产关联ID {task_asset.id} 已更新到新接收人 {new_user.real_name if new_user else ''}")
                
                # 如果状态改为"在库"，将未完成的安全检查任务标记为已退库
                if "status" in changed_fields and asset.status == "在库":
                    pending_task_assets = db.query(TaskAsset).filter(
                        TaskAsset.asset_id == asset.id,
                        TaskAsset.status == "pending"
                    ).all()
                    
                    for task_asset in pending_task_assets:
                        task_asset.status = "returned"  # 标记为已退库
                        logger.info(f"资产编辑审批：安全检查任务资产关联ID {task_asset.id} 已标记为已退库")
                
                # 导入字段名映射函数
                from routers.asset_history import get_field_label
                field_labels = [get_field_label(field) for field in changed_fields] if changed_fields else []
                logger.info(f"管理员 {current_user.ehr_number}({current_user.real_name}) 审批通过资产编辑申请: 资产ID {asset.id}({asset.asset_number}), 修改字段: {', '.join(field_labels) if field_labels else '无'}, 申请ID {request.id}")
                
                # 记录审批通过历史
                try:
                    create_history = get_create_history_record()
                    new_values = {field: getattr(asset, field) for field in changed_fields}
                    create_history(
                        db=db,
                        asset_id=request.asset_id,
                        action_type="edit_approve",
                        action_description=f"审批通过资产编辑：修改了 {', '.join(field_labels) if field_labels else '无变化'}",
                        operator_id=request.user_id,
                        approver_id=current_user.id,
                        old_value={k: old_values.get(k) for k in changed_fields if k in old_values},
                        new_value=new_values,
                        related_request_id=request.id,
                        related_request_type="edit"
                    )
                except Exception as e:
                    logger.error(f"记录审批历史失败: {e}", exc_info=True)
        else:
            # 记录审批拒绝历史
            asset = db.query(Asset).filter(Asset.id == request.asset_id).first()
            logger.info(f"管理员 {current_user.ehr_number}({current_user.real_name}) 拒绝资产编辑申请: 资产ID {request.asset_id}({asset.asset_number if asset else 'N/A'}), 申请ID {request.id}")
            
            try:
                create_history = get_create_history_record()
                create_history(
                    db=db,
                    asset_id=request.asset_id,
                    action_type="edit_approve",
                    action_description="审批拒绝资产编辑申请",
                    operator_id=request.user_id,
                    approver_id=current_user.id,
                    related_request_id=request.id,
                    related_request_type="edit"
                )
            except Exception as e:
                logger.error(f"记录审批历史失败: {e}", exc_info=True)
        
        db.commit()
        return {"message": "审批完成"}
    
    else:
        raise HTTPException(status_code=400, detail="无效的申请类型")
