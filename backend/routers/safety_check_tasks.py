"""
安全检查任务管理路由
管理员可以创建和管理任务，普通用户可以查看分配给自己的任务
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from sqlalchemy.exc import IntegrityError
import random
import string
import re
import io
from typing import List, Optional
from datetime import datetime
from database import get_db
from utils_time import now_east8
from models import (
    SafetyCheckTask, SafetyCheckType, TaskAsset, Asset, User
)
from schemas import (
    SafetyCheckTaskCreate, SafetyCheckTaskUpdate, SafetyCheckTaskResponse,
    TaskAssetResponse
)
from auth import get_current_user, get_current_admin_user
import json
from urllib.parse import quote
import pandas as pd

router = APIRouter()


def ensure_overdue_status_updated(db: Session) -> None:
    """
    方案 B：将截止时间已过且仍为 pending 的任务与任务资产更新为 overdue。
    待检查数/红点仅统计 pending，不统计 overdue。在 get_tasks / get_my_tasks 前调用。
    """
    now = now_east8()
    # 任务表：deadline 已过且 status 仍为 pending 的改为 overdue
    overdue_tasks = db.query(SafetyCheckTask).filter(
        SafetyCheckTask.deadline.isnot(None),
        SafetyCheckTask.deadline < now,
        SafetyCheckTask.status == "pending"
    ).all()
    for task in overdue_tasks:
        task.status = "overdue"
        # 该任务下仍为 pending 的 TaskAsset 改为 overdue
        db.query(TaskAsset).filter(
            TaskAsset.task_id == task.id,
            TaskAsset.status == "pending"
        ).update({TaskAsset.status: "overdue"}, synchronize_session="fetch")
    if overdue_tasks:
        db.commit()


def generate_task_number(db: Session, retry_count: int = 0) -> str:
    """生成任务编号：SAFETY-YYYY-NNN"""
    year = now_east8().year
    prefix = f"SAFETY-{year}-"
    # 采用 MAX 逻辑获取今年最大的末尾数字，比 count 更稳健（防止删除后编号重复）
    last_task = db.query(SafetyCheckTask).filter(
        SafetyCheckTask.task_number.like(f"{prefix}%")
    ).order_by(SafetyCheckTask.task_number.desc()).first()
    
    next_num = 1
    if last_task:
        try:
            # 提取最后三位或更多的数字部分
            last_num_str = last_task.task_number.replace(prefix, "")
            # 过滤掉可能的随机后缀（如果有的话）
            last_num_clean = "".join(filter(str.isdigit, last_num_str.split('-')[0]))
            if last_num_clean:
                next_num = int(last_num_clean) + 1
        except Exception:
            # 降级方案
            next_num = db.query(SafetyCheckTask).filter(
                SafetyCheckTask.task_number.like(f"{prefix}%")
            ).count() + 1
            
    number = f"{prefix}{str(next_num).zfill(3)}"
    
    # 如果是重试，由于已经发生了 IntegrityError，必须加上随机后缀打破竞态
    if retry_count > 0:
        random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        number = f"{number}-{random_str}"
        
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

    # 引入重试机制解决并发编号冲突（Bug 13 / B9）
    max_retries = 3
    for retry_count in range(max_retries):
        try:
            # 生成任务编号
            task_number = generate_task_number(db, retry_count)
            
            # 创建任务（管理员手动发布，来源为 manual）
            db_task = SafetyCheckTask(
                task_number=task_number,
                check_type_id=task_data.check_type_id,
                title=task_data.title,
                description=task_data.description,
                deadline=task_data.deadline,
                created_by_id=current_user.id,
                status="pending",
                source="manual"
            )
            db.add(db_task)
            db.flush()  # 获取任务ID
            
            # 为每个资产创建任务资产关联记录
            created_count = 0
            for asset in assets:
                assigned_id = getattr(asset, "safety_check_executor_id", None) or asset.user_id
                if not assigned_id:
                    continue
                
                task_asset = TaskAsset(
                    task_id=db_task.id,
                    asset_id=asset.id,
                    assigned_user_id=assigned_id,
                    status="pending"
                )
                db.add(task_asset)
                created_count += 1
            
            if created_count == 0:
                db.rollback()
                raise HTTPException(status_code=400, detail="所选资产都没有使用人或执行人，无法创建任务")
            
            db.commit()
            db.refresh(db_task)
            # 返回任务详情
            return await get_task_detail(db_task.id, db, current_user)
            
        except IntegrityError:
            db.rollback()
            if retry_count == max_retries - 1:
                raise HTTPException(status_code=500, detail="任务编号生成冲突，请稍后重试")
            continue  # 重试生成带随机后缀的新编号
        except HTTPException:
            raise
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=dict)
async def get_tasks(
    status: Optional[str] = Query(None, description="任务状态筛选"),
    source: Optional[str] = Query(None, description="任务来源筛选：manual/inbound/transfer/reallocation/resignation"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取任务列表"""
    ensure_overdue_status_updated(db)
    query = db.query(SafetyCheckTask)
    
    # 非管理员权限限制
    if current_user.role != "admin":
        if current_user.role == "leader":
            # 组长：可以看到分配给自己执行的任务，或者资产属于自己组的任务
            query = query.join(TaskAsset).join(Asset, TaskAsset.asset_id == Asset.id).filter(
                or_(
                    TaskAsset.assigned_user_id == current_user.id,
                    Asset.user_group == current_user.group
                )
            ).distinct()
        else:
            # 普通用户：只能查看分配给自己的任务
            query = query.join(TaskAsset).filter(
                TaskAsset.assigned_user_id == current_user.id
            ).distinct()
    
    # 状态筛选
    if status:
        query = query.filter(SafetyCheckTask.status == status)
    
    # 任务来源筛选（角色 D：任务列表按来源筛选）
    if source:
        query = query.filter(SafetyCheckTask.source == source)
    
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
                    task_dict["completed_at"] = now_east8()
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
                task.completed_at = now_east8()
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
    
    # 非管理员权限限制
    if current_user.role != "admin":
        if current_user.role == "leader":
            # 组长：自己执行的任务，或者包含本组资产的任务
            has_access = db.query(TaskAsset).join(Asset).filter(
                TaskAsset.task_id == task_id,
                or_(
                    TaskAsset.assigned_user_id == current_user.id,
                    Asset.user_group == current_user.group
                )
            ).first()
        else:
            # 普通用户：只能查看分配给自己的任务
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
                task.completed_at = now_east8()
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
    
    # 资产列表过滤：排除已退库的。管理员看全集，其他人受限。
    query = db.query(TaskAsset).join(Asset).filter(TaskAsset.task_id == task_id)
    if current_user.role == "admin":
        pass
    elif current_user.role == "leader":
        # 组长：看分配给自己的，或者属于本组的资产
        query = query.filter(
            or_(
                TaskAsset.assigned_user_id == current_user.id,
                Asset.user_group == current_user.group
            ),
            TaskAsset.status != "returned"
        )
    else:
        # 普通用户：仅看分配给自己的
        query = query.filter(
            TaskAsset.assigned_user_id == current_user.id,
            TaskAsset.status != "returned"
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


# Excel 导出固有列名（与需求一致）
EXPORT_FIXED_HEADERS = [
    "电脑类型（WINDOWS/信创）",
    "电脑应用（OA/BL）",
    "资产编号",
    "连接显示器1型号",
    "显示器1资产编号",
    "显示器1序列号",
    "连接显示器2型号",
    "显示器2资产编号",
    "显示器2序列号",
    "终端IP号",
    "终端MAC地址",
    "具体存放楼层",
    "使用人",
    "使用人EHR",
    "资产管理联系人",
]


def _safe_filename(title: str) -> str:
    """将任务标题转为安全文件名：去掉非法字符"""
    if not title or not title.strip():
        return "任务导出"
    s = re.sub(r'[\\/:*?"<>|]', '_', title.strip())
    return s[:100] if len(s) > 100 else s


@router.get("/{task_id}/export")
async def export_task_result(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """导出任务结果 Excel（仅管理员；仅已完成或已逾期任务；包含已退库资产）"""
    task = db.query(SafetyCheckTask).filter(SafetyCheckTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if task.status not in ("completed", "overdue"):
        raise HTTPException(status_code=400, detail="仅支持导出已完成或已逾期的任务")

    # 该任务下所有任务资产（含已退库）
    task_assets = db.query(TaskAsset).filter(TaskAsset.task_id == task_id).order_by(TaskAsset.id).all()
    check_type = db.query(SafetyCheckType).filter(SafetyCheckType.id == task.check_type_id).first()
    check_items = []
    if check_type and check_type.check_items:
        try:
            check_items = json.loads(check_type.check_items)
        except Exception:
            check_items = []
    # 检查项列名：按配置顺序，取 item 作为列名
    check_item_names = [item.get("item") or "" for item in check_items if isinstance(item, dict)]

    def _result_display(val):
        """导出时检查项结果 yes/no 转为 是/否"""
        if val == "yes":
            return "是"
        if val == "no":
            return "否"
        return val or ""

    headers = EXPORT_FIXED_HEADERS + check_item_names + ["备注"]
    rows = []

    for ta in task_assets:
        asset = ta.asset
        if not asset:
            continue
        user = asset.user
        row = {
            "电脑类型（WINDOWS/信创）": (asset.computer_type or ""),
            "电脑应用（OA/BL）": (asset.computer_usage or ""),
            "资产编号": (asset.asset_number or ""),
            "连接显示器1型号": (asset.monitor1_model or ""),
            "显示器1资产编号": (asset.monitor1_asset_number or ""),
            "显示器1序列号": (asset.monitor1_serial or ""),
            "连接显示器2型号": (asset.monitor2_model or ""),
            "显示器2资产编号": (asset.monitor2_asset_number or ""),
            "显示器2序列号": (asset.monitor2_serial or ""),
            "终端IP号": (asset.ip_address or ""),
            "终端MAC地址": (asset.mac_address or ""),
            "具体存放楼层": (asset.floor or ""),
            "使用人": (user.real_name if user else ""),
            "使用人EHR": (user.ehr_number if user else ""),
            "资产管理联系人": (asset.asset_contact or ""),
        }
        # 检查项结果
        items_result = ta.get_check_items_result()
        result_by_item = {x.get("item"): x.get("result") for x in items_result if isinstance(x, dict) and x.get("item")}
        for name in check_item_names:
            row[name] = _result_display(result_by_item.get(name))
        row["备注"] = (ta.check_comment or "")
        rows.append(row)

    df = pd.DataFrame(rows, columns=headers)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="检查结果")
    output.seek(0)

    date_str = now_east8().strftime("%Y%m%d")
    safe_title = _safe_filename(task.title)
    filename = f"{safe_title}_{date_str}.xlsx"
    # 使用 RFC 5987 编码以支持中文文件名
    encoded_filename = quote(filename)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}",
        },
    )


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
            task.completed_at = now_east8()
    
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

