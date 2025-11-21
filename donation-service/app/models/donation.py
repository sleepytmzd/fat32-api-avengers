from sqlalchemy import Column, Integer, String, Float, DateTime, func, Enum, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
import enum

Base = declarative_base()


class DonationStatus(enum.Enum):
    """Donation status enumeration following payment flow"""
    INITIATED = "initiated"  # Donation intent created
    AUTHORIZED = "authorized"  # Payment authorized but not captured
    CAPTURED = "captured"  # Payment completed successfully
    FAILED = "failed"  # Payment failed
    REFUNDED = "refunded"  # Donation refunded
    CANCELLED = "cancelled"  # Donation cancelled by user


class Donation(Base):
    """Donation model for fundraising campaigns"""
    __tablename__ = "donations"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, nullable=True, index=True)  # Nullable for guest donations
    campaign_id = Column(Integer, nullable=False, index=True)  # Campaign being donated to
    amount = Column(Float, nullable=False)  # Donation amount
    status = Column(Enum(DonationStatus), nullable=False, default=DonationStatus.INITIATED)
    payment_method = Column(String, nullable=True)  # e.g., 'card', 'paypal', 'bank_transfer'
    payment_id = Column(String, nullable=True, index=True)  # External payment provider ID
    donor_name = Column(String, nullable=True)  # For guest donations
    donor_email = Column(String, nullable=True)  # For guest donations
    message = Column(Text, nullable=True)  # Optional message from donor
    is_anonymous = Column(Boolean, nullable=False, default=False)  # Hide donor identity
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<Donation(id={self.id}, campaign_id={self.campaign_id}, amount={self.amount}, status='{self.status.value}')>"