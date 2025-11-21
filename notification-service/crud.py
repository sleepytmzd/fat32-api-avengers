"""
CRUD operations for Notification Service
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from sqlalchemy.orm import selectinload
from models import Notification, NotificationStatus, NotificationChannel
from datetime import datetime
from typing import List, Optional, Dict
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# Create operations
# ============================================================================

async def create_notification(
    db: AsyncSession,
    notification_id: str,
    user_id: str,
    notification_type: str,
    channel: NotificationChannel,
    body: str,
    user_email: Optional[str] = None,
    title: Optional[str] = None,
    subject: Optional[str] = None,
    html: Optional[str] = None,
    data: Optional[Dict] = None,
    status: NotificationStatus = NotificationStatus.PENDING
) -> Notification:
    """Create a new notification record"""
    notification = Notification(
        id=notification_id,
        user_id=user_id,
        user_email=user_email,
        notification_type=notification_type,
        channel=channel,
        status=status,
        title=title,
        subject=subject,
        body=body,
        html=html,
        data=data,
        created_at=datetime.utcnow()
    )
    
    db.add(notification)
    await db.commit()
    await db.refresh(notification)
    
    logger.info(f"Created notification {notification_id} for user {user_id}")
    return notification

# ============================================================================
# Read operations
# ============================================================================

async def get_notification_by_id(
    db: AsyncSession,
    notification_id: str
) -> Optional[Notification]:
    """Get notification by ID"""
    result = await db.execute(
        select(Notification).where(Notification.id == notification_id)
    )
    return result.scalar_one_or_none()

async def get_user_notifications(
    db: AsyncSession,
    user_id: str,
    limit: int = 100,
    offset: int = 0,
    channel: Optional[NotificationChannel] = None,
    status: Optional[NotificationStatus] = None
) -> List[Notification]:
    """Get notifications for a specific user"""
    query = select(Notification).where(Notification.user_id == user_id)
    
    if channel:
        query = query.where(Notification.channel == channel)
    
    if status:
        query = query.where(Notification.status == status)
    
    query = query.order_by(Notification.created_at.desc()).limit(limit).offset(offset)
    
    result = await db.execute(query)
    return result.scalars().all()

async def get_unread_notifications(
    db: AsyncSession,
    user_id: str,
    limit: int = 100
) -> List[Notification]:
    """Get unread notifications for a user"""
    query = select(Notification).where(
        Notification.user_id == user_id,
        Notification.read_at.is_(None),
        Notification.channel == NotificationChannel.IN_APP
    ).order_by(Notification.created_at.desc()).limit(limit)
    
    result = await db.execute(query)
    return result.scalars().all()

async def get_all_notifications(
    db: AsyncSession,
    limit: int = 100,
    offset: int = 0
) -> List[Notification]:
    """Get all notifications (for admin/monitoring)"""
    query = select(Notification).order_by(
        Notification.created_at.desc()
    ).limit(limit).offset(offset)
    
    result = await db.execute(query)
    return result.scalars().all()

# ============================================================================
# Update operations
# ============================================================================

async def update_notification_status(
    db: AsyncSession,
    notification_id: str,
    status: NotificationStatus,
    error_message: Optional[str] = None
) -> Optional[Notification]:
    """Update notification status"""
    notification = await get_notification_by_id(db, notification_id)
    
    if not notification:
        return None
    
    notification.status = status
    
    if status == NotificationStatus.SENT:
        notification.sent_at = datetime.utcnow()
    
    if error_message:
        notification.error_message = error_message
    
    if status == NotificationStatus.RETRY:
        notification.retry_count = str(int(notification.retry_count) + 1)
    
    await db.commit()
    await db.refresh(notification)
    
    logger.info(f"Updated notification {notification_id} status to {status}")
    return notification

async def mark_notification_as_read(
    db: AsyncSession,
    notification_id: str
) -> Optional[Notification]:
    """Mark a notification as read"""
    notification = await get_notification_by_id(db, notification_id)
    
    if not notification:
        return None
    
    notification.read_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(notification)
    
    logger.info(f"Marked notification {notification_id} as read")
    return notification

async def mark_all_as_read(
    db: AsyncSession,
    user_id: str
) -> int:
    """Mark all notifications as read for a user"""
    stmt = (
        update(Notification)
        .where(
            Notification.user_id == user_id,
            Notification.read_at.is_(None)
        )
        .values(read_at=datetime.utcnow())
    )
    
    result = await db.execute(stmt)
    await db.commit()
    
    count = result.rowcount
    logger.info(f"Marked {count} notifications as read for user {user_id}")
    return count

# ============================================================================
# Statistics operations
# ============================================================================

async def get_notification_stats(
    db: AsyncSession,
    user_id: Optional[str] = None
) -> Dict:
    """Get notification statistics"""
    query = select(
        func.count(Notification.id).label("total"),
        Notification.status,
        Notification.channel
    )
    
    if user_id:
        query = query.where(Notification.user_id == user_id)
    
    query = query.group_by(Notification.status, Notification.channel)
    
    result = await db.execute(query)
    rows = result.all()
    
    stats = {
        "total": 0,
        "by_status": {},
        "by_channel": {}
    }
    
    for row in rows:
        count = row.total
        status = row.status
        channel = row.channel
        
        stats["total"] += count
        stats["by_status"][status] = stats["by_status"].get(status, 0) + count
        stats["by_channel"][channel] = stats["by_channel"].get(channel, 0) + count
    
    return stats

async def get_unread_count(
    db: AsyncSession,
    user_id: str
) -> int:
    """Get count of unread notifications for a user"""
    query = select(func.count(Notification.id)).where(
        Notification.user_id == user_id,
        Notification.read_at.is_(None),
        Notification.channel == NotificationChannel.IN_APP
    )
    
    result = await db.execute(query)
    return result.scalar()
