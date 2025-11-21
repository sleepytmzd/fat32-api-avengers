from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class DonationCreatedEvent(BaseModel):
    """Schema for donation_created Kafka event"""
    event_type: str = "donation_created"
    donation_id: int
    user_id: Optional[str]
    campaign_id: int
    amount: float
    status: str
    payment_method: Optional[str]
    is_anonymous: bool
    timestamp: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "event_type": "donation_created",
                "donation_id": 123,
                "user_id": "user-456-def",
                "campaign_id": 5,
                "amount": 100.00,
                "status": "initiated",
                "payment_method": "card",
                "is_anonymous": False,
                "timestamp": "2025-11-21T12:00:00Z"
            }
        }


class DonationCapturedEvent(BaseModel):
    """Schema for donation_captured Kafka event"""
    event_type: str = "donation_captured"
    donation_id: int
    user_id: Optional[str]
    campaign_id: int
    amount: float
    payment_id: str
    timestamp: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "event_type": "donation_captured",
                "donation_id": 123,
                "user_id": "user-456-def",
                "campaign_id": 5,
                "amount": 100.00,
                "payment_id": "pi_1234567890",
                "timestamp": "2025-11-21T12:05:00Z"
            }
        }


class DonationFailedEvent(BaseModel):
    """Schema for donation_failed Kafka event"""
    event_type: str = "donation_failed"
    donation_id: int
    user_id: Optional[str]
    campaign_id: int
    amount: float
    reason: str
    timestamp: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "event_type": "donation_failed",
                "donation_id": 123,
                "user_id": "user-456-def",
                "campaign_id": 5,
                "amount": 100.00,
                "reason": "Insufficient funds",
                "timestamp": "2025-11-21T12:05:00Z"
            }
        }
