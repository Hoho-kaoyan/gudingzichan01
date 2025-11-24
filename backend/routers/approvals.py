"""
审批管理路由
包括交接和退回申请的审批
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import TransferRequest, ReturnRequest, AssetEditRequest, Asset, User
from schemas import ApprovalRequest
from auth import get_current_admin_user
# 延迟导入避免循环依赖
def get_create_history_record():
    from routers import asset_history
    return asset_history.create_history_record
from datetime import datetime

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
        
        if request.status != "pending":
            raise HTTPException(status_code=400, detail="该申请已处理")
        
        # 更新申请状态
        request.status = "approved" if approval_data.approved else "rejected"
        request.approver_id = current_user.id
        request.approval_comment = approval_data.comment
        request.approved_at = datetime.utcnow()
        
        # 如果批准，更新资产信息
        if approval_data.approved:
            # 查询资产，包括已删除的（因为审批时资产可能已被删除，但仍需要处理审批）
            asset = db.query(Asset).filter(Asset.id == request.asset_id).first()
            if asset and asset.deleted_at is None:
                old_user_id = asset.user_id
                old_user = db.query(User).filter(User.id == old_user_id).first() if old_user_id else None
                
                asset.user_id = request.to_user_id
                # 更新使用人组别
                to_user = db.query(User).filter(User.id == request.to_user_id).first()
                if to_user:
                    asset.user_group = to_user.group
                
                # 获取转出用户信息
                from_user = db.query(User).filter(User.id == request.from_user_id).first()
                
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
                    print(f"记录审批历史失败: {e}")
        else:
            # 记录审批拒绝历史
            # operator_id 应该是实际发起申请的用户
            operator_id = request.created_by_id if request.created_by_id else request.from_user_id
            
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
                print(f"记录审批历史失败: {e}")
        
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
        request.approved_at = datetime.utcnow()
        
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
                
                # 判断是否修改了保管人
                changed_user = request.new_user_id is not None
                
                # 判断申请人是否修改了其他字段（排除保管人）
                has_changes = any([
                    request.mac_address is not None,
                    request.ip_address is not None,
                    request.office_location is not None,
                    request.floor is not None,
                    request.seat_number is not None,
                    request.remark is not None
                ])
                
                # 获取"仓库"用户
                warehouse_user = db.query(User).filter(User.ehr_number == "1000000").first()
                if not warehouse_user:
                    raise HTTPException(status_code=500, detail="仓库用户不存在，请先初始化数据库")
                
                # 根据三种情况处理
                # 注意：无论哪种情况，审批通过后资产状态都变为"库存备用"
                if changed_user:
                    # 情况1：申请人修改了保管人
                    # 状态变为"库存备用"，其他字段按照申请人修改的内容修改
                    new_user = db.query(User).filter(User.id == request.new_user_id).first()
                    if new_user:
                        asset.user_id = request.new_user_id
                        asset.user_group = new_user.group
                    else:
                        raise HTTPException(status_code=404, detail="指定的保管人不存在")
                    
                    # 更新其他字段（如果申请人提供了，包括null值）
                    asset.mac_address = request.mac_address
                    asset.ip_address = request.ip_address
                    asset.office_location = request.office_location
                    asset.floor = request.floor
                    asset.seat_number = request.seat_number
                    asset.remark = request.remark
                    
                    # 状态变为"库存备用"
                    asset.status = "库存备用"
                    
                elif has_changes:
                    # 情况2：申请人未修改保管人但修改了其他信息
                    # 保管人改为"仓库"用户，其他内容按照申请人修改的内容修改
                    asset.user_id = warehouse_user.id
                    asset.user_group = warehouse_user.group
                    asset.status = "库存备用"
                    
                    # 更新申请人修改的字段（包括null值）
                    asset.mac_address = request.mac_address
                    asset.ip_address = request.ip_address
                    asset.office_location = request.office_location
                    asset.floor = request.floor
                    asset.seat_number = request.seat_number
                    asset.remark = request.remark
                    
                else:
                    # 情况3：申请人没有修改任何字段
                    # 保管人改为"仓库"用户，除状态外其他内容不变
                    asset.user_id = warehouse_user.id
                    asset.user_group = warehouse_user.group
                    asset.status = "库存备用"
                    # 其他字段保持不变
                
                # 记录审批通过历史
                try:
                    create_history = get_create_history_record()
                    new_user_obj = db.query(User).filter(User.id == asset.user_id).first() if asset.user_id else None
                    new_values = {
                        "user_id": asset.user_id,
                        "user_name": new_user_obj.real_name if new_user_obj else "仓库",
                        "user_group": asset.user_group,
                        "status": asset.status,
                        "mac_address": asset.mac_address,
                        "ip_address": asset.ip_address,
                        "office_location": asset.office_location,
                        "floor": asset.floor,
                        "seat_number": asset.seat_number,
                        "remark": asset.remark
                    }
                    
                    # 构建描述
                    if changed_user:
                        desc = f"审批通过资产退回：保管人改为 {new_user_obj.real_name if new_user_obj else ''}，状态改为库存备用，其他字段按申请人修改"
                    elif has_changes:
                        desc = f"审批通过资产退回：资产退回仓库（{warehouse_user.real_name}），状态改为库存备用，字段按申请人修改"
                    else:
                        desc = f"审批通过资产退回：资产退回仓库（{warehouse_user.real_name}），状态改为库存备用"
                    
                    create_history(
                        db=db,
                        asset_id=request.asset_id,
                        action_type="approve",
                        action_description=desc,
                        operator_id=request.user_id,
                        approver_id=current_user.id,
                        old_value=old_values,
                        new_value=new_values,
                        related_request_id=request.id,
                        related_request_type="return"
                    )
                except Exception as e:
                    print(f"记录审批历史失败: {e}")
        else:
            # 记录审批拒绝历史
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
                print(f"记录审批历史失败: {e}")
        
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
        request.approved_at = datetime.utcnow()
        
        # 如果批准，更新资产信息
        if approval_data.approved:
            # 查询资产，包括已删除的（因为审批时资产可能已被删除，但仍需要处理审批）
            asset = db.query(Asset).filter(Asset.id == request.asset_id).first()
            if asset and asset.deleted_at is None:
                # 解析编辑数据
                import json
                edit_data = json.loads(request.edit_data) if request.edit_data else {}
                
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
                
                # 如果更新了使用人，自动更新组别
                if "user_id" in edit_data and edit_data["user_id"] is not None:
                    user = db.query(User).filter(User.id == edit_data["user_id"]).first()
                    if user:
                        asset.user_group = user.group
                
                # 记录审批通过历史
                try:
                    create_history = get_create_history_record()
                    new_values = {field: getattr(asset, field) for field in changed_fields}
                    create_history(
                        db=db,
                        asset_id=request.asset_id,
                        action_type="edit_approve",
                        action_description=f"审批通过资产编辑：修改了 {', '.join(changed_fields) if changed_fields else '无变化'}",
                        operator_id=request.user_id,
                        approver_id=current_user.id,
                        old_value={k: old_values.get(k) for k in changed_fields if k in old_values},
                        new_value=new_values,
                        related_request_id=request.id,
                        related_request_type="edit"
                    )
                except Exception as e:
                    print(f"记录审批历史失败: {e}")
        else:
            # 记录审批拒绝历史
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
                print(f"记录审批历史失败: {e}")
        
        db.commit()
        return {"message": "审批完成"}
    
    else:
        raise HTTPException(status_code=400, detail="无效的申请类型")
