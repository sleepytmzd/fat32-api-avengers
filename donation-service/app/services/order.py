from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.order import Order, OrderStatus
from app.schemas.order import CreateOrderRequest, UpdateOrderRequest, OrderResponse
from app.kafka.producer import get_kafka_producer
import structlog

logger = structlog.get_logger(__name__)


class OrderService:
    """Business logic for order operations"""

    @staticmethod
    def create_order(db: Session, order_data: CreateOrderRequest, product_price: float) -> OrderResponse:
        """Create a new order"""
        try:
            # Calculate total price
            total_price = product_price * order_data.quantity
            
            # Create new order instance
            db_order = Order(
                user_id=order_data.user_id,
                product_id=order_data.product_id,
                quantity=order_data.quantity,
                total_price=total_price,
                status=OrderStatus.PENDING
            )
            
            # Add to database
            db.add(db_order)
            db.commit()
            db.refresh(db_order)
            
            logger.info("Order created successfully", 
                       order_id=db_order.id, 
                       user_id=db_order.user_id, 
                       product_id=db_order.product_id,
                       total_price=total_price)
            
            return OrderResponse(
                id=db_order.id,
                user_id=db_order.user_id,
                product_id=db_order.product_id,
                quantity=db_order.quantity,
                status=db_order.status.value,
                total_price=db_order.total_price,
                created_at=db_order.created_at,
                updated_at=db_order.updated_at
            ), db_order  # Return both response and db_order for Kafka publishing
            
        except Exception as e:
            db.rollback()
            logger.error("Failed to create order", error=str(e), order_data=order_data.dict())
            raise Exception(f"Failed to create order: {str(e)}")

    @staticmethod
    def get_order(db: Session, order_id: int) -> Optional[OrderResponse]:
        """Get an order by ID"""
        try:
            db_order = db.query(Order).filter(Order.id == order_id).first()
            
            if not db_order:
                logger.warning("Order not found", order_id=order_id)
                return None
            
            logger.info("Order retrieved successfully", order_id=order_id)
            
            return OrderResponse(
                id=db_order.id,
                user_id=db_order.user_id,
                product_id=db_order.product_id,
                quantity=db_order.quantity,
                status=db_order.status.value,
                total_price=db_order.total_price,
                created_at=db_order.created_at,
                updated_at=db_order.updated_at
            )
            
        except Exception as e:
            logger.error("Failed to get order", error=str(e), order_id=order_id)
            raise Exception(f"Failed to get order: {str(e)}")

    @staticmethod
    def get_orders_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[OrderResponse]:
        """Get orders by user ID with pagination"""
        try:
            db_orders = db.query(Order).filter(Order.user_id == user_id).offset(skip).limit(limit).all()
            
            orders = [
                OrderResponse(
                    id=order.id,
                    user_id=order.user_id,
                    product_id=order.product_id,
                    quantity=order.quantity,
                    status=order.status.value,
                    total_price=order.total_price,
                    created_at=order.created_at,
                    updated_at=order.updated_at
                )
                for order in db_orders
            ]
            
            logger.info("Orders retrieved successfully", user_id=user_id, count=len(orders))
            
            return orders
            
        except Exception as e:
            logger.error("Failed to get orders", error=str(e), user_id=user_id)
            raise Exception(f"Failed to get orders: {str(e)}")

    @staticmethod
    def get_all_orders(db: Session, skip: int = 0, limit: int = 100) -> List[OrderResponse]:
        """Get all orders with pagination"""
        try:
            db_orders = db.query(Order).offset(skip).limit(limit).all()
            
            orders = [
                OrderResponse(
                    id=order.id,
                    user_id=order.user_id,
                    product_id=order.product_id,
                    quantity=order.quantity,
                    status=order.status.value,
                    total_price=order.total_price,
                    created_at=order.created_at,
                    updated_at=order.updated_at
                )
                for order in db_orders
            ]
            
            logger.info("All orders retrieved successfully", count=len(orders))
            
            return orders
            
        except Exception as e:
            logger.error("Failed to get all orders", error=str(e))
            raise Exception(f"Failed to get all orders: {str(e)}")

    @staticmethod
    def update_order_status(db: Session, order_id: int, status: OrderStatus) -> Optional[OrderResponse]:
        """Update order status"""
        try:
            db_order = db.query(Order).filter(Order.id == order_id).first()
            
            if not db_order:
                logger.warning("Order not found for status update", order_id=order_id)
                return None
            
            db_order.status = status
            db.commit()
            db.refresh(db_order)
            
            logger.info("Order status updated successfully", order_id=order_id, new_status=status.value)
            
            return OrderResponse(
                id=db_order.id,
                user_id=db_order.user_id,
                product_id=db_order.product_id,
                quantity=db_order.quantity,
                status=db_order.status.value,
                total_price=db_order.total_price,
                created_at=db_order.created_at,
                updated_at=db_order.updated_at
            )
            
        except Exception as e:
            db.rollback()
            logger.error("Failed to update order status", error=str(e), order_id=order_id)
            raise Exception(f"Failed to update order status: {str(e)}")