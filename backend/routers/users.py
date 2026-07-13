"""
用户管理路由
包括用户的增删改查、批量导入等
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional
from database import get_db
from models import User, Asset, SafetyCheckTask, TaskAsset
from schemas import UserCreate, UserUpdate, UserResponse, ImportResponse, PasswordChange, ImportConflictDetail, ImportConflictDiff, ImportResolveRequest
from auth import get_current_user, get_current_admin_user, get_password_hash, verify_password
import pandas as pd
import io
from excel_io import cell_to_str, row_to_error_dict
from utils_time import now_east8
from safety_check_linkage import get_check_type_for_asset
from logger import logger
import random
from schemas import ImportErrorDetail


def _build_user_import_conflict_diffs(existing_user: User, new_data: dict) -> List[ImportConflictDiff]:
    """比对数据库现有用户与导入数据的差异"""
    diffs = []
    # 映射表：(字段名, 中文显示名)
    field_map = [
        ("real_name", "姓名"),
        ("group", "组别"),
        ("role", "角色"),
        ("status", "状态"),
    ]
    
    role_map = {
        'admin': '管理员',
        'leader': '组长',
        'user': '普通用户'
    }

    for field, label in field_map:
        db_val = getattr(existing_user, field) or ""
        import_val = new_data.get(field) or ""
        
        # 处理角色显示的特殊变换
        db_display = role_map.get(db_val, db_val) if field == "role" else db_val
        import_display = role_map.get(import_val, import_val) if field == "role" else import_val
        
        if str(db_val).strip() != str(import_val).strip():
            diffs.append(ImportConflictDiff(
                field_label=label,
                db_value=str(db_display),
                import_value=str(import_display)
            ))
    return diffs


def _create_resignation_safety_tasks(db: Session, user: User, current_user_id: int) -> None:
    """
    离职场景：为该用户名下全部资产生成安全检查任务（按类型聚合），不提交事务。
    使用 get_check_type_for_asset 解析类型（含映射+默认类型+is_active 校验），
    无法解析的资产跳过并打日志。供 mark_user_resignation 与 update_user 共用。
    """
    assets = db.query(Asset).filter(
        Asset.user_id == user.id,
        Asset.deleted_at.is_(None)
    ).all()
    if not assets:
        return

    tasks_to_create = {}  # type_id -> [asset_id, ...]
    for asset in assets:
        type_id = get_check_type_for_asset(db, asset)
        if type_id is None:
            logger.warning(
                "离职安检：资产 %s (%s) 未匹配到有效检查类型，已跳过",
                getattr(asset, "name", ""),
                getattr(asset, "asset_number", asset.id),
            )
            continue
        if type_id not in tasks_to_create:
            tasks_to_create[type_id] = []
        tasks_to_create[type_id].append(asset.id)

    ts_str = now_east8().strftime("%Y%m%d%H%M%S")
    for type_id, asset_ids in tasks_to_create.items():
        task_number = f"SC-RESIGN-{ts_str}-{user.id}-{type_id}-{random.randint(100, 999)}"
        task = SafetyCheckTask(
            task_number=task_number,
            check_type_id=type_id,
            title=f"离职安全检查 - {user.real_name}",
            description=f"用户 {user.real_name} 离职触发的自动安全检查任务",
            status="pending",
            source="resignation",
            created_by_id=current_user_id,
        )
        db.add(task)
        db.flush()
        for aid in asset_ids:
            ta = TaskAsset(
                task_id=task.id,
                asset_id=aid,
                assigned_user_id=user.id,
                status="pending",
            )
            db.add(ta)


router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """获取当前登录用户信息"""
    return UserResponse.model_validate(current_user)


@router.put("/me/password")
async def change_my_password(
    body: PasswordChange,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """当前用户修改自己的密码"""
    if not verify_password(body.old_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="原密码错误")
    current_user.password_hash = get_password_hash(body.new_password)
    current_user.must_change_password = False
    db.commit()
    return {"message": "密码修改成功"}


@router.get("/", response_model=List[UserResponse])
async def get_users(
    skip: int = 0,
    limit: int = 500,
    search: Optional[str] = Query(None, description="搜索关键词，支持模糊搜索所有字段"),
    role: Optional[str] = Query(None, description="按角色筛选"),
    status: Optional[str] = Query(None, description="按状态筛选"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取用户列表（所有已登录用户可访问，用于选择转入用户等场景），支持搜索；不含已逻辑删除用户"""
    query = db.query(User).filter(User.deleted_at.is_(None))
    
    # 支持模糊搜索所有字段
    if search:
        query = query.filter(
            or_(
                User.ehr_number.contains(search),
                User.real_name.contains(search),
                User.group.contains(search)
            )
        )
    
    # 按角色筛选
    if role:
        query = query.filter(User.role == role)
    
    # 按状态筛选
    if status:
        query = query.filter(User.status == status)
    
    users = query.offset(skip).limit(limit).all()
    return [UserResponse.model_validate(user) for user in users]


