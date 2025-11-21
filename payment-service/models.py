"""
Payment Service - Data Models
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from decimal import Decimal
from enum import Enum
from sqlalchemy import Column, String, Numeric, DateTime, Text, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from database import Base
import uuid

# ============================================================================
# Enums
# ============================================================================

class PaymentStatus(str, Enum):
    """Payment status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"

class PaymentMethod(str, Enum):
    """Payment method"""
    CARD = "card"
    BANK_TRANSFER = "bank_transfer"
    WALLET = "wallet"
    CASH_ON_DELIVERY = "cash_on_delivery"

# ============================================================================
# SQLAlchemy Model (Database)
# ============================================================================

class Payment(Base):
    """Payment database model"""
    __tablename__ = "payments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    donation_id = Column(String(255), nullable=True, index=True)  # Donation ID (for donation payments)
    campaign_id = Column(String(255), nullable=True, index=True)  # Campaign ID (optional)
    
    # Payment details
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="USD", nullable=False)
    payment_method = Column(SQLEnum(PaymentMethod), nullable=False)
    status = Column(SQLEnum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False)
    
    # Transaction details
    transaction_id = Column(String(255), unique=True, nullable=True)
    failure_reason = Column(Text, nullable=True)
    refund_reason = Column(Text, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    refunded_at = Column(DateTime, nullable=True)

# ============================================================================
# Pydantic Models (API)
# ============================================================================

class PaymentBase(BaseModel):
    """Base payment model"""
    user_id: str
    donation_id: Optional[str] = None
    campaign_id: Optional[str] = None
    amount: Decimal = Field(..., gt=0)
    currency: str = Field(default="USD", max_length=3)
    payment_method: PaymentMethod

class PaymentCreate(PaymentBase):
    """Payment creation model"""
    status: PaymentStatus = PaymentStatus.PENDING

class PaymentUpdate(BaseModel):
    """Payment update model"""
    status: Optional[PaymentStatus] = None
    transaction_id: Optional[str] = None
    failure_reason: Optional[str] = None
    refund_reason: Optional[str] = None

class PaymentResponse(BaseModel):
    """Payment response model"""
    id: uuid.UUID
    user_id: uuid.UUID
    donation_id: Optional[str] = None
    campaign_id: Optional[str] = None
    amount: Decimal
    currency: str
    payment_method: PaymentMethod
    status: PaymentStatus
    transaction_id: Optional[str]
    failure_reason: Optional[str]
    refund_reason: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    completed_at: Optional[datetime]
    refunded_at: Optional[datetime]
    
    class Config:
        from_attributes = True