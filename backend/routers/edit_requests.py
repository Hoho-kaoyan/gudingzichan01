"""
资产编辑申请路由
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from typing import List, Optional
import json
from database import get_db
from models import AssetEditRequest, Asset, User
from schemas import AssetEditRequestCreate, AssetEditRequestResponse
from auth import get_current_user
from logger import logger
# 延迟导入避免循环依赖
def get_create_history_record():
    from routers import asset_history
    return asset_history.create_history_record

router = APIRouter()


@router.get("/", response_model=List[AssetEditRequestResponse])
async def get_edit_requests(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    search: Optional[str] = Query(None, description="搜索关键词,支持模糊搜索所有字段"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取编辑申请列表,支持搜索"""
    query = db.query(AssetEditRequest)
    
    # 普通用户只能看到自己的申请
    if current_user.role != "admin":
        query = query.filter(AssetEditRequest.user_id == current_user.id)
    
    if status:
        query = query.filter(AssetEditRequest.status == status)
    
    # 支持模糊搜索
    if search:
        # 先获取所有相关的资产ID
        asset_results = db.query(Asset.id).filter(
            or_(
                Asset.asset_number.contains(search),
                Asset.name.contains(search),
                Asset.specification.contains(search)
            )
        ).all()
        asset_ids = [row[0] for row in asset_results]
        
        # 获取匹配的用户ID
        user_results = db.query(User.id).filter(
            or_(
                User.real_name.contains(search),
                User.ehr_number.contains(search)
            )
        ).all()
        user_ids = [row[0] for row in user_results]
        
        # 构建搜索条件
        search_conditions = []
        
        if asset_ids:
            search_conditions.append(AssetEditRequest.asset_id.in_(asset_ids))
        if user_ids:
            search_conditions.append(AssetEditRequest.user_id.in_(user_ids))
        
        if search_conditions:
            query = query.filter(or_(*search_conditions))
    
    # 使用joinedload预加载关联数据
    requests = query.options(
        joinedload(AssetEditRequest.asset),
        joinedload(AssetEditRequest.user),
        joinedload(AssetEditRequest.approver)
    ).order_by(AssetEditRequest.created_at.desc()).offset(skip).limit(limit).all()
    
    # 手动构造响应，处理edit_data的JSON解析
    result = []
    for req in requests:
        req_dict = {
            "id": req.id,
            "asset_id": req.asset_id,
            "user_id": req.user_id,
            "status": req.status,
            "approver_id": req.approver_id,
            "approval_comment": req.approval_comment,
            "created_at": req.created_at,
            "updated_at": req.updated_at,
            "approved_at": req.approved_at,
            "edit_data": json.loads(req.edit_data) if req.edit_data else {},
            "asset": req.asset,
            "user": req.user,
            "approver": req.approver
        }
        result.append(AssetEditRequestResponse(**req_dict))
    
    return result


@router.delete("/{request_id}")
async def cancel_edit_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """撤回资产编辑申请（仅申请人可以撤回,且只能撤回待审批状态的申请）"""
    request = db.query(AssetEditRequest).filter(AssetEditRequest.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="编辑申请不存在")
    
    # 检查申请状态,只能撤回待审批的申请
    if request.status != "pending":
        raise HTTPException(status_code=400, detail="只能撤回待审批状态的申请")
    
    # 检查权限：只有申请人可以撤回（管理员也可以）
    if current_user.role != "admin" and request.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="只有申请人可以撤回申请")
    
    asset = db.query(Asset).filter(Asset.id == request.asset_id).first()
    logger.info(f"用户 {current_user.ehr_number}({current_user.real_name}) 撤回资产编辑申请: 资产ID {request.asset_id}({asset.asset_number if asset else 'N/A'}), 申请ID {request.id}")
    
    # 记录撤回历史
    try:
        create_history = get_create_history_record()
        create_history(
            db=db,
            asset_id=request.asset_id,
            action_type="edit",
            action_description="撤回资产编辑申请",
            operator_id=current_user.id,
            related_request_id=request.id,
            related_request_type="edit"
        )
    except Exception as e:
        logger.error(f"记录撤回历史失败: {e}", exc_info=True)
    
    # 删除申请
    db.delete(request)
    db.commit()
    return {"message": "申请已撤回"}


