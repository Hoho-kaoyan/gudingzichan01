"""
资产管理路由
包括资产的增删改查、批量导入等
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional
from database import get_db
from models import Asset, AssetCategory, User, TaskAsset
from schemas import (
    AssetCreate, AssetUpdate, AssetResponse, AssetUpdateResponse, ImportResponse,
    ImportConflictDetail, ImportConflictDiff, ImportResolveRequest,
)
from auth import get_current_user, get_current_admin_user
import pandas as pd
import io
from fastapi.responses import StreamingResponse
from excel_io import cell_to_str, row_cell_str, str_to_int, str_to_date, cell_to_date, row_to_error_dict
from logger import logger
# 延迟导入避免循环依赖
def get_create_history_record():
    from routers import asset_history
    return asset_history.create_history_record
from datetime import datetime, date
from utils_time import now_east8
from safety_check_linkage import create_system_allocated_task

router = APIRouter()

# 导入冲突比对：资产字段名 -> 中文标签（用于展示差异）
ASSET_FIELD_LABELS = {
    "category_id": "所属大类",
    "name": "实物名称",
    "specification": "规格型号",
    "status": "状态",
    "available_status": "可用状态",
    "mac_address": "MAC地址",
    "ip_address": "IP地址",
    "office_location": "存放办公地点",
    "floor": "存放楼层",
    "seat_number": "座位号",
    "user_id": "使用人",
    "user_group": "使用人组别",
    "remark": "备注说明",
    "quantity": "件数",
    "team": "所在团队",
    "purchase_date": "购置日期",
    "card_number": "卡片编号",
    "safety_check_executor_id": "检查执行人",
    "safety_check_executor_name": "检查执行人姓名",
    "computer_type": "电脑类型",
    "computer_usage": "电脑应用",
    "computer_name": "计算机名",
    "monitor1_model": "连接显示器1型号",
    "monitor1_asset_number": "连接显示器1资产编号",
    "monitor1_serial": "显示器1序列号",
    "monitor2_model": "连接显示器2型号",
    "monitor2_asset_number": "连接显示器2资产编号",
    "monitor2_serial": "显示器2序列号",
    "asset_contact": "资产管理联系人",
    "reserve_1": "预留1", "reserve_2": "预留2", "reserve_3": "预留3",
    "reserve_4": "预留4", "reserve_5": "预留5", "reserve_6": "预留6",
}


def _format_asset_value_for_diff(val, field: str, db: Session) -> str:
    """将资产字段值格式化为可展示的字符串，用于冲突对比"""
    if val is None:
        return ""
    if field == "category_id" and db is not None:
        cat = db.query(AssetCategory).filter(AssetCategory.id == val).first()
        return cat.name if cat else str(val)
    if field == "user_id" and db is not None:
        u = db.query(User).filter(User.id == val).first()
        if u:
            return f"{u.real_name}({u.ehr_number})"
        return str(val)
    if field == "safety_check_executor_id" and db is not None:
        u = db.query(User).filter(User.id == val).first()
        return u.real_name if u else str(val)
    if hasattr(val, "isoformat"):  # date/datetime
        return val.isoformat()[:10] if val else ""
    return str(val).strip()


def _build_import_conflict_diffs(existing_asset, parsed: dict, db: Session) -> List[ImportConflictDiff]:
    """比较数据库中资产与解析后的导入数据，返回有差异的字段列表（用于展示）"""
    diffs = []
    for field, label in ASSET_FIELD_LABELS.items():
        if field not in parsed:
            continue
        db_val = getattr(existing_asset, field, None)
        imp_val = parsed[field]
        # 统一比较：None 与 "" 视为同义，数字与字符串数字视为同义
        def _norm(v):
            if v is None:
                return ""
            if hasattr(v, "isoformat"):
                return v.isoformat()[:10] if v else ""
            s = str(v).strip()
            return s if s else ""

        db_str = _format_asset_value_for_diff(db_val, field, db)
        imp_str = _format_asset_value_for_diff(imp_val, field, db) if imp_val is not None else ""
        if _norm(db_val) != _norm(imp_val) or db_str != imp_str:
            # 展示用：数据库值、导入值
            d_str = db_str if db_str else "(空)"
            i_str = imp_str if imp_str else "(空)"
            if d_str != i_str:
                diffs.append(ImportConflictDiff(field_label=label, db_value=d_str, import_value=i_str))
    return diffs


def _get_rd(row_data: dict, *keys: str) -> str:
    """从 row_data（中文列名）取第一个存在的键的值，strip 后返回"""
    for k in keys:
        v = row_data.get(k)
        if v is not None:
            s = (str(v).strip() if not hasattr(v, "strip") else v.strip()) if v else ""
            if s and str(s).lower() != "nan":
                return s
    return ""


def _parse_row_data_for_resolve(row_data: dict, db: Session):
    """
    将冲突详情中的 row_data（中文列名、字符串值）解析为与导入逻辑一致的字段字典，
    用于「覆盖」时更新资产。返回 (parsed_dict, category)；
    若大类或必填为空则抛出 ValueError。
    """
    category_name = _get_rd(row_data, "所属大类")
    name = _get_rd(row_data, "实物名称")
    if not category_name or not name:
        raise ValueError("所属大类、实物名称为必填")
    category = db.query(AssetCategory).filter(AssetCategory.name == category_name).first()
    if not category:
        category = AssetCategory(name=category_name)
        db.add(category)
        db.flush()
    specification = _get_rd(row_data, "规格型号") or None
    status = _get_rd(row_data, "实物状态", "状态") or "在用"
    if status == "库存备用":
        status = "在库"
    available_status = _get_rd(row_data, "可用状态") or "可用"
    if available_status not in ("可用", "维修中", "已报废"):
        available_status = "可用"
    mac_address = _get_rd(row_data, "终端mac地址", "MAC地址") or None
    ip_address = _get_rd(row_data, "终端IP号", "IP地址") or None
    office_location = _get_rd(row_data, "存放办公地点") or None
    floor = _get_rd(row_data, "具体存放楼层", "存放楼层") or None
    seat_number = _get_rd(row_data, "座位号") or None
    user_group = _get_rd(row_data, "使用人组别", "组別", "组别") or None
    remark = _get_rd(row_data, "备注说明") or None
    quantity = str_to_int(_get_rd(row_data, "件数"), default=1)
    if quantity is None or quantity < 1:
        quantity = 1
    team = _get_rd(row_data, "所在团队") or None
    purchase_date = str_to_date(_get_rd(row_data, "购置日期")) if _get_rd(row_data, "购置日期") else None
    card_number = _get_rd(row_data, "卡片编号") or None
    computer_type = _get_rd(row_data, "电脑类型") or None
    computer_usage = _get_rd(row_data, "电脑应用") or None
    computer_name = _get_rd(row_data, "计算机名") or None
    monitor1_model = _get_rd(row_data, "连接显示器1型号") or None
    monitor1_asset_number = _get_rd(row_data, "连接显示器1资产编号") or None
    monitor1_serial = _get_rd(row_data, "显示器1 序列号", "显示器1序列号") or None
    monitor2_model = _get_rd(row_data, "连接显示器2", "连接显示器2型号") or None
    monitor2_asset_number = _get_rd(row_data, "连接显示器2资产编号") or None
    monitor2_serial = _get_rd(row_data, "显示器2序列号") or None
    asset_contact = _get_rd(row_data, "资产管理联系人") or None
    reserve_1 = _get_rd(row_data, "预留1") or None
    reserve_2 = _get_rd(row_data, "预留2") or None
    reserve_3 = _get_rd(row_data, "预留3") or None
    reserve_4 = _get_rd(row_data, "预留4") or None
    reserve_5 = _get_rd(row_data, "预留5") or None
    reserve_6 = _get_rd(row_data, "预留6") or None
    safety_check_executor_id = str_to_int(_get_rd(row_data, "检查执行人ID"), default=None)
    safety_check_executor_name = _get_rd(row_data, "检查执行人") or None
    if safety_check_executor_id is None and safety_check_executor_name:
        u = db.query(User).filter(
            User.real_name == safety_check_executor_name.strip(),
            User.deleted_at.is_(None)
        ).first()
        if u:
            safety_check_executor_id = u.id
    user_id = str_to_int(_get_rd(row_data, "所有人ID"), default=None)
    if user_id is not None:
        u = db.query(User).filter(User.id == user_id, User.deleted_at.is_(None)).first()
        if not u:
            user_id = None
        elif not user_group:
            user_group = u.group
    if user_id is None:
        owner_name = _get_rd(row_data, "所有人")
        if owner_name:
            u = db.query(User).filter(
                User.real_name == owner_name.strip(),
                User.deleted_at.is_(None)
            ).first()
            if u:
                user_id = u.id
                if not user_group:
                    user_group = u.group
    if user_id is None:
        user_ehr = _get_rd(row_data, "使用人EHR号")
        if user_ehr:
            user = db.query(User).filter(User.ehr_number == user_ehr, User.deleted_at.is_(None)).first()
            if user:
                user_id = user.id
                if not user_group:
                    user_group = user.group
    # 若仅修改了使用人而未显式指定执行人，则将执行人重置为新使用人
    if user_id is not None and safety_check_executor_id is None and not safety_check_executor_name:
        u = db.query(User).filter(User.id == user_id, User.deleted_at.is_(None)).first()
        if u:
            safety_check_executor_id = u.id
            safety_check_executor_name = u.real_name
    parsed = {
        "category_id": category.id, "name": name, "specification": specification,
        "status": status, "available_status": available_status, "mac_address": mac_address, "ip_address": ip_address,
        "office_location": office_location, "floor": floor, "seat_number": seat_number,
        "user_id": user_id, "user_group": user_group, "remark": remark,
        "quantity": quantity, "team": team, "purchase_date": purchase_date,
        "card_number": card_number, "safety_check_executor_id": safety_check_executor_id,
        "safety_check_executor_name": safety_check_executor_name,
        "computer_type": computer_type, "computer_usage": computer_usage, "computer_name": computer_name,
        "monitor1_model": monitor1_model, "monitor1_asset_number": monitor1_asset_number, "monitor1_serial": monitor1_serial,
        "monitor2_model": monitor2_model, "monitor2_asset_number": monitor2_asset_number, "monitor2_serial": monitor2_serial,
        "asset_contact": asset_contact,
        "reserve_1": reserve_1, "reserve_2": reserve_2, "reserve_3": reserve_3,
        "reserve_4": reserve_4, "reserve_5": reserve_5, "reserve_6": reserve_6,
    }
    return parsed, category


@router.get("/", response_model=List[AssetResponse])
async def get_assets(
    skip: int = 0,
    limit: int = 100,
    asset_number: Optional[str] = None,
    category_id: Optional[int] = None,
    status: Optional[str] = None,
    user_id: Optional[int] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取资产列表，支持筛选"""
    # 只查询未删除的资产
    query = db.query(Asset).filter(Asset.deleted_at.is_(None))
    
    # 管理员可以筛选指定用户的资产
    if user_id is not None:
        if current_user.role != "admin":
            raise HTTPException(status_code=403, detail="仅管理员可按使用人筛选资产")
        query = query.filter(Asset.user_id == user_id)
    
    if asset_number:
        query = query.filter(Asset.asset_number.contains(asset_number))
    if category_id:
        query = query.filter(Asset.category_id == category_id)
    if status:
        query = query.filter(Asset.status == status)
    if search:
        query = query.outerjoin(AssetCategory, Asset.category).outerjoin(User, Asset.user)
        like_value = f"%{search}%"
        query = query.filter(
            or_(
                Asset.asset_number.ilike(like_value),
                Asset.name.ilike(like_value),
                Asset.specification.ilike(like_value),
                Asset.mac_address.ilike(like_value),
                Asset.ip_address.ilike(like_value),
                Asset.office_location.ilike(like_value),
                Asset.floor.ilike(like_value),
                Asset.seat_number.ilike(like_value),
                Asset.remark.ilike(like_value),
                Asset.user_group.ilike(like_value),
                Asset.status.ilike(like_value),
                AssetCategory.name.ilike(like_value),
                User.real_name.ilike(like_value),
                User.ehr_number.ilike(like_value)
            )
        )
    
    # 组长只能看到本组资产
    if current_user.role == "leader":
        query = query.filter(Asset.user_group == current_user.group)
    
    assets = query.offset(skip).limit(limit).all()
    return [AssetResponse.model_validate(asset) for asset in assets]


