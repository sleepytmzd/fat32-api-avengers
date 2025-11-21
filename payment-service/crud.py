"""
Payment Service - CRUD Operations
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List
from datetime import datetime
from models import Payment, PaymentCreate, PaymentStatus
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# CREATE
# ============================================================================

async def create_payment(db: AsyncSession, payment_data: PaymentCreate) -> Payment:
    """Create a new payment"""
    payment = Payment(**payment_data.dict())
    
    db.add(payment)
    await db.commit()
    await db.refresh(payment)
    
    reference = payment.donation_id or "N/A"
    logger.info(
        f"Created payment {payment.id} for donation {reference}, "
        f"amount: {payment.amount} {payment.currency}"
    )
    return payment

# ============================================================================
# READ
# ============================================================================

async def get_payment_by_id(db: AsyncSession, payment_id: str) -> Optional[Payment]:
    """Get payment by ID"""
    result = await db.execute(
        select(Payment).where(Payment.id == payment_id)
    )
    return result.scalar_one_or_none()

async def get_payment_by_donation_id(db: AsyncSession, donation_id: str) -> Optional[Payment]:
    """Get payment by donation ID"""
    result = await db.execute(
        select(Payment).where(Payment.donation_id == donation_id)
    )
    return result.scalar_one_or_none()

async def get_user_payments(
    db: AsyncSession,
    user_id: str,
    skip: int = 0,
    limit: int = 100,
    status: Optional[PaymentStatus] = None
) -> List[Payment]:
    """Get all payments for a user"""
    query = select(Payment).where(Payment.user_id == user_id)
    
    if status:
        query = query.where(Payment.status == status)
    
    query = query.order_by(Payment.created_at.desc()).offset(skip).limit(limit)
    
    result = await db.execute(query)
    return result.scalars().all()

async def get_all_payments(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    status: Optional[PaymentStatus] = None,
    user_id: Optional[str] = None
) -> List[Payment]:
    """Get all payments with filtering (admin)"""
    query = select(Payment)
    
    if status:
        query = query.where(Payment.status == status)
    
    if user_id:
        query = query.where(Payment.user_id == user_id)
    
    query = query.order_by(Payment.created_at.desc()).offset(skip).limit(limit)
    
    result = await db.execute(query)
    return result.scalars().all()

# ============================================================================
# UPDATE
# ============================================================================

async def update_payment_status(
    db: AsyncSession,
    payment_id: str,
    status: PaymentStatus
) -> Optional[Payment]:
    """Update payment status"""
    payment = await get_payment_by_id(db, payment_id)
    if not payment:
        return None
    
    old_status = payment.status
    payment.status = status
    
    # Set completion timestamp
    if status == PaymentStatus.COMPLETED:
        payment.completed_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(payment)
    
    logger.info(
        f"Updated payment {payment_id} status: {old_status.value} -> {status.value}"
    )
    return payment

async def process_refund(
    db: AsyncSession,
    payment_id: str,
    reason: str
) -> Optional[Payment]:
    """Process payment refund"""
    payment = await get_payment_by_id(db, payment_id)
    if not payment:
        return None
    
    if payment.status != PaymentStatus.COMPLETED:
        logger.warning(
            f"Cannot refund payment {payment_id} with status {payment.status.value}"
        )
        return None
    
    payment.status = PaymentStatus.REFUNDED
    payment.refund_reason = reason
    payment.refunded_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(payment)
    
    logger.info(f"Refunded payment {payment_id}: {reason}")
    return payment