"""
联动安全检查配置：全局默认检查类型 + 实物名称→检查类型映射
仅管理员可访问。
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models import SafetyCheckAutoConfig, SafetyCheckAssetTypeMapping, SafetyCheckType, User
from schemas import (
    SafetyCheckAutoConfigResponse,
    SafetyCheckAutoConfigUpdate,
    SafetyCheckAssetTypeMappingCreate,
    SafetyCheckAssetTypeMappingUpdate,
    SafetyCheckAssetTypeMappingResponse,
    SafetyCheckTypeResponse,
)
from auth import get_current_admin_user
import json

router = APIRouter()


def _check_type_to_response(ct: SafetyCheckType) -> SafetyCheckTypeResponse:
    if not ct:
        return None
    ct_dict = {
        "id": ct.id,
        "name": ct.name,
        "description": ct.description,
        "is_active": ct.is_active,
        "created_at": ct.created_at,
        "updated_at": ct.updated_at,
        "created_by_id": ct.created_by_id,
        "created_by": ct.created_by,
    }
    if ct.check_items:
        try:
            ct_dict["check_items"] = json.loads(ct.check_items)
        except Exception:
            ct_dict["check_items"] = []
    else:
        ct_dict["check_items"] = []
    return SafetyCheckTypeResponse(**ct_dict)


# ---------- 全局默认检查类型（单条） ----------
@router.get("", response_model=SafetyCheckAutoConfigResponse)
async def get_auto_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """获取联动安全检查全局配置（仅管理员）。无配置时返回默认结构。"""
    config = db.query(SafetyCheckAutoConfig).first()
    if not config:
        return SafetyCheckAutoConfigResponse(
            id=0,
            default_check_type_id=None,
            created_at=None,
            updated_at=None,
            default_check_type=None,
        )
    out = SafetyCheckAutoConfigResponse(
        id=config.id,
        default_check_type_id=config.default_check_type_id,
        created_at=config.created_at,
        updated_at=config.updated_at,
        default_check_type=_check_type_to_response(config.default_check_type) if config.default_check_type else None,
    )
    return out


@router.put("", response_model=SafetyCheckAutoConfigResponse)
async def update_auto_config(
    body: SafetyCheckAutoConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """创建或更新联动安全检查全局配置（仅管理员）。"""
    if body.default_check_type_id is not None:
        ct = db.query(SafetyCheckType).filter(
            SafetyCheckType.id == body.default_check_type_id,
            SafetyCheckType.is_active == True,
        ).first()
        if not ct:
            raise HTTPException(status_code=400, detail="检查类型不存在或已停用")
    config = db.query(SafetyCheckAutoConfig).first()
    if not config:
        config = SafetyCheckAutoConfig(default_check_type_id=body.default_check_type_id)
        db.add(config)
    else:
        config.default_check_type_id = body.default_check_type_id
    db.commit()
    db.refresh(config)
    return SafetyCheckAutoConfigResponse(
        id=config.id,
        default_check_type_id=config.default_check_type_id,
        created_at=config.created_at,
        updated_at=config.updated_at,
        default_check_type=_check_type_to_response(config.default_check_type) if config.default_check_type else None,
    )


# ---------- 实物名称→检查类型映射 ----------
@router.get("/asset-type-mappings", response_model=List[SafetyCheckAssetTypeMappingResponse])
async def list_asset_type_mappings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """获取实物名称→检查类型映射列表（仅管理员）。"""
    rows = db.query(SafetyCheckAssetTypeMapping).order_by(SafetyCheckAssetTypeMapping.asset_type).all()
    result = []
    for r in rows:
        result.append(SafetyCheckAssetTypeMappingResponse(
            id=r.id,
            asset_type=r.asset_type,
            check_type_id=r.check_type_id,
            created_at=r.created_at,
            check_type=_check_type_to_response(r.check_type) if r.check_type else None,
        ))
    return result


@router.post("/asset-type-mappings", response_model=SafetyCheckAssetTypeMappingResponse)
async def create_asset_type_mapping(
    body: SafetyCheckAssetTypeMappingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """新增实物名称→检查类型映射（仅管理员）。"""
    ct = db.query(SafetyCheckType).filter(
        SafetyCheckType.id == body.check_type_id,
        SafetyCheckType.is_active == True,
    ).first()
    if not ct:
        raise HTTPException(status_code=400, detail="检查类型不存在或已停用")
    existing = db.query(SafetyCheckAssetTypeMapping).filter(
        SafetyCheckAssetTypeMapping.asset_type == body.asset_type.strip()
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="该实物名称已存在映射")
    row = SafetyCheckAssetTypeMapping(
        asset_type=body.asset_type.strip(),
        check_type_id=body.check_type_id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return SafetyCheckAssetTypeMappingResponse(
        id=row.id,
        asset_type=row.asset_type,
        check_type_id=row.check_type_id,
        created_at=row.created_at,
        check_type=_check_type_to_response(row.check_type) if row.check_type else None,
    )


@router.put("/asset-type-mappings/{mapping_id}", response_model=SafetyCheckAssetTypeMappingResponse)
async def update_asset_type_mapping(
    mapping_id: int,
    body: SafetyCheckAssetTypeMappingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """按 id 更新实物名称→检查类型映射的 check_type_id（仅管理员）。"""
    ct = db.query(SafetyCheckType).filter(
        SafetyCheckType.id == body.check_type_id,
        SafetyCheckType.is_active == True,
    ).first()
    if not ct:
        raise HTTPException(status_code=400, detail="检查类型不存在或已停用")
    row = db.query(SafetyCheckAssetTypeMapping).filter(SafetyCheckAssetTypeMapping.id == mapping_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="映射不存在")
    row.check_type_id = body.check_type_id
    db.commit()
    db.refresh(row)
    return SafetyCheckAssetTypeMappingResponse(
        id=row.id,
        asset_type=row.asset_type,
        check_type_id=row.check_type_id,
        created_at=row.created_at,
        check_type=_check_type_to_response(row.check_type) if row.check_type else None,
    )


@router.delete("/asset-type-mappings/{mapping_id}")
async def delete_asset_type_mapping(
    mapping_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """删除实物名称→检查类型映射（仅管理员）。"""
    row = db.query(SafetyCheckAssetTypeMapping).filter(SafetyCheckAssetTypeMapping.id == mapping_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="映射不存在")
    db.delete(row)
    db.commit()
    return {"message": "已删除"}
