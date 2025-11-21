from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class OrderItem(BaseModel):
    """Order item schema for events"""
    product_id: int
    quantity: int
    price: float


class OrderCreatedEvent(BaseModel):
    """Schema for order_created Kafka event"""
    event_type: str = "order_created"
    order_id: str
    user_id: str
    items: List[OrderItem]
    total_amount: float
    status: str
    timestamp: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "event_type": "order_created",
                "order_id": "123",
                "user_id": "456",
                "items": [
                    {
                        "product_id": 1,
                        "quantity": 2,
                        "price": 29.99
                    }
                ],
                "total_amount": 59.98,
                "status": "pending",
                "timestamp": "2024-01-01T12:00:00Z"
            }
        }
