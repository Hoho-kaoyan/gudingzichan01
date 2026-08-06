"""
系统通知路由（v5.1 新增）
用户获取自己的未读/已读通知，标记已读
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from database import get_db
from models import Notification, User
from auth import get_current_user
from utils_time import datetime_to_east8_iso, now_utc_naive

router = APIRouter()


class NotificationResponse(BaseModel):
    id: int
    type: str
    title: str
    content: str
    related_request_type: Optional[str] = None
    related_request_id: Optional[int] = None
    is_read: bool
    created_at: Optional[str] = None
    read_at: Optional[str] = None

    class Config:
        from_attributes = True


def _to_resp(n: Notification) -> NotificationResponse:
    return NotificationResponse(
        id=n.id,
        type=n.type,
        title=n.title,
        content=n.content,
        related_request_type=n.related_request_type,
        related_request_id=n.related_request_id,
        is_read=n.is_read,
        created_at=datetime_to_east8_iso(n.created_at),
        read_at=datetime_to_east8_iso(n.read_at),
    )


@router.get("/", response_model=List[NotificationResponse])
async def list_notifications(
    unread: bool = Query(False, description="只返回未读"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取当前用户的通知列表（最新在前）"""
    q = db.query(Notification).filter(Notification.user_id == current_user.id)
    if unread:
        q = q.filter(Notification.is_read == False)  # noqa: E712
    items = q.order_by(Notification.created_at.desc()).limit(limit).all()
    return [_to_resp(n) for n in items]


@router.get("/unread-count")
async def unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取未读通知数（用于侧边栏红点）"""
    cnt = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False,  # noqa: E712
    ).count()
    return {"unread_count": cnt}


@router.put("/{notification_id}/read", response_model=NotificationResponse)
async def mark_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """标记单条通知为已读"""
    n = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id,
    ).first()
    if not n:
        raise HTTPException(status_code=404, detail="通知不存在")
    if not n.is_read:
        n.is_read = True
        n.read_at = now_utc_naive()
        db.commit()
        db.refresh(n)
    return _to_resp(n)


@router.put("/read-all")
async def mark_all_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """标记当前用户所有未读通知为已读"""
    cnt = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False,  # noqa: E712
    ).update({Notification.is_read: True, Notification.read_at: now_utc_naive()}, synchronize_session=False)
    db.commit()
    return {"message": f"已标记 {cnt} 条通知为已读"}


# 工具函数：其他路由调用以写入通知
def create_notification(
    db: Session,
    user_id: int,
    type_: str,
    title: str,
    content: str,
    related_request_type: Optional[str] = None,
    related_request_id: Optional[int] = None,
) -> Notification:
    """写入一条系统通知（v5.1 新增）
    失败不抛异常（通知失败不应阻塞主业务）
    """
    try:
        n = Notification(
            user_id=user_id,
            type=type_,
            title=title,
            content=content,
            related_request_type=related_request_type,
            related_request_id=related_request_id,
            is_read=False,
        )
        db.add(n)
        db.flush()
        return n
    except Exception:
        from logger import logger
        logger.error(f"写入通知失败: user_id={user_id} type={type_}", exc_info=True)
        return None