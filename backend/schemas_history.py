"""
资产流转记录相关的Pydantic模式
"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class AssetHistoryResponse(BaseModel):
    id: int
    asset_id: int
    action_type: str
    action_description: Optional[str] = None
    operator_id: Optional[int] = None
    approver_id: Optional[int] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    related_request_id: Optional[int] = None
    related_request_type: Optional[str] = None
    created_at: datetime
    operator: Optional[dict] = None
    approver: Optional[dict] = None
    
    class Config:
        from_attributes = True
