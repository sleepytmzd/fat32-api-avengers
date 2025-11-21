"""
Database models for Notification Service
"""
from sqlalchemy import Column, String, DateTime, Text, JSON, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import enum

Base = declarative_base()

class NotificationStatus(str, enum.Enum):
    """Notification delivery status"""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    RETRY = "retry"

class NotificationChannel(str, enum.Enum):
    """Notification delivery channel"""
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    IN_APP = "in_app"

class Notification(Base):
    """User notification model"""
    __tablename__ = "notifications"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    user_email = Column(String, nullable=True)  # For email notifications
    
    # Notification details
    notification_type = Column(String, nullable=False)  # e.g., "order_confirmation", "payment_status"
    channel = Column(SQLEnum(NotificationChannel), nullable=False)
    status = Column(SQLEnum(NotificationStatus), default=NotificationStatus.PENDING, nullable=False)
    
    # Content
    title = Column(String, nullable=True)
    subject = Column(String, nullable=True)  # For emails
    body = Column(Text, nullable=False)
    html = Column(Text, nullable=True)  # For HTML emails
    
    # Metadata
    data = Column(JSON, nullable=True)  # Additional structured data
    error_message = Column(Text, nullable=True)  # Error details if failed
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    sent_at = Column(DateTime, nullable=True)
    read_at = Column(DateTime, nullable=True)  # For in-app notifications
    
    # Retry tracking
    retry_count = Column(String, default="0", nullable=False)
    
    def __repr__(self):
        return f"<Notification(id={self.id}, user_id={self.user_id}, type={self.notification_type}, status={self.status})>"
