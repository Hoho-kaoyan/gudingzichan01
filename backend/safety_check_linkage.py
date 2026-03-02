"""
联动安全检查：按实物名称解析检查类型
供入库、交接、调拨、离职等场景在系统自动分配任务时使用。
"""
from typing import Optional
from sqlalchemy.orm import Session
from models import SafetyCheckAssetTypeMapping, SafetyCheckAutoConfig, SafetyCheckType
from logger import logger


def get_check_type_for_asset_name(db: Session, asset_name: str) -> Optional[int]:
    """
    根据资产实物名称解析应使用的检查类型 ID。
    先查「实物名称→检查类型」映射，若无则用全局默认检查类型。
    若解析出的检查类型不存在或已停用，返回 None。

    :param db: 数据库会话
    :param asset_name: 实物名称（assets.name）
    :return: 检查类型 id，无配置或无效时返回 None
    """
    if asset_name is None or not asset_name.strip():
        logger.warning("联动安全检查：实物名称为空，不创建任务")
        return None

    asset_name = asset_name.strip()

    # 1) 查实物名称→检查类型映射
    mapping = db.query(SafetyCheckAssetTypeMapping).filter(
        SafetyCheckAssetTypeMapping.asset_type == asset_name
    ).first()
    if mapping:
        check_type_id = mapping.check_type_id
    else:
        # 2) 用全局默认检查类型
        config = db.query(SafetyCheckAutoConfig).first()
        if not config or config.default_check_type_id is None:
            logger.warning("联动安全检查：未配置默认检查类型且实物名称 %s 无映射，不创建任务", asset_name)
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