@router.get("/export")
async def export_assets(
    asset_ids: Optional[str] = Query(
        default=None,
        description="要导出的资产ID，多个以逗号分隔；为空则导出全部"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """导出资产列表（仅管理员）"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="只有管理员可以导出资产")

    # 只查询未删除的资产
    query = db.query(Asset).filter(Asset.deleted_at.is_(None))
    ids: List[int] = []
    if asset_ids:
        try:
            ids = [int(i.strip()) for i in asset_ids.split(",") if i.strip()]
        except ValueError:
            raise HTTPException(status_code=400, detail="资产ID格式不正确")
        if ids:
            query = query.filter(Asset.id.in_(ids))

    assets = query.all()
    if not assets:
        raise HTTPException(status_code=404, detail="没有可导出的资产")

    data = []
    for asset in assets:
        data.append({
            "资产编号": asset.asset_number,
            "所属大类": asset.category.name if asset.category else "",
            "实物名称": asset.name,
            "规格型号": asset.specification or "",
            "状态": asset.status,
            "MAC地址": asset.mac_address or "",
            "IP地址": asset.ip_address or "",
            "存放办公地点": asset.office_location or "",
            "存放楼层": asset.floor or "",
            "座位号": asset.seat_number or "",
            "使用人": asset.user.real_name if asset.user else "",
            "使用人EHR号": asset.user.ehr_number if asset.user else "",
            "组别": asset.user_group or "",
            "备注说明": asset.remark or "",
            "创建时间": asset.created_at.strftime("%Y-%m-%d %H:%M:%S") if asset.created_at else "",
            "更新时间": asset.updated_at.strftime("%Y-%m-%d %H:%M:%S") if asset.updated_at else ""
        })

    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="资产列表")
    output.seek(0)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": 'attachment; filename="assets_export.xlsx"'
        }
    )


@router.get("/{asset_id}", response_model=AssetResponse)
async def get_asset(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取指定资产信息"""
    # 只查询未删除的资产
    asset = db.query(Asset).filter(Asset.id == asset_id, Asset.deleted_at.is_(None)).first()
    if not asset:
        raise HTTPException(status_code=404, detail="资产不存在")
    
    # 普通用户只能查看自己名下的资产；组长可查看本组资产
    if current_user.role == "user" and asset.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权查看此资产")
    if current_user.role == "leader" and asset.user_group != current_user.group:
        raise HTTPException(status_code=403, detail="无权查看此资产")
    
    return AssetResponse.model_validate(asset)


@router.post("/", response_model=AssetResponse)
async def create_asset(
    asset_data: AssetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """创建新资产（仅管理员）"""
    # 检查资产编号是否已存在（包括已删除的资产，因为资产编号应该唯一）
    existing = db.query(Asset).filter(
        Asset.asset_number == asset_data.asset_number,
        Asset.deleted_at.is_(None)  # 只检查未删除的资产编号
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="资产编号已存在")
    
    # 检查大类是否存在
    category = db.query(AssetCategory).filter(AssetCategory.id == asset_data.category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="资产大类不存在")
    
    asset_dict = asset_data.dict()

    # 如果是普通用户或组长，强制将资产归属到自己的组
    if current_user.role != "admin":
        # 组长可以选择使用人，但默认组别必须是自己的组
        if current_user.role == "leader":
            user_id = asset_dict.get("user_id")
            if user_id:
                user = db.query(User).filter(User.id == user_id).first()
                if not user or user.group != current_user.group:
                    raise HTTPException(status_code=403, detail="组长只能将资产分配给本组人员")
                asset_dict["user_group"] = current_user.group
            else:
                asset_dict["user_group"] = current_user.group
        else:
            # 普通用户强制归属自己
            asset_dict["user_id"] = current_user.id
            asset_dict["user_group"] = current_user.group

        # 普通用户不能设置状态，默认设置为"在用"
        if current_user.role == "user":
            if "status" in asset_dict:
                del asset_dict["status"]
            asset_dict["status"] = "在用"
    else:
        # 管理员创建时，可指定使用人（含管理员本人，以便管理员名下可有资产并对自己资产做检查）
        user_id = asset_dict.get("user_id")
        if user_id:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise HTTPException(status_code=404, detail="使用人不存在")
            if not asset_dict.get("user_group"):
                asset_dict["user_group"] = user.group

    db_asset = Asset(**asset_dict)
    db.add(db_asset)
    db.flush()  # 先flush获取ID
    
    logger.info(f"用户 {current_user.ehr_number}({current_user.real_name}) 创建资产: {db_asset.asset_number} - {db_asset.name}")
    
    # 记录创建历史
    try:
        create_history = get_create_history_record()
        create_history(
            db=db,
            asset_id=db_asset.id,
            action_type="create",
            action_description=f"创建资产：{db_asset.asset_number} - {db_asset.name}",
            operator_id=current_user.id,
            new_value={
                "asset_number": db_asset.asset_number,
                "name": db_asset.name,
                "category": category.name,
                "status": db_asset.status,
                "user_id": db_asset.user_id
            }
        )
    except Exception as e:
        logger.error(f"记录创建历史失败: {e}", exc_info=True)
    
    db.commit()
    db.refresh(db_asset)
    
    # 【新增逻辑】：如果资产落库后有使用人或检查执行人，下发安检联动任务（优先使用检查执行人ID）
    assigned_id = getattr(db_asset, "safety_check_executor_id", None) or db_asset.user_id
    if assigned_id:
        try:
            create_system_allocated_task(
                db=db,
                asset_id=db_asset.id,
                assigned_user_id=assigned_id,
                source="inbound"
            )
        except Exception as e:
            logger.error(f"创建资产时触发系统安检任务下发失败: {e}", exc_info=True)

    return AssetResponse.model_validate(db_asset)


@router.put("/{asset_id}", response_model=AssetUpdateResponse)
async def update_asset(
    asset_id: int,
    asset_data: AssetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新资产信息
    管理员：直接更新资产
    普通用户：提交编辑申请，需要管理员审批
    """
    # 只查询未删除的资产
    asset = db.query(Asset).filter(Asset.id == asset_id, Asset.deleted_at.is_(None)).first()
    if not asset:
        raise HTTPException(status_code=404, detail="资产不存在")
    
    # 普通用户只能编辑自己名下的资产
    if current_user.role == "user" and asset.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="只能编辑自己名下的资产")
        
    # 组长只能编辑本组所在的资产
    if current_user.role == "leader" and asset.user_group != current_user.group:
        raise HTTPException(status_code=403, detail="组长只能编辑本组关联的资产")
    
    # 普通用户不能修改使用人
    if current_user.role == "user" and asset_data.user_id is not None:
        if asset_data.user_id != asset.user_id:
            raise HTTPException(status_code=403, detail="普通用户不能修改资产使用人")
            
    # 组长如果修改使用人，新使用人必须与组长同组
    if current_user.role == "leader" and asset_data.user_id is not None and asset_data.user_id != asset.user_id:
        new_usr = db.query(User).filter(User.id == asset_data.user_id).first()
        if not new_usr or new_usr.group != current_user.group:
            raise HTTPException(status_code=403, detail="组长只能将资产分配给本组人员")
    
    # 如果是普通用户，提交编辑申请而不是直接更新
    if current_user.role == "user":
        import json
        from models import AssetEditRequest
        
        # 检查是否已有待审批的编辑申请
        existing_request = db.query(AssetEditRequest).filter(
            AssetEditRequest.asset_id == asset_id,
            AssetEditRequest.status == "pending"
        ).first()
        if existing_request:
            raise HTTPException(status_code=400, detail="该资产已有待审批的编辑申请，请等待审批完成或先撤回现有申请")
        
        # 构建编辑数据（排除状态字段，普通用户不能修改状态/可用状态）
        update_data = asset_data.dict(exclude_unset=True)
        if "status" in update_data:
            del update_data["status"]  # 移除状态字段
        if "available_status" in update_data:
            del update_data["available_status"]
        
        # 记录旧值（包含所有可能修改的字段，与 AssetUpdate 一致，避免未传字段被误判为有变更）
        old_values = {
            "category_id": asset.category_id,
            "name": asset.name,
            "specification": asset.specification,
            "status": asset.status,
            "available_status": asset.available_status,
            "mac_address": asset.mac_address,
            "ip_address": asset.ip_address,
            "office_location": asset.office_location,
            "floor": asset.floor,
            "seat_number": asset.seat_number,
            "user_id": asset.user_id,
            "user_group": asset.user_group,
            "remark": asset.remark,
            "quantity": asset.quantity,
            "team": asset.team,
            "purchase_date": asset.purchase_date,
            "card_number": asset.card_number,
            "safety_check_executor_id": asset.safety_check_executor_id,
            "safety_check_executor_name": asset.safety_check_executor_name,
            "computer_type": asset.computer_type,
            "computer_usage": asset.computer_usage,
            "computer_name": asset.computer_name,
            "monitor1_model": asset.monitor1_model,
            "monitor1_asset_number": asset.monitor1_asset_number,
            "monitor1_serial": asset.monitor1_serial,
            "monitor2_model": asset.monitor2_model,
            "monitor2_asset_number": asset.monitor2_asset_number,
            "monitor2_serial": asset.monitor2_serial,
            "asset_contact": asset.asset_contact,
            "reserve_1": asset.reserve_1,
            "reserve_2": asset.reserve_2,
            "reserve_3": asset.reserve_3,
            "reserve_4": asset.reserve_4,
            "reserve_5": asset.reserve_5,
            "reserve_6": asset.reserve_6,
        }
        
        # 只保留真正有变化的字段
        changed_fields = {}
        for k, v in update_data.items():
            old_val = old_values.get(k)
            # 处理空值比较：None、空字符串、空值都视为相同
            old_val_normalized = old_val if old_val is not None and old_val != "" else None
            new_val_normalized = v if v is not None and v != "" else None
            if old_val_normalized != new_val_normalized:
                changed_fields[k] = v
        
        # 如果没有字段变化，不允许创建编辑申请
        if not changed_fields:
            raise HTTPException(status_code=400, detail="没有字段发生变化，无需提交编辑申请")
        
        # 将 date/datetime 转为字符串，以便 json.dumps 序列化
        def _serializable_value(v):
            if isinstance(v, (date, datetime)):
                return v.isoformat()
            return v
        serializable_changed = {k: _serializable_value(v) for k, v in changed_fields.items()}
        
        # 创建编辑申请（只存储有变化的字段）
        db_request = AssetEditRequest(
            asset_id=asset_id,
            user_id=current_user.id,
            edit_data=json.dumps(serializable_changed, ensure_ascii=False),
            status="pending"
        )
        db.add(db_request)
        db.flush()
        
        # 记录编辑申请历史
        try:
            create_history = get_create_history_record()
            # 导入字段名映射函数
            from routers.asset_history import get_field_label
            field_labels = [get_field_label(field) for field in changed_fields.keys()]
            create_history(
                db=db,
                asset_id=asset_id,
                action_type="edit",
                action_description=f"申请编辑资产：修改了 {', '.join(field_labels) if field_labels else '无变化'}",
                operator_id=current_user.id,
                old_value={k: old_values.get(k) for k in changed_fields.keys() if k in old_values},
                new_value=changed_fields,
                related_request_id=db_request.id,
                related_request_type="edit"
            )
        except Exception as e:
            logger.error(f"记录编辑申请历史失败: {e}", exc_info=True)
        
        logger.info(f"用户 {current_user.ehr_number}({current_user.real_name}) 提交资产编辑申请: {asset.asset_number} - {asset.name}, 修改字段: {', '.join(changed_fields.keys()) if changed_fields else '无'}")
        
        db.commit()
        # 返回成功消息，前端需要特殊处理
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=200,
            content={"message": "编辑申请已提交，等待管理员审批", "edit_request_id": db_request.id}
        )
    
    # 管理员和组长直接更新资产
    # 记录旧值
    old_values = {
        "name": asset.name,
        "specification": asset.specification,
        "status": asset.status,
        "available_status": asset.available_status,
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
    update_data = asset_data.dict(exclude_unset=True)
    
    # 使用人可为管理员（管理员名下可有资产并对自己资产做检查）
    # （不再限制「使用人不能是管理员」）
    
    # 【改动：延迟调拨生效拦截】
    is_reallocation = False
    new_user_id = asset_data.user_id
    if "user_id" in update_data and new_user_id != old_values.get("user_id"):
        is_reallocation = True
        del update_data["user_id"]
        if "user_group" in update_data:
            del update_data["user_group"] # 等调拨生效时一起改

    changed_fields = []
    for field, value in update_data.items():
        old_val = getattr(asset, field, None)
        if old_val != value:
            setattr(asset, field, value)
            changed_fields.append(field)
            
    # 【新增：延迟调用和安检派发】仅修改使用人时联动；仅修改使用人组别不联动
    triggered_safety_check = False
    old_user_id = old_values.get("user_id")
    if is_reallocation:
        from models import PendingReallocation
        # 如果原来有使用人，派发给旧人查（转出核验）；如果没人在库房（如新资产），派发给新人（入职上岗核验）
        allocated_user_id = old_user_id if old_user_id else new_user_id
        assigned_id = getattr(asset, "safety_check_executor_id", None) or allocated_user_id
        if assigned_id:
            try:
                task = create_system_allocated_task(
                    db=db,
                    asset_id=asset.id,
                    assigned_user_id=assigned_id,
                    source="reallocation"
                )
                if task:
                    triggered_safety_check = True
                    pending = PendingReallocation(
                        asset_id=asset.id,
                        new_user_id=new_user_id,
                        task_id=task.id
                    )
                    db.add(pending)
                logger.info(f"生成待生效调拨记录：资产 {asset.asset_number} 拟移交至新用户ID {new_user_id}")
            except Exception as e:
                logger.error(f"调拨时触发系统安检任务下发失败: {e}", exc_info=True)
    
    # 如果状态改为"在库"，将未完成的安全检查任务标记为已退库
    if "status" in changed_fields and asset.status == "在库":
        pending_task_assets = db.query(TaskAsset).filter(
            TaskAsset.asset_id == asset.id,
            TaskAsset.status == "pending"
        ).all()
        
        for task_asset in pending_task_assets:
            task_asset.status = "returned"  # 标记为已退库
            logger.info(f"资产编辑：安全检查任务资产关联ID {task_asset.id} 已标记为已退库")
    
    # 记录编辑历史
    if changed_fields or is_reallocation:
        try:
            # 导入字段名映射函数
            from routers.asset_history import get_field_label
            field_labels = [get_field_label(field) for field in changed_fields]
            if is_reallocation:
                field_labels.append("使用人(待安检生效)")
        except Exception as e:
            logger.error(f"导入字段名映射函数失败: {e}", exc_info=True)
            # 如果导入失败，使用原始字段名
            field_labels = changed_fields
            if is_reallocation:
                field_labels.append("user_id(待结案生效)")
        
        logger.info(f"管理员/组长 {current_user.ehr_number}({current_user.real_name}) 编辑资产: {asset.asset_number} - {asset.name}, 修改字段: {', '.join(field_labels)}")
        try:
            create_history = get_create_history_record()
            new_values = {field: getattr(asset, field) for field in changed_fields}
            
            # 把被截留的新主人放进前端历史记录显示面板里
            if is_reallocation:
                new_values["user_id(待结案生效)"] = new_user_id
                
            create_history(
                db=db,
                asset_id=asset.id,
                action_type="edit",
                action_description=f"编辑资产：修改了 {', '.join(field_labels)}",
                operator_id=current_user.id,
                old_value={k: old_values.get(k) for k in changed_fields if k in old_values},
                new_value=new_values
            )
        except Exception as e:
            logger.error(f"记录编辑历史失败: {e}", exc_info=True)
    
    db.commit()
    db.refresh(asset)
    resp = AssetResponse.model_validate(asset)
    return AssetUpdateResponse(**(resp.model_dump()), triggered_safety_check=triggered_safety_check)


@router.delete("/{asset_id}")
async def delete_asset(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除资产（仅管理员，软删除）"""
    # 只有管理员可以删除资产
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="只有管理员可以删除资产")
    
    # 查询资产，包括已删除的（用于检查是否存在）
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="资产不存在")
    
    # 检查是否已经删除
    if asset.deleted_at is not None:
        raise HTTPException(status_code=400, detail="资产已被删除")
    
    # 软删除：设置删除时间和删除人
    asset.deleted_at = now_east8()
    asset.deleted_by_id = current_user.id
    
    logger.info(f"管理员 {current_user.ehr_number}({current_user.real_name}) 删除资产: {asset.asset_number} - {asset.name}")
    
    # 记录删除历史
    try:
        create_history = get_create_history_record()
        create_history(
            db=db,
            asset_id=asset.id,
            action_type="delete",
            action_description=f"删除资产：{asset.asset_number} - {asset.name}",
            operator_id=current_user.id,
            old_value={
                "asset_number": asset.asset_number,
                "name": asset.name,
                "status": asset.status,
                "user_id": asset.user_id
            }
        )
    except Exception as e:
        logger.error(f"记录删除历史失败: {e}", exc_info=True)
    
    db.commit()
    db.refresh(asset)
    return {"message": "资产已删除"}


@router.post("/import", response_model=ImportResponse)
async def import_assets(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    批量导入资产（仅管理员）
    Excel格式要求：
    - 列名：资产编号、所属大类、实物名称、规格型号（可选）、状态（在用/在库）、
            MAC地址（可选）、IP地址（可选）、存放办公地点（可选）、存放楼层（可选）、
            座位号（可选）、使用人EHR号（可选）、组别/使用人组别（可选）、备注说明（可选）
    """
    # 只有管理员可以批量导入
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="只有管理员可以批量导入资产")
    
    try:
        # 读取Excel文件
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents))
        
        # 验证必需的列
        required_columns = ['资产编号', '所属大类', '实物名称']
        for col in required_columns:
            if col not in df.columns:
                raise HTTPException(
                    status_code=400,
                    detail=f"Excel文件缺少必需的列：{col}"
                )
        
        success_count = 0
        error_count = 0
        skip_count = 0
        errors = []
        error_details = []
        conflict_count = 0
        conflict_details: List[ImportConflictDetail] = []
        
        for index, row in df.iterrows():
            row_number = index + 2  # Excel行号（从2开始，第1行是表头）
            row_data = row.to_dict()  # 保存原始行数据
            
            try:
                # 使用 Savepoint (嵌套事务) 确保单行失败不影响整体 (Bug 15 / B11)
                with db.begin_nested():
                    # 单元格先转字符串（空/NaN→''，数字浮点去 .0），再按 DB 类型用
                    asset_number = cell_to_str(row.get('资产编号', ''))
                    category_name = cell_to_str(row.get('所属大类', ''))
                    name = cell_to_str(row.get('实物名称', ''))
                    # 行级必填校验（参考用户批量导入）
                    if not (asset_number and str(asset_number).strip()) or not (category_name and str(category_name).strip()) or not (name and str(name).strip()):
                        raise ValueError("资产编号、所属大类、实物名称为必填")
                    
                    # 按资产编号查库（含已逻辑删除），用于判断：未删除则比对冲突/跳过，已删除则恢复+更新
                    existing_any = db.query(Asset).filter(Asset.asset_number == asset_number).first()
                    
                    # 查找或创建资产大类
                    category = db.query(AssetCategory).filter(AssetCategory.name == category_name).first()
                    if not category:
                        category = AssetCategory(name=category_name)
                        db.add(category)
                        db.flush()
                    
                    specification = row_cell_str(row, df.columns, '规格型号') or None
                    # 状态：优先读「实物状态」，若无则读「状态」；只允许在用/在库/库存备用
                    status_raw = row_cell_str(row, df.columns, '实物状态', '状态') or '在用'
                    if status_raw not in ('在用', '在库', '库存备用'):
                        raise ValueError(f"状态必须是：在用、在库、库存备用，当前为「{status_raw}」")
                    
                    status = '在库' if status_raw == '库存备用' else status_raw
                    available_status_raw = row_cell_str(row, df.columns, '可用状态') or '可用'
                    if available_status_raw not in ('可用', '维修中', '已报废'):
                        available_status_raw = '可用'
                    available_status = available_status_raw
                    mac_address = row_cell_str(row, df.columns, '终端mac地址', 'MAC地址') or None
                    ip_address = row_cell_str(row, df.columns, '终端IP号', 'IP地址') or None
                    office_location = row_cell_str(row, df.columns, '存放办公地点') or None
                    floor = row_cell_str(row, df.columns, '具体存放楼层', '存放楼层') or None
                    seat_number = row_cell_str(row, df.columns, '座位号') or None
                    user_group = row_cell_str(row, df.columns, '使用人组别', '组別', '组别') or None
                    remark = row_cell_str(row, df.columns, '备注说明') or None
                    quantity = str_to_int(row_cell_str(row, df.columns, '件数'), default=None)
                    if quantity is not None and quantity < 1:
                        quantity = 1
                    if quantity is None:
                        quantity = 1
                    team = row_cell_str(row, df.columns, '所在团队') or None
                    purchase_date = cell_to_date(row.get('购置日期')) if '购置日期' in df.columns else None
                    card_number = row_cell_str(row, df.columns, '卡片编号') or None
                    computer_type = row_cell_str(row, df.columns, '电脑类型') or None
                    computer_usage = row_cell_str(row, df.columns, '电脑应用') or None
                    computer_name = row_cell_str(row, df.columns, '计算机名') or None
                    monitor1_model = row_cell_str(row, df.columns, '连接显示器1型号') or None
                    monitor1_asset_number = row_cell_str(row, df.columns, '连接显示器1资产编号') or None
                    monitor1_serial = row_cell_str(row, df.columns, '显示器1 序列号', '显示器1序列号') or None
                    monitor2_model = row_cell_str(row, df.columns, '连接显示器2', '连接显示器2型号') or None
                    monitor2_asset_number = row_cell_str(row, df.columns, '连接显示器2资产编号') or None
                    monitor2_serial = row_cell_str(row, df.columns, '显示器2序列号') or None
                    asset_contact = row_cell_str(row, df.columns, '资产管理联系人') or None
                    reserve_1 = row_cell_str(row, df.columns, '预留1') or None
                    reserve_2 = row_cell_str(row, df.columns, '预留2') or None
                    reserve_3 = row_cell_str(row, df.columns, '预留3') or None
                    reserve_4 = row_cell_str(row, df.columns, '预留4') or None
                    reserve_5 = row_cell_str(row, df.columns, '预留5') or None
                    reserve_6 = row_cell_str(row, df.columns, '预留6') or None
                    safety_check_executor_id = str_to_int(row_cell_str(row, df.columns, '检查执行人ID'), default=None)
                    safety_check_executor_name = row_cell_str(row, df.columns, '检查执行人') or None
                    if safety_check_executor_id is None and safety_check_executor_name:
                        u = db.query(User).filter(
                            User.real_name == safety_check_executor_name.strip(),
                            User.deleted_at.is_(None)
                        ).first()
                        if u:
                            safety_check_executor_id = u.id
                    
                    # 解析使用人（所有人）：优先所有人ID，否则所有人（姓名），否则使用人EHR号
                    user_id = str_to_int(row_cell_str(row, df.columns, '所有人ID'), default=None)
                    if user_id is not None:
                        u = db.query(User).filter(User.id == user_id, User.deleted_at.is_(None)).first()
                        if not u:
                            user_id = None
                        elif not user_group:
                            user_group = u.group
                    if user_id is None:
                        owner_name = row_cell_str(row, df.columns, '所有人')
                        if owner_name:
                            u = db.query(User).filter(
                                User.real_name == owner_name.strip(),
                                User.deleted_at.is_(None)
                            ).first()
                            if u:
                                user_id = u.id
                                if not user_group:
                                    user_group = u.group
                            else:
                                raise ValueError(f"所有人「{owner_name}」未找到对应用户")
                    
                    if user_id is None:
                        user_ehr = row_cell_str(row, df.columns, '使用人EHR号')
                        if user_ehr:
                            user = db.query(User).filter(User.ehr_number == user_ehr, User.deleted_at.is_(None)).first()
                            if user:
                                user_id = user.id
                                if not user_group:
                                    user_group = user.group
                            else:
                                raise ValueError(f"使用人EHR号{user_ehr}不存在")
                    
                    # 若仅修改了使用人且未显式指定执行人，则将执行人重置为新使用人
                    if user_id is not None and safety_check_executor_id is None and not safety_check_executor_name:
                        u = db.query(User).filter(User.id == user_id, User.deleted_at.is_(None)).first()
                        if u:
                            safety_check_executor_id = u.id
                            safety_check_executor_name = u.real_name
                    
                    assigned_id = safety_check_executor_id or user_id
                    
                    # 已存在且未删除：比对差异，有差异则加入冲突列表供用户选择覆盖/保持
                    if existing_any and existing_any.deleted_at is None:
                        parsed = {
                            "category_id": category.id, "name": name, "specification": specification,
                            "status": status, "available_status": available_status, "mac_address": mac_address, "ip_address": ip_address,
                            "office_location": office_location, "floor": floor, "seat_number": seat_number,
                            "user_id": user_id, "user_group": user_group, "remark": remark,
                            "quantity": quantity, "team": team, "purchase_date": purchase_date,
                            "card_number": card_number, "safety_check_executor_id": safety_check_executor_id,
                            "safety_check_executor_name": safety_check_executor_name,
                            "computer_type": computer_type, "computer_usage": computer_usage, "computer_name": computer_name,
                            "monitor1_model": monitor1_model, "monitor1_asset_number": monitor1_asset_number, "monitor1_serial": monitor1_serial,
                            "monitor2_model": monitor2_model, "monitor2_asset_number": monitor2_asset_number, "monitor2_serial": monitor2_serial,
                            "asset_contact": asset_contact,
                            "reserve_1": reserve_1, "reserve_2": reserve_2, "reserve_3": reserve_3,
                            "reserve_4": reserve_4, "reserve_5": reserve_5, "reserve_6": reserve_6,
                        }
                        diffs = _build_import_conflict_diffs(existing_any, parsed, db)
                        if not diffs:
                            skip_count += 1
                            return # 这里跳出 begin_nested，继续下一行
                        conflict_count += 1
                        conflict_details.append(ImportConflictDetail(
                            row_number=row_number,
                            asset_number=asset_number,
                            asset_id=existing_any.id,
                            diffs=diffs,
                            row_data=row_to_error_dict(row_data),
                        ))
                        return # 继续下一行
                    
                    if existing_any and existing_any.deleted_at is not None:
                        # 存在且已逻辑删除：恢复并更新该行，不插入
                        existing_any.deleted_at = None
                        existing_any.deleted_by_id = None
                        existing_any.category_id = category.id
                        existing_any.name = name
                        existing_any.specification = specification or None
                        existing_any.status = status
                        existing_any.available_status = available_status
                        existing_any.mac_address = mac_address or None
                        existing_any.ip_address = ip_address or None
                        existing_any.office_location = office_location or None
                        existing_any.floor = floor or None
                        existing_any.seat_number = seat_number or None
                        existing_any.user_id = user_id
                        existing_any.user_group = user_group or None
                        existing_any.remark = remark or None
                        existing_any.quantity = quantity
                        existing_any.team = team
                        existing_any.purchase_date = purchase_date
                        existing_any.card_number = card_number
                        existing_any.safety_check_executor_id = safety_check_executor_id
                        existing_any.safety_check_executor_name = safety_check_executor_name
                        existing_any.computer_type = computer_type
                        existing_any.computer_usage = computer_usage
                        existing_any.computer_name = computer_name
                        existing_any.monitor1_model = monitor1_model
                        existing_any.monitor1_asset_number = monitor1_asset_number
                        existing_any.monitor1_serial = monitor1_serial
                        existing_any.monitor2_model = monitor2_model
                        existing_any.monitor2_asset_number = monitor2_asset_number
                        existing_any.monitor2_serial = monitor2_serial
                        existing_any.asset_contact = asset_contact
                        existing_any.reserve_1 = reserve_1
                        existing_any.reserve_2 = reserve_2
                        existing_any.reserve_3 = reserve_3
                        existing_any.reserve_4 = reserve_4
                        existing_any.reserve_5 = reserve_5
                        existing_any.reserve_6 = reserve_6
                        db.flush()
                        if assigned_id:
                            try:
                                create_system_allocated_task(db=db, asset_id=existing_any.id, assigned_user_id=assigned_id, source="inbound")
                            except Exception as e:
                                logger.error(f"批量导入恢复资产时触发系统安检任务下发失败: {e}", exc_info=True)
                        success_count += 1
                        return # 继续下一行
                    
                    # 不存在：新增
                    db_asset = Asset(
                        asset_number=asset_number,
                        category_id=category.id,
                        name=name,
                        specification=specification or None,
                        status=status,
                        available_status=available_status,
                        mac_address=mac_address or None,
                        ip_address=ip_address or None,
                        office_location=office_location or None,
                        floor=floor or None,
                        seat_number=seat_number or None,
                        user_id=user_id,
                        user_group=user_group or None,
                        remark=remark or None,
                        quantity=quantity,
                        team=team,
                        purchase_date=purchase_date,
                        card_number=card_number,
                        safety_check_executor_id=safety_check_executor_id,
                        safety_check_executor_name=safety_check_executor_name,
                        computer_type=computer_type,
                        computer_usage=computer_usage,
                        computer_name=computer_name,
                        monitor1_model=monitor1_model,
                        monitor1_asset_number=monitor1_asset_number,
                        monitor1_serial=monitor1_serial,
                        monitor2_model=monitor2_model,
                        monitor2_asset_number=monitor2_asset_number,
                        monitor2_serial=monitor2_serial,
                        asset_contact=asset_contact,
                        reserve_1=reserve_1,
                        reserve_2=reserve_2,
                        reserve_3=reserve_3,
                        reserve_4=reserve_4,
                        reserve_5=reserve_5,
                        reserve_6=reserve_6,
                    )
                    db.add(db_asset)
                    db.flush()
                    if assigned_id:
                        try:
                            create_system_allocated_task(db=db, asset_id=db_asset.id, assigned_user_id=assigned_id, source="inbound")
                        except Exception as e:
                            logger.error(f"批量导入时触发系统安检任务下发失败: {e}", exc_info=True)
                    success_count += 1
            
            except Exception as e:
                # 注：begin_nested() 这里的异常会自动回滚子事务（这一行）
                error_count += 1
                error_msg = str(e)
                errors.append(f"第{row_number}行：{error_msg}")
                error_details.append({
                    "row_number": row_number,
                    "error_message": error_msg,
                    "row_data": row_to_error_dict(row_data)
                })
        
        db.commit()
        
        # 限制返回的错误与冲突数量
        max_errors = 100
        max_conflicts = 100
        limited_errors = errors[:max_errors]
        limited_error_details = error_details[:max_errors]
        limited_conflict_details = conflict_details[:max_conflicts]
        
        return ImportResponse(
            success_count=success_count,
            error_count=error_count,
            skip_count=skip_count,
            errors=limited_errors,
            error_details=limited_error_details,
            conflict_count=conflict_count,
            conflict_details=limited_conflict_details,
        )
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"导入失败：{str(e)}")


@router.post("/import-resolve")
async def resolve_import_conflicts(
    body: ImportResolveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    解决导入冲突：用户选择「覆盖」则用导入数据更新资产，选择「保持」则不修改。
    仅管理员可调用。
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="只有管理员可以处理导入冲突")
    overwrite_count = 0
    errors_resolve = []
    for d in body.decisions:
        asset = db.query(Asset).filter(Asset.id == d.asset_id, Asset.deleted_at.is_(None)).first()
        if not asset:
            errors_resolve.append(f"资产ID {d.asset_id} 不存在或已删除，已跳过")
            continue
        if d.action == "keep":
            continue
        if d.action != "overwrite" or not d.row_data:
            errors_resolve.append(f"资产 {asset.asset_number}：覆盖操作需要提供 row_data")
            continue
        try:
            parsed, _ = _parse_row_data_for_resolve(d.row_data, db)
        except Exception as e:
            errors_resolve.append(f"资产 {asset.asset_number} 解析 row_data 失败：{str(e)}")
            continue
        # 使用人可为管理员（管理员名下可有资产）
        # 覆盖前保存旧值，用于流转记录与编辑历史
        old_user_id = asset.user_id
        old_name = asset.name
        old_status = asset.status
        old_user = db.query(User).filter(User.id == old_user_id).first() if old_user_id else None
        asset.category_id = parsed["category_id"]
        asset.name = parsed["name"]
        asset.specification = parsed["specification"]
        asset.status = parsed["status"]
        asset.available_status = parsed.get("available_status", "可用")
        asset.mac_address = parsed["mac_address"]
        asset.ip_address = parsed["ip_address"]
        asset.office_location = parsed["office_location"]
        asset.floor = parsed["floor"]
        asset.seat_number = parsed["seat_number"]
        asset.user_id = parsed["user_id"]
        asset.user_group = parsed["user_group"]
        asset.remark = parsed["remark"]
        asset.quantity = parsed["quantity"]
        asset.team = parsed["team"]
        asset.purchase_date = parsed["purchase_date"]
        asset.card_number = parsed["card_number"]
        asset.safety_check_executor_id = parsed["safety_check_executor_id"]
        asset.safety_check_executor_name = parsed["safety_check_executor_name"]
        asset.computer_type = parsed["computer_type"]
        asset.computer_usage = parsed["computer_usage"]
        asset.computer_name = parsed["computer_name"]
        asset.monitor1_model = parsed["monitor1_model"]
        asset.monitor1_asset_number = parsed["monitor1_asset_number"]
        asset.monitor1_serial = parsed["monitor1_serial"]
        asset.monitor2_model = parsed["monitor2_model"]
        asset.monitor2_asset_number = parsed["monitor2_asset_number"]
        asset.monitor2_serial = parsed["monitor2_serial"]
        asset.asset_contact = parsed["asset_contact"]
        asset.reserve_1 = parsed["reserve_1"]
        asset.reserve_2 = parsed["reserve_2"]
        asset.reserve_3 = parsed["reserve_3"]
        asset.reserve_4 = parsed["reserve_4"]
        asset.reserve_5 = parsed["reserve_5"]
        asset.reserve_6 = parsed["reserve_6"]
        overwrite_count += 1
        try:
            create_history = get_create_history_record()
            create_history(
                db=db,
                asset_id=asset.id,
                action_type="edit",
                action_description=f"导入冲突解决：用户选择覆盖，更新资产 {asset.asset_number}",
                operator_id=current_user.id,
                old_value={"name": old_name, "status": old_status, "user_id": old_user_id},
                new_value={"name": asset.name, "status": asset.status, "user_id": asset.user_id},
            )
            # 使用人变动时新增一条流转记录
            if old_user_id != parsed["user_id"]:
                new_user = db.query(User).filter(User.id == asset.user_id).first() if asset.user_id else None
                create_history(
                    db=db,
                    asset_id=asset.id,
                    action_type="transfer",
                    action_description=f"导入覆盖导致使用人变更：资产 {asset.asset_number}",
                    operator_id=current_user.id,
                    old_value={"user_id": old_user_id, "user_name": old_user.real_name if old_user else ""},
                    new_value={"user_id": asset.user_id, "user_name": new_user.real_name if new_user else ""},
                )
        except Exception as e:
            logger.error(f"记录导入覆盖历史失败: {e}", exc_info=True)
    db.commit()
    return {
        "message": f"已处理 {len(body.decisions)} 条，其中覆盖 {overwrite_count} 条",
        "overwrite_count": overwrite_count,
        "errors": errors_resolve,
    }
