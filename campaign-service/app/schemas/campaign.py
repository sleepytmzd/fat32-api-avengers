from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional


class CreateCampaignRequest(BaseModel):
    """Request schema for creating a campaign"""
    title: str = Field(..., min_length=1, description="Campaign title is required")
    name: str = Field(..., min_length=1, description="Campaign name is required")
    description: Optional[str] = Field(None, description="Campaign description")
    product_id: int = Field(..., gt=0, description="Product ID must be greater than 0")
    start_date: datetime = Field(..., description="Campaign start date")
    end_date: datetime = Field(..., description="Campaign end date")
    is_active: bool = Field(default=True, description="Whether campaign is active")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Summer Sale 2025",
                "name": "summer-sale-2025",
                "description": "Get amazing deals this summer",
                "product_id": 1,
                "start_date": "2025-06-01T00:00:00Z",
                "end_date": "2025-08-31T23:59:59Z",
                "is_active": True
            }
        }
    )


class UpdateCampaignRequest(BaseModel):
    """Request schema for updating a campaign"""
    title: Optional[str] = Field(None, min_length=1, description="Campaign title")
    name: Optional[str] = Field(None, min_length=1, description="Campaign name")
    description: Optional[str] = Field(None, description="Campaign description")
    product_id: Optional[int] = Field(None, gt=0, description="Product ID")
    start_date: Optional[datetime] = Field(None, description="Campaign start date")
    end_date: Optional[datetime] = Field(None, description="Campaign end date")
    is_active: Optional[bool] = Field(None, description="Whether campaign is active")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Summer Sale 2025 Extended",
                "end_date": "2025-09-15T23:59:59Z",
                "is_active": True
            }
        }
    )


class CampaignResponse(BaseModel):
    """Response schema for campaign data"""
    id: int
    title: str
    name: str
    description: Optional[str]
    product_id: int
    start_date: datetime
    end_date: datetime
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,  # Allows conversion from SQLAlchemy models
        json_schema_extra={
            "example": {
                "id": 1,
                "title": "Summer Sale 2025",
                "name": "summer-sale-2025",
                "description": "Get amazing deals this summer",
                "product_id": 1,
                "start_date": "2025-06-01T00:00:00Z",
                "end_date": "2025-08-31T23:59:59Z",
                "is_active": True,
                "created_at": "2025-05-01T10:00:00Z",
                "updated_at": "2025-05-01T10:00:00Z"
            }
        }
    )


class CampaignListResponse(BaseModel):
    """Response schema for list of campaigns"""
    campaigns: list[CampaignResponse]
    total: int
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "campaigns": [
                    {
                        "id": 1,
                        "title": "Summer Sale 2025",
                        "name": "summer-sale-2025",
                        "description": "Get amazing deals this summer",
                        "product_id": 1,
                        "start_date": "2025-06-01T00:00:00Z",
                        "end_date": "2025-08-31T23:59:59Z",
                        "is_active": True,
                        "created_at": "2025-05-01T10:00:00Z",
                        "updated_at": "2025-05-01T10:00:00Z"
                    }
                ],
                "total": 1
            }
        }
    )