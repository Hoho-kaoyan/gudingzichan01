"""
资产退回仓库路由
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from typing import List, Optional
from database import get_db
from models import ReturnRequest, Asset, User
from schemas import ReturnRequestCreate, ReturnRequestResponse
from auth import get_current_user
# 延迟导入避免循环依赖
def get_create_history_record():
    from routers import asset_history
    return asset_history.create_history_record

router = APIRouter()


@router.get("/", response_model=List[ReturnRequestResponse])
async def get_return_requests(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    search: Optional[str] = Query(None, description="搜索关键词，支持模糊搜索所有字段"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取退回申请列表，支持搜索"""
    query = db.query(ReturnRequest)
    
    # 普通用户只能看到自己的申请
    if current_user.role != "admin":
        query = query.filter(ReturnRequest.user_id == current_user.id)
    
    if status:
        query = query.filter(ReturnRequest.status == status)
    
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
        
        # 获取匹配的用户ID
        user_results = db.query(User.id).filter(
            or_(
                User.real_name.contains(search),
                User.ehr_number.contains(search),
                User.group.contains(search)
            )
        ).all()
        user_ids = [row[0] for row in user_results]
        
        # 构建搜索条件
        search_conditions = [ReturnRequest.reason.contains(search)]
        
        if asset_ids:
            search_conditions.append(ReturnRequest.asset_id.in_(asset_ids))
        if user_ids:
            search_conditions.append(ReturnRequest.user_id.in_(user_ids))
        
        if search_conditions:
            query = query.filter(or_(*search_conditions))
    
    # 使用joinedload预加载关联数据
    requests = query.options(
        joinedload(ReturnRequest.asset),
        joinedload(ReturnRequest.user),
        joinedload(ReturnRequest.new_user),
        joinedload(ReturnRequest.approver)
    ).order_by(ReturnRequest.created_at.desc()).offset(skip).limit(limit).all()
    return [ReturnRequestResponse.model_validate(req) for req in requests]


@router.get("/{request_id}", response_model=ReturnRequestResponse)
async def get_return_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取指定退回申请"""
    request = db.query(ReturnRequest).options(
        joinedload(ReturnRequest.asset),
        joinedload(ReturnRequest.user),
        joinedload(ReturnRequest.new_user),
        joinedload(ReturnRequest.approver)
    ).filter(ReturnRequest.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="退回申请不存在")
    
    # 权限检查
    if current_user.role != "admin" and request.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权查看此申请")
    
    return ReturnRequestResponse.model_validate(request)


@router.post("/", response_model=ReturnRequestResponse)
async def create_return_request(
    return_data: ReturnRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建资产退回仓库申请"""
    # 检查资产是否存在（只查询未删除的）
    asset = db.query(Asset).filter(
        Asset.id == return_data.asset_id,
        Asset.deleted_at.is_(None)
    ).first()
    if not asset:
        raise HTTPException(status_code=404, detail="资产不存在")
    
    # 检查资产是否在使用中
    if asset.status != "在用":
        raise HTTPException(status_code=400, detail="只能退回在用状态的资产")
    
    # 检查资产是否属于当前用户（普通用户只能退回自己的资产）
    if current_user.role != "admin" and asset.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="只能退回自己名下的资产")
    
    # 如果指定了新的保管人，验证用户是否存在
    if return_data.new_user_id is not None:
        new_user = db.query(User).filter(User.id == return_data.new_user_id).first()
        if not new_user:
            raise HTTPException(status_code=404, detail="指定的保管人不存在")
    
    # 创建退回申请，保存申请人修改的字段
    user_id = asset.user_id or current_user.id
    db_request = ReturnRequest(
        asset_id=return_data.asset_id,
        user_id=user_id,
        reason=return_data.reason,
        status="pending",
        # 保存申请人修改的字段
        mac_address=return_data.mac_address,
        ip_address=return_data.ip_address,
        office_location=return_data.office_location,
        floor=return_data.floor,
        seat_number=return_data.seat_number,
        new_user_id=return_data.new_user_id,
        remark=return_data.remark
    )
    db.add(db_request)
    db.flush()  # 先flush获取ID
    
    # 获取退回用户信息
    return_user = db.query(User).filter(User.id == user_id).first()
    
    # 构建修改说明
    changes = []
    if return_data.mac_address is not None:
        changes.append(f"MAC地址: {asset.mac_address or ''} -> {return_data.mac_address}")
    if return_data.ip_address is not None:
        changes.append(f"IP地址: {asset.ip_address or ''} -> {return_data.ip_address}")
    if return_data.office_location is not None:
        changes.append(f"存放地点: {asset.office_location or ''} -> {return_data.office_location}")
    if return_data.floor is not None:
        changes.append(f"存放楼层: {asset.floor or ''} -> {return_data.floor}")
    if return_data.seat_number is not None:
        changes.append(f"座位号: {asset.seat_number or ''} -> {return_data.seat_number}")
    if return_data.new_user_id is not None:
        new_user = db.query(User).filter(User.id == return_data.new_user_id).first()
        changes.append(f"保管人: {return_user.real_name if return_user else ''} -> {new_user.real_name if new_user else ''}")
    if return_data.remark is not None:
        changes.append(f"备注: {asset.remark or ''} -> {return_data.remark}")
    
    change_desc = "；".join(changes) if changes else "无修改"
    
    # 记录退回申请历史
    try:
        create_history = get_create_history_record()
        old_value = {
            "user_id": user_id,
            "user_name": return_user.real_name if return_user else "",
            "status": asset.status,
            "mac_address": asset.mac_address,
            "ip_address": asset.ip_address,
            "office_location": asset.office_location,
            "floor": asset.floor,
            "seat_number": asset.seat_number,
            "remark": asset.remark
        }
        new_value = {
            "user_id": return_data.new_user_id if return_data.new_user_id else None,
            "status": "库存备用",
            "mac_address": return_data.mac_address,
            "ip_address": return_data.ip_address,
            "office_location": return_data.office_location,
            "floor": return_data.floor,
            "seat_number": return_data.seat_number,
            "remark": return_data.remark
        }
        create_history(
            db=db,
            asset_id=return_data.asset_id,
            action_type="return",
            action_description=f"申请资产退回仓库：退回人 {return_user.real_name if return_user else ''}，修改内容：{change_desc}",
            operator_id=current_user.id,
            old_value=old_value,
            new_value=new_value,
            related_request_id=db_request.id,
            related_request_type="return"
        )
    except Exception as e:
        print(f"记录退回历史失败: {e}")
    
    db.commit()
    db.refresh(db_request)
    # 重新加载关联数据
    db_request = db.query(ReturnRequest).options(
        joinedload(ReturnRequest.asset),
        joinedload(ReturnRequest.user),
        joinedload(ReturnRequest.new_user),
        joinedload(ReturnRequest.approver)
    ).filter(ReturnRequest.id == db_request.id).first()
    return ReturnRequestResponse.model_validate(db_request)