@router.get("/{request_id}", response_model=AssetEditRequestResponse)
async def get_edit_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取指定编辑申请"""
    request = db.query(AssetEditRequest).options(
        joinedload(AssetEditRequest.asset),
        joinedload(AssetEditRequest.user),
        joinedload(AssetEditRequest.approver)
    ).filter(AssetEditRequest.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="编辑申请不存在")
    
    # 权限检查
    if current_user.role != "admin" and request.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权查看此申请")
    
    req_dict = {
        "id": request.id,
        "asset_id": request.asset_id,
        "user_id": request.user_id,
        "status": request.status,
        "approver_id": request.approver_id,
        "approval_comment": request.approval_comment,
        "created_at": request.created_at,
        "updated_at": request.updated_at,
        "approved_at": request.approved_at,
        "edit_data": json.loads(request.edit_data) if request.edit_data else {},
        "asset": request.asset,
        "user": request.user,
        "approver": request.approver
    }
    return AssetEditRequestResponse(**req_dict)


@router.post("/", response_model=AssetEditRequestResponse)
async def create_edit_request(
    edit_data: AssetEditRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建资产编辑申请"""
    # 检查资产是否存在（只查询未删除的）
    asset = db.query(Asset).filter(
        Asset.id == edit_data.asset_id,
        Asset.deleted_at.is_(None)
    ).first()
    if not asset:
        raise HTTPException(status_code=404, detail="资产不存在")
    
    # 普通用户只能编辑自己名下的资产
    if current_user.role != "admin" and asset.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="只能编辑自己名下的资产")
    
    # 普通用户不能修改使用人
    if current_user.role != "admin" and edit_data.edit_data.get("user_id") is not None:
        if edit_data.edit_data.get("user_id") != asset.user_id:
            raise HTTPException(status_code=403, detail="普通用户不能修改资产使用人")
    
    # 普通用户不能修改状态
    if current_user.role != "admin" and edit_data.edit_data.get("status") is not None:
        raise HTTPException(status_code=403, detail="普通用户不能修改资产状态")
    
    # 检查是否已有待审批的编辑申请
    existing_request = db.query(AssetEditRequest).filter(
        AssetEditRequest.asset_id == edit_data.asset_id,
        AssetEditRequest.status == "pending"
    ).first()
    if existing_request:
        raise HTTPException(status_code=400, detail="该资产已有待审批的编辑申请，请等待审批完成或先撤回现有申请")
    
    # 记录旧值（包含所有可能修改的字段）
    old_values = {
        "category_id": asset.category_id,
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
    
    # 只保留真正有变化的字段
    changed_fields = {}
    for k, v in edit_data.edit_data.items():
        old_val = old_values.get(k)
        # 处理空值比较：None、空字符串、空值都视为相同
        old_val_normalized = old_val if old_val is not None and old_val != "" else None
        new_val_normalized = v if v is not None and v != "" else None
        if old_val_normalized != new_val_normalized:
            changed_fields[k] = v
    
    # 如果没有字段变化，不允许创建编辑申请
    if not changed_fields:
        raise HTTPException(status_code=400, detail="没有字段发生变化，无需提交编辑申请")
    
    # 创建编辑申请（只存储有变化的字段）
    db_request = AssetEditRequest(
        asset_id=edit_data.asset_id,
        user_id=current_user.id,
        edit_data=json.dumps(changed_fields, ensure_ascii=False),
        status="pending"
    )
    db.add(db_request)
    db.flush()  # 先flush获取ID
    
    # 记录编辑申请历史
    try:
        create_history = get_create_history_record()
        # 导入字段名映射函数
        from routers.asset_history import get_field_label
        field_labels = [get_field_label(field) for field in changed_fields.keys()]
        create_history(
            db=db,
            asset_id=edit_data.asset_id,
            action_type="edit",
            action_description=f"申请编辑资产:修改了 {', '.join(field_labels) if field_labels else '无变化'}",
            operator_id=current_user.id,
            old_value={k: old_values.get(k) for k in changed_fields.keys() if k in old_values},
            new_value=changed_fields,
            related_request_id=db_request.id,
            related_request_type="edit"
        )
    except Exception as e:
        logger.error(f"记录编辑申请历史失败: {e}", exc_info=True)
    
    db.commit()
    db.refresh(db_request)
    
    # 重新加载关联数据
    db_request = db.query(AssetEditRequest).options(
        joinedload(AssetEditRequest.asset),
        joinedload(AssetEditRequest.user),
        joinedload(AssetEditRequest.approver)
    ).filter(AssetEditRequest.id == db_request.id).first()
    
    req_dict = {
        "id": db_request.id,
        "asset_id": db_request.asset_id,
        "user_id": db_request.user_id,
        "status": db_request.status,
        "approver_id": db_request.approver_id,
        "approval_comment": db_request.approval_comment,
        "created_at": db_request.created_at,
        "updated_at": db_request.updated_at,
        "approved_at": db_request.approved_at,
        "edit_data": json.loads(db_request.edit_data) if db_request.edit_data else {},
        "asset": db_request.asset,
        "user": db_request.user,
        "approver": db_request.approver
    }
    return AssetEditRequestResponse(**req_dict)
