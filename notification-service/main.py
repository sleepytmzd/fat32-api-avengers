"""
Notification Service - Email, SMS, and push notification delivery
No database - stateless service ready for Kafka integration
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Header
from typing import Optional, Dict, List
import logging
from datetime import datetime
from pydantic import BaseModel, EmailStr
import asyncio
from prometheus_fastapi_instrumentator import Instrumentator
from kafka_consumer import KafkaHandler
from sqlalchemy.ext.asyncio import AsyncSession

# Database imports
from database import init_db, get_db, close_db
import crud
from models import NotificationChannel, NotificationStatus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Notification Service",
    description="Multi-channel notification delivery service",
    version="1.0.0"
)

Instrumentator().instrument(app).expose(app, endpoint="/metrics")

# Kafka handler
kafka_handler = KafkaHandler()

@app.on_event("startup")
async def startup():
    """Initialize service and Kafka"""
    logger.info("Initializing Notification Service...")
    
    # Initialize database
    await init_db()
    logger.info("Database initialized")
    
    await kafka_handler.start()
    
    # Start Kafka consumer in background
    asyncio.create_task(kafka_handler.consume_events())
    
    logger.info("Notification Service started successfully")
    logger.info("Kafka consumer running")

@app.on_event("shutdown")
async def shutdown():
    """Cleanup"""
    await kafka_handler.stop()
    await close_db()
    logger.info("Notification Service stopped")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "notification-service",
        "kafka_connected": kafka_handler.is_connected()
    }

# ============================================================================
# Helper Functions - Extract user context from gateway headers
# ============================================================================

def get_current_user_id(x_user_id: Optional[str] = Header(None)) -> Optional[str]:
    """Extract user ID from gateway header"""
    return x_user_id

def get_current_user_email(x_user_email: Optional[str] = Header(None)) -> Optional[str]:
    """Extract user email from gateway header"""
    return x_user_email

def get_current_user_role(x_user_role: Optional[str] = Header(None)) -> Optional[str]:
    """Extract user role from gateway header"""
    return x_user_role

def require_user(x_user_id: Optional[str] = Header(None)) -> str:
    """Require authenticated user"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    return x_user_id

# ============================================================================
# Models
# ============================================================================

class EmailNotification(BaseModel):
    """Email notification model"""
    to: EmailStr
    subject: str
    body: str
    html: Optional[str] = None
    user_id: Optional[str] = None  # Optional user ID for tracking

class SMSNotification(BaseModel):
    """SMS notification model"""
    to: str
    message: str
    user_id: Optional[str] = None  # Optional user ID for tracking

class PushNotification(BaseModel):
    """Push notification model"""
    user_id: str
    title: str
    body: str
    data: Optional[Dict] = None

# class OrderConfirmationData(BaseModel):
#     """Order confirmation notification data"""
#     user_email: EmailStr
#     order_id: str
#     total_amount: float
#     currency: str = "USD"

# class PaymentNotificationData(BaseModel):
#     """Payment notification data"""
#     user_email: EmailStr
#     payment_id: str
#     amount: float
#     status: str

# ============================================================================
# INTERNAL ENDPOINTS - For service-to-service communication
# ============================================================================

# @app.post("/internal/notifications/order-confirmation")
# async def send_order_confirmation(
#     data: OrderConfirmationData,
#     background_tasks: BackgroundTasks
# ):
#     """
#     Send order confirmation notification
#     Called by Order Service
#     """
#     notification_id = f"notif-{datetime.utcnow().timestamp()}"
    
#     # Add to background tasks (non-blocking)
#     background_tasks.add_task(
#         send_email_async,
#         to=data.user_email,
#         subject=f"Order Confirmation - {data.order_id}",
#         body=f"""
#         Thank you for your order!
        
#         Order ID: {data.order_id}
#         Total: {data.total_amount} {data.currency}
        
#         Your order has been confirmed and is being processed.
#         We'll send you another notification when your order ships.
        
#         Thank you for shopping with us!
#         """,
#         notification_id=notification_id,
#         notification_type="order_confirmation"
#     )
    