@router.get("/groups", response_model=List[str])
async def get_all_groups(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取所有现有的组别名称（用于前端下拉选择）"""
    groups = db.query(User.group).filter(
        User.group.isnot(None), 
        User.group != "",
        User.deleted_at.is_(None)
    ).distinct().all()
    # groups 返回的是列表的元组，如 [('研发',), ('行政',)]，需要展平
    return sorted([g[0] for g in groups if g[0]])


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取指定用户信息"""
    user = db.query(User).filter(User.id == user_id, User.deleted_at.is_(None)).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return UserResponse.model_validate(user)


@router.post("/", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """创建新用户（仅管理员）"""
    # 检查EHR号是否已存在（未删除用户）
    existing_user = db.query(User).filter(
        User.ehr_number == user_data.ehr_number,
        User.deleted_at.is_(None)
    ).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="EHR号已存在")
    
    # 创建新用户
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        ehr_number=user_data.ehr_number,
        real_name=user_data.real_name,
        group=user_data.group,
        role=user_data.role,
        status=user_data.status if hasattr(user_data, 'status') and user_data.status else "在岗",
        password_hash=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return UserResponse.model_validate(db_user)


@router.put("/{user_id}/mark-resignation", response_model=UserResponse)
async def mark_user_resignation(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """标记用户离职，并根据资产配置自动触发安全检查任务（仅管理员）"""
    user = db.query(User).filter(User.id == user_id, User.deleted_at.is_(None)).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    if user.status == "离职":
        raise HTTPException(status_code=400, detail="该用户已经是离职状态")

    if user.role == "admin":
        raise HTTPException(status_code=400, detail="不能标记管理员为离职")

    # 【新增：强级拦截】离职前检查是否还负责他人的安检执行工作
    is_executor_for_others = db.query(Asset).filter(
        Asset.safety_check_executor_id == user_id,
        Asset.deleted_at.is_(None)
    ).first()
    
    if is_executor_for_others:
        # 为了输出更准确的提示，可以只扫一眼计数
        count = db.query(Asset).filter(
            Asset.safety_check_executor_id == user_id,
            Asset.deleted_at.is_(None)
        ).count()
        raise HTTPException(
            status_code=400, 
            detail=f"该员工目前仍担任 {count} 件资产的检查执行人，请先将这些资产的安检职责移交他人，方可办理离职！"
        )

    _create_resignation_safety_tasks(db, user, current_user.id)
    user.status = "离职"
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """更新用户信息（仅管理员）"""
    user = db.query(User).filter(User.id == user_id, User.deleted_at.is_(None)).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 记录旧状态
    old_status = user.status
    
    # 更新字段
    if user_data.real_name is not None:
        user.real_name = user_data.real_name
    if user_data.group is not None:
        user.group = user_data.group
    if user_data.role is not None:
        user.role = user_data.role
    if user_data.status is not None:
        user.status = user_data.status
    if user_data.password is not None:
        user.password_hash = get_password_hash(user_data.password)
    
    if old_status != "离职" and user.status == "离职":
        # 【新增：强级拦截】离职前检查是否还负责他人的安检执行工作 (与 mark_user_resignation 同步)
        is_executor_for_others = db.query(Asset).filter(
            Asset.safety_check_executor_id == user_id,
            Asset.deleted_at.is_(None)
        ).first()
        
        if is_executor_for_others:
            count = db.query(Asset).filter(
                Asset.safety_check_executor_id == user_id,
                Asset.deleted_at.is_(None)
            ).count()
            raise HTTPException(
                status_code=400, 
                detail=f"该员工目前仍担任 {count} 件资产的检查执行人，请先将这些资产的安检职责移交他人，方可将其状态更改为离职！"
            )
            
        _create_resignation_safety_tasks(db, user, current_user.id)

    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """删除用户（仅管理员，软删除）"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.deleted_at is not None:
        raise HTTPException(status_code=400, detail="用户已被删除")
    
    # 禁止管理员删除自己
    if current_user.id == user_id:
        raise HTTPException(status_code=400, detail="不能删除自己的账号")
        
    # 【新增：拦截验证】检查该员工名下是否还有绑定的有效资产
    has_assets = db.query(Asset).filter(
        Asset.user_id == user_id, 
        Asset.deleted_at.is_(None),
        Asset.status != "已报废" # (如果是报废并且想删人，业务上可能要求资产也要解绑，简单起见只要是未删除的资产有绑定就拦截)
    ).first()
    if has_assets:
        raise HTTPException(status_code=400, detail="该用户名下存在资产不可删除")
        
    # 【新增：拦截验证】检查该员工是否被登记为其他资产的检查执行人
    is_executor_for_assets = db.query(Asset).filter(
        Asset.safety_check_executor_id == user_id,
        Asset.deleted_at.is_(None)
    ).first()
    if is_executor_for_assets:
        raise HTTPException(status_code=400, detail="该用户已被登记为其他资产的检查执行人，不可删除")
    
    user.deleted_at = now_east8()
    user.deleted_by_id = current_user.id
    db.commit()
    return {"message": "用户已删除"}




@router.post("/import", response_model=ImportResponse)
async def import_users(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    批量导入用户（仅管理员）
    Excel格式要求：
    - 列名：EHR号、姓名、组别、角色（可选，默认为user）、密码（可选，默认为123456）
    """
    try:
        # 读取Excel文件
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents))
        
        # 验证必需的列
        required_columns = ['EHR号', '姓名', '组别']
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
        conflict_details = []
        
        for index, row in df.iterrows():
            row_number = index + 2  # Excel行号（从2开始，第1行是表头）
            row_data = row.to_dict()  # 保存原始行数据
            
            try:
                # 单元格先转字符串（空/NaN→''，数字浮点去 .0），再当字符串用
                ehr_number = cell_to_str(row.get('EHR号', ''))
                real_name = cell_to_str(row.get('姓名', ''))
                group = cell_to_str(row.get('组别', ''))
                role = cell_to_str(row.get('角色', '')) or 'user'
                status = cell_to_str(row.get('状态', '')) or '在岗'
                password = cell_to_str(row.get('密码', '')) or 'Aa@1234567'
                
                # 状态合法性校验
                valid_statuses = {"在岗", "离职", "长期出差", "借调", "产假"}
                if status and status not in valid_statuses:
                    raise ValueError(f"状态 '{status}' 不合法，可选范围：{'/'.join(sorted(list(valid_statuses)))}")

                if not ehr_number or not real_name or not group:
                    raise ValueError("EHR号、姓名、组别均不能为空")
                
                # 验证EHR号
                if len(ehr_number) != 7 or not ehr_number.isdigit():
                    error_count += 1
                    error_msg = "EHR号格式错误（必须为7位数字）"
                    errors.append(f"第{row_number}行：{error_msg}")
                    error_details.append({
                        "row_number": row_number,
                        "error_message": error_msg,
                        "row_data": row_to_error_dict(row_data)
                    })
                    continue
                
                # 按EHR号查库（含已逻辑删除）：未删除则比对冲突，已删除则恢复并更新
                existing_user = db.query(User).filter(User.ehr_number == ehr_number).first()
                if existing_user and existing_user.deleted_at is None:
                    parsed_data = {
                        "real_name": real_name,
                        "group": group,
                        "role": role,
                        "status": status,
                        "password": password # 虽然不比对，但解决冲突覆盖时可能用到
                    }
                    diffs = _build_user_import_conflict_diffs(existing_user, parsed_data)
                    if not diffs:
                        skip_count += 1
                        continue
                    
                    conflict_count += 1
                    conflict_details.append(ImportConflictDetail(
                        row_number=row_number,
                        asset_number=ehr_number, # 这里借用字段存放 EHR 号
                        asset_id=existing_user.id, # 这里借用字段存放 User ID
                        diffs=diffs,
                        row_data=row_to_error_dict(row_data)
                    ))
                    continue
                
                if existing_user and existing_user.deleted_at is not None:
                    # 存在且已逻辑删除：恢复并用本行 Excel 更新
                    existing_user.deleted_at = None
                    existing_user.deleted_by_id = None
                    existing_user.real_name = real_name
                    existing_user.group = group
                    existing_user.role = role
                    existing_user.status = status
                    existing_user.password_hash = get_password_hash(password)
                    success_count += 1
                    continue
                
                # 不存在：创建用户
                hashed_password = get_password_hash(password)
                db_user = User(
                    ehr_number=ehr_number,
                    real_name=real_name,
                    group=group,
                    role=role,
                    status=status,
                    password_hash=hashed_password,
                    must_change_password=True
                )
                db.add(db_user)
                success_count += 1
                
            except Exception as e:
                error_count += 1
                error_msg = str(e)
                errors.append(f"第{row_number}行：{error_msg}")
                error_details.append({
                    "row_number": row_number,
                    "error_message": error_msg,
                    "row_data": row_to_error_dict(row_data)
                })
        
        db.commit()
        
        # 限制返回的错误数量
        max_errors = 100
        limited_errors = errors[:max_errors]
        limited_error_details = error_details[:max_errors]
        
        return ImportResponse(
            success_count=success_count,
            error_count=error_count,
            skip_count=skip_count,
            errors=limited_errors,
            error_details=limited_error_details,
            conflict_count=conflict_count,
            conflict_details=conflict_details[:100]
        )
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"导入失败：{str(e)}")


