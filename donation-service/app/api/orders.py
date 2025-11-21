from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from app.database.database import get_db
from app.services.order import OrderService
from app.services.grpc_client import ProductGRPCClient, get_product_grpc_client
from app.services.http_client import ProductHTTPClient, get_product_http_client
from app.schemas.order import CreateOrderRequest, UpdateOrderRequest, OrderResponse, OrderListResponse
from app.kafka.producer import get_kafka_producer
import structlog
import asyncio

router = APIRouter(prefix="/api/v1/orders", tags=["orders"])
logger = structlog.get_logger(__name__)


@router.post("", response_model=OrderResponse, status_code=201)
async def create_order(
    order_data: CreateOrderRequest,
    db: Session = Depends(get_db)
):
    """
    Create a new order with gRPC stock validation
    Follows the Go implementation pattern:
    1. Check product availability via gRPC
    2. Get product details via gRPC
    3. Calculate total price
    4. Create order in database
    """
    try:
        logger.info(
            "Creating order",
            user_id=order_data.user_id,
            product_id=order_data.product_id,
            quantity=order_data.quantity
        )
        
        # Use gRPC client to check availability and get product details
        async with ProductGRPCClient() as grpc_client:
            # Step 1: Check product availability via gRPC
            # Equivalent to: available, stock, err := h.productClient.CheckAvailability(ctx, int32(req.ProductID), int32(req.Quantity))
            available, current_stock = await grpc_client.check_availability(
                order_data.product_id, 
                order_data.quantity
            )
            
            if not available:
                logger.warning(
                    "Product not available",
                    product_id=order_data.product_id,
                    requested_quantity=order_data.quantity,
                    available_stock=current_stock
                )
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "Product not available",
                        "requested_quantity": order_data.quantity,
                        "available_stock": current_stock
                    }
                )
            
            # Step 2: Get product details to calculate total price
            # Equivalent to: productResp, err := h.productClient.GetProduct(ctx, int32(req.ProductID))
            product_details = await grpc_client.get_product(order_data.product_id)
            
            # Step 3: Calculate total price
            # Equivalent to: totalPrice := float64(req.Quantity) * float64(productResp.GetPrice())
            product_price = product_details["price"]
            total_price = float(order_data.quantity) * product_price
            
            logger.info(
                "Product validation successful",
                product_id=order_data.product_id,
                product_name=product_details["name"],
                unit_price=product_price,
                total_price=total_price,
                available_stock=current_stock
            )
        
        # Step 4: Create order in database
        order, db_order = OrderService.create_order(
            db=db, 
            order_data=order_data, 
            product_price=product_price
        )
        
        # Step 4.5: Reduce product stock via HTTP call
        try:
            http_client = ProductHTTPClient()
            stock_response = await http_client.reduce_stock(
                order_data.product_id,
                order_data.quantity
            )
            logger.info(
                "Product stock reduced via HTTP",
                product_id=order_data.product_id,
                quantity=order_data.quantity,
                new_stock=stock_response.get("stock")
            )
        except Exception as http_error:
            # If stock reduction fails, we should handle it
            # In production, you might want to rollback the order or use saga pattern
            logger.error(
                "Failed to reduce product stock via HTTP",
                order_id=db_order.id,
                product_id=order_data.product_id,
                error=str(http_error)
            )
            # For now, we'll continue but log the error
            # In production, consider implementing compensating transactions
        
        # Step 5: Publish order_created event to Kafka (async, non-blocking)
        try:
            kafka_producer = await get_kafka_producer()
            await kafka_producer.publish_order_created({
                "id": db_order.id,
                "user_id": db_order.user_id,
                "items": [{
                    "product_id": db_order.product_id,
                    "quantity": db_order.quantity,
                    "price": product_price
                }],
                "total_amount": db_order.total_price,
                "status": db_order.status.value,
                "created_at": db_order.created_at.isoformat() if db_order.created_at else None
            })
        except Exception as kafka_error:
            # Log but don't fail order creation if Kafka fails
            import sys
            print(f"[ORDER] ⚠ Kafka publish failed - order_id: {db_order.id}, error: {kafka_error}")
            sys.stdout.flush()
            logger.warning(
                "Failed to publish order_created event to Kafka", 
                order_id=db_order.id, 
                error=str(kafka_error)
            )
        
        print(f"[ORDER] ✓ Order created successfully - order_id: {order.id}, user_id: {order_data.user_id}, total: ${total_price:.2f}")
        import sys
        sys.stdout.flush()
        
        logger.info(
            "Order created successfully",
            order_id=order.id,
            user_id=order_data.user_id,
            product_id=order_data.product_id,
            total_price=total_price
        )
        sys.stdout.flush()
        
        return order
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to create order", 
            error=str(e),
            user_id=order_data.user_id,
            product_id=order_data.product_id
        )
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(
    order_id: int,
    db: Session = Depends(get_db)
):
    """Get an order by ID"""
    try:
        order = OrderService.get_order(db=db, order_id=order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        return order
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get order", error=str(e), order_id=order_id)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/user/{user_id}", response_model=OrderListResponse)
def get_orders_by_user(
    user_id: int,
    skip: int = Query(0, ge=0, description="Number of orders to skip"),
    limit: int = Query(100, ge=1, le=100, description="Number of orders to return"),
    db: Session = Depends(get_db)
):
    """Get orders by user ID with pagination"""
    try:
        orders = OrderService.get_orders_by_user(db=db, user_id=user_id, skip=skip, limit=limit)
        
        return OrderListResponse(
            orders=orders,
            total=len(orders),
            skip=skip,
            limit=limit
        )
    except Exception as e:
        logger.error("Failed to get orders by user", error=str(e), user_id=user_id)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("", response_model=OrderListResponse)
def get_all_orders(
    skip: int = Query(0, ge=0, description="Number of orders to skip"),
    limit: int = Query(100, ge=1, le=100, description="Number of orders to return"),
    db: Session = Depends(get_db)
):
    """Get all orders with pagination"""
    try:
        orders = OrderService.get_all_orders(db=db, skip=skip, limit=limit)
        
        return OrderListResponse(
            orders=orders,
            total=len(orders),
            skip=skip,
            limit=limit
        )
    except Exception as e:
        logger.error("Failed to get all orders", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")