#     logger.info(f"Queued order confirmation notification for {data.user_email}")
    
#     return {
#         "success": True,
#         "notification_id": notification_id,
#         "message": "Notification queued for delivery"
#     }

# @app.post("/internal/notifications/payment-status")
# async def send_payment_notification(
#     data: PaymentNotificationData,
#     background_tasks: BackgroundTasks
# ):
#     """
#     Send payment status notification
#     Called by Payment Service
#     """
#     notification_id = f"notif-{datetime.utcnow().timestamp()}"
    
#     subject = f"Payment {data.status.title()} - {data.payment_id}"
    
#     if data.status == "completed":
#         body = f"""
#         Your payment has been processed successfully!
        
#         Payment ID: {data.payment_id}
#         Amount: {data.amount} USD
#         Status: {data.status}
        
#         Thank you for your payment.
#         """
#     elif data.status == "failed":
#         body = f"""
#         Payment Failed
        
#         Payment ID: {data.payment_id}
#         Amount: {data.amount} USD
#         Status: {data.status}
        
#         Please try again or contact support if the problem persists.
#         """
#     else:
#         body = f"""
#         Payment Update
        
#         Payment ID: {data.payment_id}
#         Amount: {data.amount} USD
#         Status: {data.status}
#         """
    
#     background_tasks.add_task(
#         send_email_async,
#         to=data.user_email,
#         subject=subject,
#         body=body,
#         notification_id=notification_id,
#         notification_type="payment_status"
#     )
    
#     logger.info(f"Queued payment notification for {data.user_email}")
    
#     return {
#         "success": True,
#         "notification_id": notification_id,
#         "message": "Notification queued for delivery"
#     }

# @app.post("/internal/notifications/order-shipped")
# async def send_order_shipped(
#     order_id: str,
#     user_email: EmailStr,
#     tracking_number: Optional[str] = None,
#     background_tasks: BackgroundTasks = None
# ):
#     """Send order shipped notification"""
#     notification_id = f"notif-{datetime.utcnow().timestamp()}"
    
#     body = f"""
#     Your order has been shipped!
    
#     Order ID: {order_id}
#     """
    
#     if tracking_number:
#         body += f"\nTracking Number: {tracking_number}"
    
#     body += "\n\nYour package is on its way!"
    
#     if background_tasks:
#         background_tasks.add_task(
#             send_email_async,
#             to=user_email,
#             subject=f"Order Shipped - {order_id}",
#             body=body,
#             notification_id=notification_id,
#             notification_type="order_shipped"
#         )
    
#     return {
#         "success": True,
#         "notification_id": notification_id,
#         "message": "Notification queued for delivery"
#     }

# ============================================================================
# Direct notification endpoints (for testing/admin use)
# ============================================================================

@app.post("/notifications/email")
async def send_email_endpoint(
    notification: EmailNotification,
    background_tasks: BackgroundTasks
):
    """Send email notification (direct)"""
    notification_id = f"notif-{datetime.utcnow().timestamp()}"
    
    background_tasks.add_task(
        send_email_async,
        to=notification.to,
        subject=notification.subject,
        body=notification.body,
        html=notification.html,
        notification_id=notification_id,
        notification_type="direct_email",
        user_id=notification.user_id
    )
    
    return {
        "success": True,
        "notification_id": notification_id,
        "message": "Email queued for delivery"
    }

@app.post("/notifications/sms")
async def send_sms_endpoint(
    notification: SMSNotification,
    background_tasks: BackgroundTasks
):
    """Send SMS notification (direct)"""
    notification_id = f"notif-{datetime.utcnow().timestamp()}"
    
    background_tasks.add_task(
        send_sms_async,
        to=notification.to,
        message=notification.message,
        notification_id=notification_id,
        user_id=notification.user_id
    )
    
    return {
        "success": True,
        "notification_id": notification_id,
        "message": "SMS queued for delivery"
    }

