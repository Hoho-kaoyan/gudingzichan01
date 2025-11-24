"""
统计信息路由
提供系统统计数据
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
from models import User, Asset, TransferRequest, ReturnRequest
from auth import get_current_user

router = APIRouter()


@router.get("/")
async def get_stats(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取系统统计数据"""
    # 用户总数
    total_users = db.query(func.count(User.id)).scalar()
    
    # 资产总数
    total_assets = db.query(func.count(Asset.id)).scalar()
    
    # 在用资产数
    in_use_assets = db.query(func.count(Asset.id)).filter(Asset.status == "在用").scalar()
    
    # 待审批的交接申请数
    pending_transfers = db.query(func.count(TransferRequest.id)).filter(
        TransferRequest.status == "pending"
    ).scalar()
    
    # 待审批的退回申请数
    pending_returns = db.query(func.count(ReturnRequest.id)).filter(
        ReturnRequest.status == "pending"
    ).scalar()
    
    return {
        "total_users": total_users or 0,
        "total_assets": total_assets or 0,
        "in_use_assets": in_use_assets or 0,
        "pending_approvals": (pending_transfers or 0) + (pending_returns or 0)
    }


统计信息路由
提供系统统计数据
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
from models import User, Asset, TransferRequest, ReturnRequest
from auth import get_current_user

router = APIRouter()


@router.get("/")
async def get_stats(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取系统统计数据"""
    # 用户总数
    total_users = db.query(func.count(User.id)).scalar()
    
    # 资产总数
    total_assets = db.query(func.count(Asset.id)).scalar()
    
    # 在用资产数
    in_use_assets = db.query(func.count(Asset.id)).filter(Asset.status == "在用").scalar()
    
    # 待审批的交接申请数
    pending_transfers = db.query(func.count(TransferRequest.id)).filter(
        TransferRequest.status == "pending"
    ).scalar()
    
    # 待审批的退回申请数
    pending_returns = db.query(func.count(ReturnRequest.id)).filter(
        ReturnRequest.status == "pending"
    ).scalar()
    
    return {
        "total_users": total_users or 0,
        "total_assets": total_assets or 0,
        "in_use_assets": in_use_assets or 0,
        "pending_approvals": (pending_transfers or 0) + (pending_returns or 0)
    }




