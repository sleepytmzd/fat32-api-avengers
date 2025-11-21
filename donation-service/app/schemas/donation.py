from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime
from enum import Enum


class DonationStatusEnum(str, Enum):
    """Donation status enumeration for Pydantic"""
    INITIATED = "initiated"
    AUTHORIZED = "authorized"
    CAPTURED = "captured"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


class CreateDonationRequest(BaseModel):
    """Schema for creating a new donation"""
    user_id: Optional[str] = Field(None, min_length=1, description="ID of registered user (null for guest)")
    campaign_id: int = Field(..., gt=0, description="ID of the campaign to donate to")
    amount: float = Field(..., gt=0, description="Donation amount")
    payment_method: Optional[str] = Field(None, description="Payment method (card, paypal, etc.)")
    donor_name: Optional[str] = Field(None, min_length=1, max_length=255, description="Donor name for guest donations")
    donor_email: Optional[EmailStr] = Field(None, description="Donor email for guest donations")
    message: Optional[str] = Field(None, max_length=1000, description="Optional message from donor")
    is_anonymous: bool = Field(default=False, description="Hide donor identity")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user-123-abc",
                "campaign_id": 5,
                "amount": 100.00,
                "payment_method": "card",
                "message": "Hope this helps!",
                "is_anonymous": False
            }
        }


class UpdateDonationRequest(BaseModel):
    """Schema for updating an existing donation"""
    status: Optional[DonationStatusEnum] = Field(None, description="New donation status")
    payment_id: Optional[str] = Field(None, description="Payment provider transaction ID")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "captured",
                "payment_id": "pi_1234567890"
            }
        }


class DonationResponse(BaseModel):
    """Schema for donation responses"""
    id: int
    user_id: Optional[str]
    campaign_id: int
    amount: float
    status: DonationStatusEnum
    payment_method: Optional[str]
    payment_id: Optional[str]
    donor_name: Optional[str]
    donor_email: Optional[str]
    message: Optional[str]
    is_anonymous: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "user_id": "user-123-abc",
                "campaign_id": 5,
                "amount": 100.00,
                "status": "captured",
                "payment_method": "card",
                "payment_id": "pi_1234567890",
                "donor_name": "John Doe",
                "donor_email": "john@example.com",
                "message": "Hope this helps!",
                "is_anonymous": False,
                "created_at": "2025-11-21T14:30:00Z",
                "updated_at": "2025-11-21T14:30:00Z"
            }
        }


class DonationListResponse(BaseModel):
    """Schema for paginated donation list response"""
    donations: list[DonationResponse]
    total: int

    class Config:
        json_schema_extra = {
            "example": {
                "donations": [
                    {
                        "id": 1,
                        "user_id": "user-123-abc",
                        "campaign_id": 5,
                        "amount": 100.00,
                        "status": "captured",
                        "payment_method": "card",
                        "payment_id": "pi_1234567890",
                        "donor_name": "John Doe",
                        "donor_email": "john@example.com",
                        "message": "Hope this helps!",
                        "is_anonymous": False,
                        "created_at": "2025-11-21T14:30:00Z",
                        "updated_at": "2025-11-21T14:30:00Z"
                    }
                ],
                "total": 1
            }
        }


class DonationEvent(BaseModel):
    """Schema for donation events"""
    donation_id: int
    user_id: Optional[str]
    campaign_id: int
    amount: float
    status: DonationStatusEnum
    event_type: str = Field(..., description="Type of event: donation_initiated, donation_captured, donation_failed, etc.")
    timestamp: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "donation_id": 1,
                "user_id": "user-123-abc",
                "campaign_id": 5,
                "amount": 100.00,
                "status": "captured",
                "event_type": "donation_captured",
                "timestamp": "2025-11-21T14:30:00Z"
            }
        }