@app.post("/notifications/push")
async def send_push_endpoint(
    notification: PushNotification,
    background_tasks: BackgroundTasks
):
    """Send push notification (direct)"""
    notification_id = f"notif-{datetime.utcnow().timestamp()}"
    
    background_tasks.add_task(
        send_push_async,
        user_id=notification.user_id,
        title=notification.title,
        body=notification.body,
        data=notification.data,
        notification_id=notification_id
    )
    
    return {
        "success": True,
        "notification_id": notification_id,
        "message": "Push notification queued for delivery"
    }

# ============================================================================
# Notification delivery functions (async)
# These simulate actual notification delivery
# In production: integrate with SendGrid, Twilio, FCM, etc.
# ============================================================================

async def send_email_async(
    to: str,
    subject: str,
    body: str,
    html: Optional[str] = None,
    notification_id: str = None,
    notification_type: str = "email",
    user_id: str = None
):
    """Simulate email sending and save to database"""
    from database import AsyncSessionLocal
    
    async with AsyncSessionLocal() as db:
        try:
            # Create notification record first
            await crud.create_notification(
                db=db,
                notification_id=notification_id,
                user_id=user_id or "unknown",
                user_email=to,
                notification_type=notification_type,
                channel=NotificationChannel.EMAIL,
                subject=subject,
                body=body,
                html=html,
                status=NotificationStatus.PENDING
            )
            
            # Simulate network delay
            await asyncio.sleep(0.5)
            
            # In production: use SendGrid, AWS SES, etc.
            logger.info(f"📧 EMAIL SENT to {to}")
            logger.info(f"   Subject: {subject}")
            logger.info(f"   Body: {body[:100]}...")
            
            # Update status to sent
            await crud.update_notification_status(
                db=db,
                notification_id=notification_id,
                status=NotificationStatus.SENT
            )
            
            return True
        
        except Exception as e:
            logger.error(f"Failed to send email to {to}: {e}")
            
            # Update status to failed
            await crud.update_notification_status(
                db=db,
                notification_id=notification_id,
                status=NotificationStatus.FAILED,
                error_message=str(e)
            )
            return False

async def send_sms_async(
    to: str,
    message: str,
    notification_id: str = None,
    user_id: str = None
):
    """Simulate SMS sending and save to database"""
    from database import AsyncSessionLocal
    
    async with AsyncSessionLocal() as db:
        try:
            # Create notification record
            await crud.create_notification(
                db=db,
                notification_id=notification_id,
                user_id=user_id or "unknown",
                notification_type="sms",
                channel=NotificationChannel.SMS,
                body=message,
                status=NotificationStatus.PENDING
            )
            
            await asyncio.sleep(0.3)
            
            # In production: use Twilio, AWS SNS, etc.
            logger.info(f"📱 SMS SENT to {to}")
            logger.info(f"   Message: {message[:100]}...")
            
            # Update status to sent
            await crud.update_notification_status(
                db=db,
                notification_id=notification_id,
                status=NotificationStatus.SENT
            )
            
            return True
        
        except Exception as e:
            logger.error(f"Failed to send SMS to {to}: {e}")
            await crud.update_notification_status(
                db=db,
                notification_id=notification_id,
                status=NotificationStatus.FAILED,
                error_message=str(e)
            )
            return False

async def send_push_async(
    user_id: str,
    title: str,
    body: str,
    data: Optional[Dict] = None,
    notification_id: str = None
):
    """Simulate push notification sending and save to database"""
    from database import AsyncSessionLocal
    
    async with AsyncSessionLocal() as db:
        try:
            # Create notification record
            await crud.create_notification(
                db=db,
                notification_id=notification_id,
                user_id=user_id,
                notification_type="push",
                channel=NotificationChannel.PUSH,
                title=title,
                body=body,
                data=data,
                status=NotificationStatus.PENDING
            )
            
            await asyncio.sleep(0.2)
            
            # In production: use Firebase Cloud Messaging, APNs, etc.
            logger.info(f"🔔 PUSH NOTIFICATION SENT to user {user_id}")
            logger.info(f"   Title: {title}")
            logger.info(f"   Body: {body}")
            
            # Update status to sent
            await crud.update_notification_status(
                db=db,
                notification_id=notification_id,
                status=NotificationStatus.SENT
            )
            
            return True
        
        except Exception as e:
            logger.error(f"Failed to send push to user {user_id}: {e}")
            await crud.update_notification_status(
                db=db,
                notification_id=notification_id,
                status=NotificationStatus.FAILED,
                error_message=str(e)
            )
            return False

