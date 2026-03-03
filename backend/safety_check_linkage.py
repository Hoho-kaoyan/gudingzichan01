"""
联动安全检查：按实物名称解析检查类型
供入库、交接、调拨、离职等场景在系统自动分配任务时使用。
"""
from typing import Optional
from sqlalchemy.orm import Session
from models import SafetyCheckAssetTypeMapping, SafetyCheckAutoConfig, SafetyCheckType, SafetyCheckTask
from logger import logger


def get_check_type_for_asset(db: Session, asset) -> Optional[int]:
    """
    根据资产的大类名称解析应使用的检查类型 ID。
    先查「资产大类名称→检查类型」映射，若无则用全局默认检查类型。
    若解析出的检查类型不存在或已停用，返回 None。

    :param db: 数据库会话
    :param asset: Asset 对象
    :return: 检查类型 id，无配置或无效时返回 None
    """
    if not asset or not asset.category:
        logger.warning("联动安全检查：未找到有效的资产大类信息，不创建任务")
        return None

    category_name = asset.category.name.strip()

    # 1) 查资产大类名称→检查类型映射
    mapping = db.query(SafetyCheckAssetTypeMapping).filter(
        SafetyCheckAssetTypeMapping.asset_type == category_name
    ).first()
    
    if mapping:
        check_type_id = mapping.check_type_id
    else:
        # 2) 用全局默认检查类型
        config = db.query(SafetyCheckAutoConfig).first()
        if not config or config.default_check_type_id is None:
            logger.warning("联动安全检查：未配置默认检查类型且资产大类 %s 无映射记录，不创建任务", category_name)
            return None
        check_type_id = config.default_check_type_id

    # 3) 校验检查类型存在且启用
    check_type = db.query(SafetyCheckType).filter(
        SafetyCheckType.id == check_type_id,
        SafetyCheckType.is_active == True
    ).first()
    if not check_type:
        logger.warning("联动安全检查：检查类型 id=%s 不存在或已停用，不创建任务", check_type_id)
        return None

    return check_type_id

def create_system_allocated_task(db: Session, asset_id: int, assigned_user_id: int, source: str, title_prefix: str = "") -> Optional[SafetyCheckTask]:
    """
    共用服务：系统按场景自动分配创建一条安全检查任务，并将对应资产分配给对应人员进行检查。
    如果解析不到匹配的安全检查类型方案，则跳过创建并记录日志。
    """
    from models import Asset, SafetyCheckTask, TaskAsset
    from datetime import datetime, timezone

    # 1) 获取资产存在性及查名字
    asset = db.query(Asset).filter(Asset.id == asset_id, Asset.deleted_at == None).first()
    if not asset:
        logger.warning(f"未能找到 ID 为 {asset_id} 的有效资产对象，无法分发联动任务。")
        return None

    # 2) 使用资产大类找配置好的检查类型
    # 注意此时的 asset 需要有关联的 category 对象
    check_type_id = get_check_type_for_asset(db, asset)
    if not check_type_id:
        # 当解析不出的时候（或类型被停用时候），日志已在内层被打印，静默不创建。
        return None

    # 3) 准备创建主任务 `safety_check_tasks`
    # 生成随机特征的任务编号（格式范例：TASK-LINKAGE-时间戳毫秒）
    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")[:17]
    task_number = f"TASK-LINKAGE-{timestamp_str}"
    
    # 构建 title（默认自带前缀和来源提醒，便于人员分辨）
    source_msg_map = {
        "inbound": "入库联动",
        "transfer": "交接前核验",
        "reallocation": "调拨前核验",
        "resignation": "离职退库/交接前核验"
    }
    action_desc = source_msg_map.get(source, "联动检测")
    final_title = f"[{action_desc}] 对 {asset.name} ({asset.asset_number}) 的安全检查任务"
    if title_prefix:
        final_title = f"{title_prefix} {final_title}"

    # 作为系统自动触发的建单人，我们在此取 `assigned_user_id` 自身或默认一个系统管理员账号，这里暂记为 1 (假设 admin 存在)。或者为了日志更好排查标记为 `assigned_user_id` 本人名下发起
    # 文档写定：“created_by可用系统用户或当前操作人id”，此处使用分配人本人或写死管理员ID(如1)。取当前负责人最稳妥
    new_task = SafetyCheckTask(
        task_number=task_number,
        check_type_id=check_type_id,
        title=final_title,
        description=f"系统在【{action_desc}】环节自动为您分配并挂载的待完成检测任务。请确认符合数据安全标准。",
        deadline=None, # 不设置明确的 overdue 自动失效，交由流程总控拦截
        status="pending",
        source=source,
        created_by_id=assigned_user_id 
    )
    db.add(new_task)
    db.flush() # flush以便获取ID

    # 4) 生成 `task_assets` 分配记录绑定到人
    new_task_asset = TaskAsset(
        task_id=new_task.id,
        asset_id=asset.id,
        assigned_user_id=assigned_user_id,
        status="pending"
    )
    db.add(new_task_asset)
    
    # 5) 提交事务
    db.commit()
    db.refresh(new_task)
    logger.info(f"联动安检：基于动作 [{source}] 成功为资产 [{asset.name} / {asset.asset_number}] 向用户 [{assigned_user_id}] 派发任务 #{new_task.task_number}。")
    return new_task
