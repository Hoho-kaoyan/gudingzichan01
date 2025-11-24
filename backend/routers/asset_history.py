"""
资产流转记录路由
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
import json
from database import get_db
from models import AssetHistory, Asset, User
from schemas_history import AssetHistoryResponse
from auth import get_current_user

router = APIRouter()


def create_history_record(
    db: Session,
    asset_id: int,
    action_type: str,
    action_description: Optional[str] = None,
    operator_id: Optional[int] = None,
    approver_id: Optional[int] = None,
    old_value: Optional[dict] = None,
    new_value: Optional[dict] = None,
    related_request_id: Optional[int] = None,
    related_request_type: Optional[str] = None
):
    """创建资产流转记录"""
    history = AssetHistory(
        asset_id=asset_id,
        action_type=action_type,
        action_description=action_description,
        operator_id=operator_id,
        approver_id=approver_id,
        old_value=json.dumps(old_value, ensure_ascii=False) if old_value else None,
        new_value=json.dumps(new_value, ensure_ascii=False) if new_value else None,
        related_request_id=related_request_id,
        related_request_type=related_request_type
    )
    db.add(history)
    db.flush()
    return history


@router.get("/asset/{asset_id}", response_model=List[AssetHistoryResponse])
async def get_asset_history(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取指定资产的流转记录"""
    # 检查资产是否存在
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="资产不存在")
    
    # 获取流转记录
    history = db.query(AssetHistory).options(
        joinedload(AssetHistory.operator),
        joinedload(AssetHistory.approver)
    ).filter(AssetHistory.asset_id == asset_id).order_by(AssetHistory.created_at.desc()).all()
    
    # 转换为响应格式
    result = []
    for item in history:
        item_dict = {
            "id": item.id,
            "asset_id": item.asset_id,
            "action_type": item.action_type,
            "action_description": item.action_description,
            "operator_id": item.operator_id,
            "approver_id": item.approver_id,
            "old_value": item.old_value,
            "new_value": item.new_value,
            "related_request_id": item.related_request_id,
            "related_request_type": item.related_request_type,
            "created_at": item.created_at,
            "operator": {
                "id": item.operator.id,
                "real_name": item.operator.real_name,
                "ehr_number": item.operator.ehr_number
            } if item.operator else None,
            "approver": {
                "id": item.approver.id,
                "real_name": item.approver.real_name,
                "ehr_number": item.approver.ehr_number
            } if item.approver else None
        }
        result.append(item_dict)
    
    return result
