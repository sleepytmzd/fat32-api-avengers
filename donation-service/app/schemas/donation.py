from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class OrderStatusEnum(str, Enum):
    """Order status enumeration for Pydantic"""
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CreateOrderRequest(BaseModel):
    """Schema for creating a new order - equivalent to Go CreateOrderRequest"""
    user_id: int = Field(..., gt=0, description="ID of the user placing the order")
    product_id: int = Field(..., gt=0, description="ID of the product being ordered")
    quantity: int = Field(..., gt=0, description="Quantity of products to order")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": 1,
                "product_id": 1,
                "quantity": 2
            }
        }


class UpdateOrderRequest(BaseModel):
    """Schema for updating an existing order"""
    quantity: Optional[int] = Field(None, gt=0, description="New quantity")
    status: Optional[OrderStatusEnum] = Field(None, description="New order status")

    class Config:
        json_schema_extra = {
            "example": {
                "quantity": 3,
                "status": "paid"
            }
        }


class OrderResponse(BaseModel):
    """Schema for order responses"""
    id: int
    user_id: int
    product_id: int
    quantity: int
    status: OrderStatusEnum
    total_price: float = Field(..., description="Total price for the order")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "user_id": 1,
                "product_id": 1,
                "quantity": 2,
                "status": "pending",
                "total_price": 1999.98,
                "created_at": "2025-11-12T14:30:00Z",
                "updated_at": "2025-11-12T14:30:00Z"
            }
        }


class OrderListResponse(BaseModel):
    """Schema for paginated order list response"""
    orders: list[OrderResponse]
    total: int
    skip: int
    limit: int

    class Config:
        json_schema_extra = {
            "example": {
                "orders": [
                    {
                        "id": 1,
                        "user_id": 1,
                        "product_id": 1,
                        "quantity": 2,
                        "status": "pending",
                        "total_price": 1999.98,
                        "created_at": "2025-11-12T14:30:00Z",
                        "updated_at": "2025-11-12T14:30:00Z"
                    }
                ],
                "total": 1,
                "skip": 0,
                "limit": 100
            }
        }


class OrderEvent(BaseModel):
    """Schema for order events - equivalent to Go OrderEvent"""
    order_id: int
    user_id: int
    product_id: int
    quantity: int
    status: OrderStatusEnum
    total_price: float
    event_type: str = Field(..., description="Type of event: order_created, order_paid, order_failed")

    class Config:
        json_schema_extra = {
            "example": {
                "order_id": 1,
                "user_id": 1,
                "product_id": 1,
                "quantity": 2,
                "status": "pending",
                "total_price": 1999.98,
                "event_type": "order_created"
            }
        }