"""
资产退回仓库路由
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from typing import List, Optional
from database import get_db
from models import ReturnRequest, Asset, User, UserRole, TransferRequest
from schemas import ReturnRequestCreate, ReturnRequestResponse
from auth import get_current_user
from logger import logger
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
    search: Optional[str] = Query(None, description="搜索关键词,支持模糊搜索所有字段"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取退回申请列表,支持搜索"""
    query = db.query(ReturnRequest)
    
    # 普通用户/组长权限过滤
    if current_user.role == "leader":
        # 组长可以看到涉及其组员的所有单据
        user_ids_in_group = [u[0] for u in db.query(User.id).filter(User.group == current_user.group).all()]
        query = query.filter(ReturnRequest.user_id.in_(user_ids_in_group))
    elif current_user.role == "user":
        # 普通用户只能看到自己的申请
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


@router.post("/", response_model=List[ReturnRequestResponse])
async def create_return_request(
    return_data: ReturnRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """批量创建资产退回仓库申请（v5.1 改造）

    - 一次提交 N 个资产，统一创建 N 条 ReturnRequest
    - 整批共用一组可修改字段（mac_address / ip_address / ...）
    - 任一资产不满足条件则整批拒绝
    """
    asset_ids = return_data.asset_ids
    if not asset_ids:
        raise HTTPException(status_code=400, detail="至少选择一件资产")

    # 1) 校验所有资产存在、未删除、状态在用
    assets = db.query(Asset).filter(
        Asset.id.in_(asset_ids),
        Asset.deleted_at.is_(None)
    ).all()
    if len(assets) != len(set(asset_ids)):
        raise HTTPException(status_code=400, detail="部分资产不存在或已删除")
    asset_map = {a.id: a for a in assets}

    # 2) 逐资产校验：状态 / 互斥 / 权限 / 安检拦截
    from routers.transfers import check_unfinished_tasks_for_asset_user
    for aid in asset_ids:
        asset = asset_map[aid]
        if asset.status != "在用":
            raise HTTPException(
                status_code=400,
                detail=f"资产 {asset.asset_number} 状态为「{asset.status}」,无法退回"
            )

        # 互斥检查
        pending_transfer = db.query(TransferRequest).filter(
            TransferRequest.asset_id == aid,
            TransferRequest.status.in_(["waiting_confirmation", "pending"])
        ).first()
        if pending_transfer:
            raise HTTPException(
                status_code=400,
                detail=f"资产 {asset.asset_number} 已有待处理的交接申请,请先处理"
            )
        pending_return = db.query(ReturnRequest).filter(
            ReturnRequest.asset_id == aid,
            ReturnRequest.status == "pending"
        ).first()
        if pending_return:
            raise HTTPException(
                status_code=400,
                detail=f"资产 {asset.asset_number} 已有待处理的退回申请,请先处理"
            )

        # 权限校验
        if current_user.role == "admin":
            pass
        elif current_user.role == "leader":
            if asset.user_group != current_user.group:
                raise HTTPException(
                    status_code=403,
                    detail=f"资产 {asset.asset_number} 不在本组,组长无法代退"
                )
        else:
            if asset.user_id != current_user.id:
                raise HTTPException(
                    status_code=403,
                    detail=f"资产 {asset.asset_number} 不在您名下,无法退回"
                )

        # 安检拦截
        check_unfinished_tasks_for_asset_user(db, aid, asset.user_id or current_user.id)

    # 3) 整批共用字段快照（用于变更说明 & 历史记录）
    common_mac = return_data.mac_address
    common_ip = return_data.ip_address
    common_office = return_data.office_location
    common_floor = return_data.floor
    common_seat = return_data.seat_number
    common_remark = return_data.remark

    changes = []
    if common_mac is not None: changes.append(f"MAC地址:{common_mac}")
    if common_ip is not None: changes.append(f"IP地址:{common_ip}")
    if common_office is not None: changes.append(f"存放地点:{common_office}")
    if common_floor is not None: changes.append(f"存放楼层:{common_floor}")
    if common_seat is not None: changes.append(f"座位号:{common_seat}")
    if common_remark is not None: changes.append(f"备注:{common_remark}")
    change_desc = ";".join(changes) if changes else "无修改"

    # 4) 创建 N 条 ReturnRequest
    created = []
    for aid in asset_ids:
        asset = asset_map[aid]
        user_id = asset.user_id or current_user.id
        rr = ReturnRequest(
            asset_id=aid,
            user_id=user_id,
            reason=return_data.reason,
            status="pending",
            mac_address=common_mac,
            ip_address=common_ip,
            office_location=common_office,
            floor=common_floor,
            seat_number=common_seat,
            new_user_id=None,
            remark=common_remark,
        )
        db.add(rr)
        db.flush()

        return_user = db.query(User).filter(User.id == user_id).first()
        # 写历史
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
                "remark": asset.remark,
            }
            new_value = {
                "user_id": None,
                "status": "在库",
                "mac_address": common_mac,
                "ip_address": common_ip,
                "office_location": common_office,
                "floor": common_floor,
                "seat_number": common_seat,
                "remark": common_remark,
            }
            create_history(
                db=db,
                asset_id=aid,
                action_type="return",
                action_description=f"申请资产退回仓库(批量):退回人 {return_user.real_name if return_user else ''},修改内容:{change_desc}",
                operator_id=current_user.id,
                old_value=old_value,
                new_value=new_value,
                related_request_id=rr.id,
                related_request_type="return",
            )
        except Exception as e:
            logger.error(f"记录退回历史失败: {e}", exc_info=True)

        created.append(rr)

    db.commit()

    # 重新加载关联数据
    ids = [r.id for r in created]
    loaded = db.query(ReturnRequest).options(
        joinedload(ReturnRequest.asset),
        joinedload(ReturnRequest.user),
        joinedload(ReturnRequest.new_user),
        joinedload(ReturnRequest.approver)
    ).filter(ReturnRequest.id.in_(ids)).all()
    return [ReturnRequestResponse.model_validate(x) for x in loaded]


@router.delete("/{request_id}")
async def cancel_return_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """撤回退回申请（仅申请人或管理员可撤回；修复 v5.1 Bug 1.5）

    仅 pending 状态的申请可撤回；已审批的不可撤回。
    """
    request = db.query(ReturnRequest).filter(ReturnRequest.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="退回申请不存在")

    if request.status != "pending":
        raise HTTPException(status_code=400, detail="只能撤回待审批的退回申请")

    can_cancel = (
        current_user.role == UserRole.ADMIN.value
        or request.user_id == current_user.id
    )
    if not can_cancel:
        raise HTTPException(status_code=403, detail="只有申请人或管理员可以撤回")

    asset = db.query(Asset).filter(Asset.id == request.asset_id).first()
    logger.info(
        f"用户 {current_user.ehr_number}({current_user.real_name}) 撤回资产退回申请: "
        f"资产ID {request.asset_id}({asset.asset_number if asset else 'N/A'}), 申请ID {request.id}"
    )

    request.status = "cancelled"

    # 记录撤回历史
    try:
        create_history = get_create_history_record()
        create_history(
            db=db,
            asset_id=request.asset_id,
            action_type="return",
            action_description="撤回资产退回申请",
            operator_id=current_user.id,
            related_request_id=request.id,
            related_request_type="return"
        )
    except Exception as e:
        logger.error(f"记录退回撤回历史失败: {e}", exc_info=True)

    db.commit()
    return {"message": "退回申请已撤回"}