@router.post("/import-resolve")
async def resolve_user_import_conflicts(
    body: ImportResolveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    解决用户导入冲突：选择「覆盖」则更新用户信息，选择「保持」则忽略。
    """
    overwrite_count = 0
    errors_resolve = []
    
    for d in body.decisions:
        user = db.query(User).filter(User.id == d.asset_id, User.deleted_at.is_(None)).first()
        if not user:
            errors_resolve.append(f"用户ID {d.asset_id} 不存在或已删除，已跳过")
            continue
        
        if d.action == "keep":
            continue
            
        if d.action != "overwrite" or not d.row_data:
            errors_resolve.append(f"用户 {user.ehr_number}：覆盖操作需要提供行数据")
            continue
            
        try:
            # 解析 row_data
            row = d.row_data
            user.real_name = cell_to_str(row.get('姓名', user.real_name))
            user.group = cell_to_str(row.get('组别', user.group))
            user.role = cell_to_str(row.get('角色', user.role))
            user.status = cell_to_str(row.get('状态', user.status))
            
            pwd = cell_to_str(row.get('密码', ''))
            if pwd and pwd != '123456': # 如果提供了非默认密码，则更新
                user.password_hash = get_password_hash(pwd)
            
            overwrite_count += 1
        except Exception as e:
            errors_resolve.append(f"更新用户 {user.ehr_number} 失败：{str(e)}")
            
    db.commit()
    return {
        "message": f"已处理 {len(body.decisions)} 条冲突，其中覆盖更新 {overwrite_count} 条",
        "overwrite_count": overwrite_count,
        "errors": errors_resolve
    }