"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from typing import List, Optional
from database import get_db
from models import ReturnRequest, Asset, User
from schemas import ReturnRequestCreate, ReturnRequestResponse
from auth import get_current_user
# 延迟导入避免循环依赖
def get_create_history_record():
    from routers import asset_history
    return asset_history.create_history_record

router = APIRouter()


@router.get("/", response_model=List[ReturnRequestResponse])
async def get_return_requests(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    search: Optional[str] = Query(None, description="搜索关键词，支持模糊搜索所有字段"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取退回申请列表，支持搜索"""
    query = db.query(ReturnRequest)
    
    # 普通用户只能看到自己的申请
    if current_user.role != "admin":
        query = query.filter(ReturnRequest.user_id == current_user.id)
    
    if status:
        query = query.filter(ReturnRequest.status == status)
    
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
        
        # 获取匹配的用户ID
        user_results = db.query(User.id).filter(
            or_(
                User.real_name.contains(search),
                User.ehr_number.contains(search),
                User.group.contains(search)
            )
        ).all()
        user_ids = [row[0] for row in user_results]
        
        # 构建搜索条件
        search_conditions = [ReturnRequest.reason.contains(search)]
        
        if asset_ids:
            search_conditions.append(ReturnRequest.asset_id.in_(asset_ids))
        if user_ids:
            search_conditions.append(ReturnRequest.user_id.in_(user_ids))
        
        if search_conditions:
            query = query.filter(or_(*search_conditions))
    
    # 使用joinedload预加载关联数据
    requests = query.options(
        joinedload(ReturnRequest.asset),
        joinedload(ReturnRequest.user),
        joinedload(ReturnRequest.new_user),
        joinedload(ReturnRequest.approver)
    ).order_by(ReturnRequest.created_at.desc()).offset(skip).limit(limit).all()
    return [ReturnRequestResponse.model_validate(req) for req in requests]


@router.get("/{request_id}", response_model=ReturnRequestResponse)
async def get_return_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取指定退回申请"""
    request = db.query(ReturnRequest).options(
        joinedload(ReturnRequest.asset),
        joinedload(ReturnRequest.user),
        joinedload(ReturnRequest.new_user),
        joinedload(ReturnRequest.approver)
    ).filter(ReturnRequest.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="退回申请不存在")
    
    # 权限检查
    if current_user.role != "admin" and request.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权查看此申请")
    
    return ReturnRequestResponse.model_validate(request)


@router.post("/", response_model=ReturnRequestResponse)
async def create_return_request(
    return_data: ReturnRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建资产退回仓库申请"""
    # 检查资产是否存在（只查询未删除的）
    asset = db.query(Asset).filter(
        Asset.id == return_data.asset_id,
        Asset.deleted_at.is_(None)
    ).first()
    if not asset:
        raise HTTPException(status_code=404, detail="资产不存在")
    
    # 检查资产是否在使用中
    if asset.status != "在用":
        raise HTTPException(status_code=400, detail="只能退回在用状态的资产")
    
    # 检查资产是否属于当前用户（普通用户只能退回自己的资产）
    if current_user.role != "admin" and asset.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="只能退回自己名下的资产")
    
    # 如果指定了新的保管人，验证用户是否存在
    if return_data.new_user_id is not None:
        new_user = db.query(User).filter(User.id == return_data.new_user_id).first()
        if not new_user:
            raise HTTPException(status_code=404, detail="指定的保管人不存在")
    
    # 创建退回申请，保存申请人修改的字段
    user_id = asset.user_id or current_user.id
    db_request = ReturnRequest(
        asset_id=return_data.asset_id,
        user_id=user_id,
        reason=return_data.reason,
        status="pending",
        # 保存申请人修改的字段
        mac_address=return_data.mac_address,
        ip_address=return_data.ip_address,
        office_location=return_data.office_location,
        floor=return_data.floor,
        seat_number=return_data.seat_number,
        new_user_id=return_data.new_user_id,
        remark=return_data.remark
    )
    db.add(db_request)
    db.flush()  # 先flush获取ID
    
    # 获取退回用户信息
    return_user = db.query(User).filter(User.id == user_id).first()
    
    # 构建修改说明
    changes = []
    if return_data.mac_address is not None:
        changes.append(f"MAC地址: {asset.mac_address or ''} -> {return_data.mac_address}")
    if return_data.ip_address is not None:
        changes.append(f"IP地址: {asset.ip_address or ''} -> {return_data.ip_address}")
    if return_data.office_location is not None:
        changes.append(f"存放地点: {asset.office_location or ''} -> {return_data.office_location}")
    if return_data.floor is not None:
        changes.append(f"存放楼层: {asset.floor or ''} -> {return_data.floor}")
    if return_data.seat_number is not None:
        changes.append(f"座位号: {asset.seat_number or ''} -> {return_data.seat_number}")
    if return_data.new_user_id is not None:
        new_user = db.query(User).filter(User.id == return_data.new_user_id).first()
        changes.append(f"保管人: {return_user.real_name if return_user else ''} -> {new_user.real_name if new_user else ''}")
    if return_data.remark is not None:
        changes.append(f"备注: {asset.remark or ''} -> {return_data.remark}")
    
    change_desc = "；".join(changes) if changes else "无修改"
    
    # 记录退回申请历史
    try:
        create_history = get_create_history_record()
        old_value = {
            "user_id": user_id,
            "user_name": return_user.real_name if return_user else "",
            "status": asset.status,
            "mac_address": asset.mac_address,
            "ip_address": asset.ip_address,
            "office_location": asset.office_location,
            "floor": asset.floor,
            "seat_number": asset.seat_number,
            "remark": asset.remark
        }
        new_value = {
            "user_id": return_data.new_user_id if return_data.new_user_id else None,
            "status": "库存备用",
            "mac_address": return_data.mac_address,
            "ip_address": return_data.ip_address,
            "office_location": return_data.office_location,
            "floor": return_data.floor,
            "seat_number": return_data.seat_number,
            "remark": return_data.remark
        }
        create_history(
            db=db,
            asset_id=return_data.asset_id,
            action_type="return",
            action_description=f"申请资产退回仓库：退回人 {return_user.real_name if return_user else ''}，修改内容：{change_desc}",
            operator_id=current_user.id,
            old_value=old_value,
            new_value=new_value,
            related_request_id=db_request.id,
            related_request_type="return"
        )
    except Exception as e:
        print(f"记录退回历史失败: {e}")
    
    db.commit()
    db.refresh(db_request)
    # 重新加载关联数据
    db_request = db.query(ReturnRequest).options(
        joinedload(ReturnRequest.asset),
        joinedload(ReturnRequest.user),
        joinedload(ReturnRequest.new_user),
        joinedload(ReturnRequest.approver)
    ).filter(ReturnRequest.id == db_request.id).first()
    return ReturnRequestResponse.model_validate(db_request)

