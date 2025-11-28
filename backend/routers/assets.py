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
from schemas import AssetCreate, AssetUpdate, AssetResponse, ImportResponse
from auth import get_current_user
import pandas as pd
import io
from fastapi.responses import StreamingResponse
from logger import logger
# 延迟导入避免循环依赖
def get_create_history_record():
    from routers import asset_history
    return asset_history.create_history_record
from datetime import datetime

router = APIRouter()


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
    
    # 普通用户只能查看自己名下的资产
    if current_user.role != "admin" and asset.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权查看此资产")
    
    return AssetResponse.model_validate(asset)


@router.post("/", response_model=AssetResponse)
async def create_asset(
    asset_data: AssetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建新资产"""
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

    # 如果是普通用户，强制将资产归属到自己，并设置默认状态
    if current_user.role != "admin":
        asset_dict["user_id"] = current_user.id
        asset_dict["user_group"] = current_user.group
        # 普通用户不能设置状态，默认设置为"在用"
        if "status" in asset_dict:
            del asset_dict["status"]  # 移除用户提交的状态
        asset_dict["status"] = "在用"  # 默认设置为"在用"
    else:
        # 管理员创建时，如指定了使用人则检查
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
    return AssetResponse.model_validate(db_asset)


@router.put("/{asset_id}", response_model=AssetResponse)
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
    if current_user.role != "admin" and asset.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="只能编辑自己名下的资产")
    
    # 普通用户不能修改使用人
    if current_user.role != "admin" and asset_data.user_id is not None:
        if asset_data.user_id != asset.user_id:
            raise HTTPException(status_code=403, detail="普通用户不能修改资产使用人")
    
    # 如果是普通用户，提交编辑申请而不是直接更新
    if current_user.role != "admin":
        import json
        from models import AssetEditRequest
        
        # 检查是否已有待审批的编辑申请
        existing_request = db.query(AssetEditRequest).filter(
            AssetEditRequest.asset_id == asset_id,
            AssetEditRequest.status == "pending"
        ).first()
        if existing_request:
            raise HTTPException(status_code=400, detail="该资产已有待审批的编辑申请，请等待审批完成或先撤回现有申请")
        
        # 构建编辑数据（排除状态字段，普通用户不能修改状态）
        update_data = asset_data.dict(exclude_unset=True)
        if "status" in update_data:
            del update_data["status"]  # 移除状态字段
        
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
        
        # 创建编辑申请（只存储有变化的字段）
        db_request = AssetEditRequest(
            asset_id=asset_id,
            user_id=current_user.id,
            edit_data=json.dumps(changed_fields, ensure_ascii=False),
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
    
    # 管理员直接更新资产
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
    update_data = asset_data.dict(exclude_unset=True)
    changed_fields = []
    for field, value in update_data.items():
        old_val = getattr(asset, field, None)
        if old_val != value:
            setattr(asset, field, value)
            changed_fields.append(field)
    
    # 如果更新了使用人，自动更新组别
    old_user_id = old_values.get("user_id")
    if asset_data.user_id is not None:
        user = db.query(User).filter(User.id == asset_data.user_id).first()
        if user:
            asset.user_group = user.group
    
    # 处理安全检查任务
    # 如果修改了使用人，更新未完成的安全检查任务到新接收人
    if "user_id" in changed_fields and asset_data.user_id is not None and asset_data.user_id != old_user_id:
        pending_task_assets = db.query(TaskAsset).filter(
            TaskAsset.asset_id == asset.id,
            TaskAsset.status == "pending"
        ).all()
        
        new_user = db.query(User).filter(User.id == asset_data.user_id).first()
        for task_asset in pending_task_assets:
            task_asset.assigned_user_id = asset_data.user_id
            logger.info(f"资产编辑：安全检查任务资产关联ID {task_asset.id} 已更新到新接收人 {new_user.real_name if new_user else ''}")
    
    # 如果状态改为"库存备用"，将未完成的安全检查任务标记为已退库
    if "status" in changed_fields and asset.status == "库存备用":
        pending_task_assets = db.query(TaskAsset).filter(
            TaskAsset.asset_id == asset.id,
            TaskAsset.status == "pending"
        ).all()
        
        for task_asset in pending_task_assets:
            task_asset.status = "returned"  # 标记为已退库
            logger.info(f"资产编辑：安全检查任务资产关联ID {task_asset.id} 已标记为已退库")
    
    # 记录编辑历史
    if changed_fields:
        try:
            # 导入字段名映射函数
            from routers.asset_history import get_field_label
            field_labels = [get_field_label(field) for field in changed_fields]
        except Exception as e:
            logger.error(f"导入字段名映射函数失败: {e}", exc_info=True)
            # 如果导入失败，使用原始字段名
            field_labels = changed_fields
        
        logger.info(f"管理员 {current_user.ehr_number}({current_user.real_name}) 编辑资产: {asset.asset_number} - {asset.name}, 修改字段: {', '.join(field_labels)}")
        try:
            create_history = get_create_history_record()
            new_values = {field: getattr(asset, field) for field in changed_fields}
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
    return AssetResponse.model_validate(asset)


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
    asset.deleted_at = datetime.utcnow()
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
    - 列名：资产编号、所属大类、实物名称、规格型号（可选）、状态（在用/库存备用）、
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
        errors = []
        error_details = []
        
        for index, row in df.iterrows():
            row_number = index + 2  # Excel行号（从2开始，第1行是表头）
            row_data = row.to_dict()  # 保存原始行数据
            
            try:
                asset_number = str(row['资产编号']).strip()
                category_name = str(row['所属大类']).strip()
                name = str(row['实物名称']).strip()
                
                # 检查资产编号是否已存在（只检查未删除的）
                existing = db.query(Asset).filter(
                    Asset.asset_number == asset_number,
                    Asset.deleted_at.is_(None)
                ).first()
                if existing:
                    error_count += 1
                    error_msg = f"资产编号{asset_number}已存在"
                    errors.append(f"第{row_number}行：{error_msg}")
                    # 转换行数据为字典，处理NaN值
                    row_data_dict = {}
                    for k, v in row_data.items():
                        if pd.isna(v) or v is None:
                            row_data_dict[k] = ''
                        else:
                            row_data_dict[k] = str(v)
                    
                    error_details.append({
                        "row_number": row_number,
                        "error_message": error_msg,
                        "row_data": row_data_dict
                    })
                    continue
                
                # 查找或创建资产大类
                category = db.query(AssetCategory).filter(AssetCategory.name == category_name).first()
                if not category:
                    # 自动创建大类
                    category = AssetCategory(name=category_name)
                    db.add(category)
                    db.flush()
                
                # 获取其他字段
                specification = str(row.get('规格型号', '')).strip() if '规格型号' in df.columns else None
                status = str(row.get('状态', '在用')).strip() if '状态' in df.columns else '在用'
                mac_address = str(row.get('MAC地址', '')).strip() if 'MAC地址' in df.columns else None
                ip_address = str(row.get('IP地址', '')).strip() if 'IP地址' in df.columns else None
                office_location = str(row.get('存放办公地点', '')).strip() if '存放办公地点' in df.columns else None
                floor = str(row.get('存放楼层', '')).strip() if '存放楼层' in df.columns else None
                seat_number = str(row.get('座位号', '')).strip() if '座位号' in df.columns else None
                user_ehr = str(row.get('使用人EHR号', '')).strip() if '使用人EHR号' in df.columns else None
                # 支持两种列名：使用人组别 或 组别
                user_group = None
                if '使用人组别' in df.columns:
                    user_group = str(row.get('使用人组别', '')).strip() or None
                elif '组别' in df.columns:
                    user_group = str(row.get('组别', '')).strip() or None
                remark = str(row.get('备注说明', '')).strip() if '备注说明' in df.columns else None
                
                # 如果提供了使用人EHR号，查找用户
                user_id = None
                if user_ehr:
                    user = db.query(User).filter(User.ehr_number == user_ehr).first()
                    if user:
                        user_id = user.id
                        if not user_group:
                            user_group = user.group
                    else:
                        error_count += 1
                        error_msg = f"使用人EHR号{user_ehr}不存在"
                        errors.append(f"第{row_number}行：{error_msg}")
                        # 转换行数据为字典，处理NaN值
                        row_data_dict = {}
                        for k, v in row_data.items():
                            if pd.isna(v) or v is None:
                                row_data_dict[k] = ''
                            else:
                                row_data_dict[k] = str(v)
                        
                        error_details.append({
                            "row_number": row_number,
                            "error_message": error_msg,
                            "row_data": row_data_dict
                        })
                        continue
                
                # 创建资产
                db_asset = Asset(
                    asset_number=asset_number,
                    category_id=category.id,
                    name=name,
                    specification=specification if specification else None,
                    status=status,
                    mac_address=mac_address if mac_address else None,
                    ip_address=ip_address if ip_address else None,
                    office_location=office_location if office_location else None,
                    floor=floor if floor else None,
                    seat_number=seat_number if seat_number else None,
                    user_id=user_id,
                    user_group=user_group if user_group else None,
                    remark=remark if remark else None
                )
                db.add(db_asset)
                success_count += 1
                
            except Exception as e:
                error_count += 1
                error_msg = str(e)
                errors.append(f"第{row_number}行：{error_msg}")
                # 转换行数据为字典，处理NaN值
                row_data_dict = {}
                for k, v in row_data.items():
                    if pd.isna(v) or v is None:
                        row_data_dict[k] = ''
                    else:
                        row_data_dict[k] = str(v)
                
                error_details.append({
                    "row_number": row_number,
                    "error_message": error_msg,
                    "row_data": row_data_dict
                })
        
        db.commit()
        
        # 限制返回的错误数量
        max_errors = 100
        limited_errors = errors[:max_errors]
        limited_error_details = error_details[:max_errors]
        
        return ImportResponse(
            success_count=success_count,
            error_count=error_count,
            errors=limited_errors,
            error_details=limited_error_details
        )
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"导入失败：{str(e)}")