# ============================================================================
# User notification endpoints
# ============================================================================

@app.get("/notifications/my")
async def get_my_notifications(
    limit: int = 100,
    offset: int = 0,
    channel: Optional[str] = None,
    status: Optional[str] = None,
    user_id: str = Depends(require_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all notifications for the authenticated user"""
    channel_enum = NotificationChannel(channel) if channel else None
    status_enum = NotificationStatus(status) if status else None
    
    notifications = await crud.get_user_notifications(
        db=db,
        user_id=user_id,
        limit=limit,
        offset=offset,
        channel=channel_enum,
        status=status_enum
    )
    
    return {
        "user_id": user_id,
        "total": len(notifications),
        "notifications": [
            {
                "id": n.id,
                "type": n.notification_type,
                "channel": n.channel,
                "status": n.status,
                "title": n.title,
                "subject": n.subject,
                "body": n.body,
                "created_at": n.created_at.isoformat() if n.created_at else None,
                "sent_at": n.sent_at.isoformat() if n.sent_at else None,
                "read_at": n.read_at.isoformat() if n.read_at else None
            }
            for n in notifications
        ]
    }

@app.get("/notifications/unread")
async def get_my_unread_notifications(
    limit: int = 100,
    user_id: str = Depends(require_user),
    db: AsyncSession = Depends(get_db)
):
    """Get unread notifications for the authenticated user"""
    notifications = await crud.get_unread_notifications(db=db, user_id=user_id, limit=limit)
    count = await crud.get_unread_count(db=db, user_id=user_id)
    
    return {
        "user_id": user_id,
        "unread_count": count,
        "notifications": [
            {
                "id": n.id,
                "type": n.notification_type,
                "title": n.title,
                "body": n.body,
                "created_at": n.created_at.isoformat() if n.created_at else None
            }
            for n in notifications
        ]
    }

@app.post("/notifications/{notification_id}/read")
async def mark_notification_read_endpoint(
    notification_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Mark a notification as read"""
    notification = await crud.mark_notification_as_read(db=db, notification_id=notification_id)
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    return {
        "success": True,
        "notification_id": notification_id,
        "read_at": notification.read_at.isoformat() if notification.read_at else None
    }

@app.post("/notifications/read-all")
async def mark_all_my_notifications_read(
    user_id: str = Depends(require_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark all notifications as read for the authenticated user"""
    count = await crud.mark_all_as_read(db=db, user_id=user_id)
    
    return {
        "success": True,
        "user_id": user_id,
        "marked_read": count
    }

# ============================================================================
# Admin/Monitoring endpoints
# ============================================================================

@app.get("/notifications/log")
async def get_notification_log(
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """Get recent notification log (for monitoring)"""
    notifications = await crud.get_all_notifications(db, limit=limit, offset=offset)
    
    return {
        "total": len(notifications),
        "notifications": [
            {
                "id": n.id,
                "user_id": n.user_id,
                "type": n.notification_type,
                "channel": n.channel,
                "status": n.status,
                "created_at": n.created_at.isoformat() if n.created_at else None,
                "sent_at": n.sent_at.isoformat() if n.sent_at else None
            }
            for n in notifications
        ]
    }

@app.get("/notifications/stats")
async def get_notification_stats(
    user_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get notification statistics"""
    stats = await crud.get_notification_stats(db, user_id=user_id)
    
    # Calculate success rate
    sent = stats["by_status"].get(NotificationStatus.SENT, 0)
    total = stats["total"]
    success_rate = (sent / total * 100) if total > 0 else 0
    
    return {
        "total": total,
        "sent": sent,
        "failed": stats["by_status"].get(NotificationStatus.FAILED, 0),
        "pending": stats["by_status"].get(NotificationStatus.PENDING, 0),
        "success_rate": success_rate,
        "by_channel": stats["by_channel"],
        "by_status": stats["by_status"]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8005, reload=True)