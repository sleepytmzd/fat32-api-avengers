"""
Payment Service - Payment processing and tracking
"""
import asyncio
from fastapi import FastAPI, HTTPException, Header, Depends, Query
from typing import Optional, List
from datetime import datetime
import logging
from decimal import Decimal

from database import get_db, init_db
from models import (
    Payment, PaymentCreate, PaymentUpdate, PaymentResponse,
    PaymentStatus, PaymentMethod
)
from crud import (
    create_payment,
    get_payment_by_id,
    get_payment_by_order_id,
    get_user_payments,
    update_payment_status,
    process_refund
)
from kafka_handler import KafkaHandler
from prometheus_fastapi_instrumentator import Instrumentator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Payment Service",
    description="Payment processing and transaction tracking",
    version="1.0.0"
)

kafka_handler = KafkaHandler()
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

@app.on_event("startup")
async def startup():
    """Initialize database on startup"""
    logger.info("Initializing Payment Service...")
    await init_db()
    await kafka_handler.start()

    # Start Kafka consumer in background
    asyncio.create_task(kafka_handler.consume_events())

    logger.info("Payment Service started successfully")
    logger.info("Kafka consumer running")

@app.on_event("shutdown")
async def shutdown():
    """Cleanup"""
    await kafka_handler.stop()
    logger.info("Payment Service stopped")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "payment-service", "kafka_connected": kafka_handler.is_connected()}

# ============================================================================
# HELPER: Extract user from gateway headers
# ============================================================================

def get_current_user_id(x_user_id: Optional[str] = Header(None)) -> Optional[str]:
    """Extract user ID from gateway header"""
    return x_user_id

def get_current_user_role(x_user_role: Optional[str] = Header(None)) -> Optional[str]:
    """Extract user role from gateway header"""
    return x_user_role

def require_user(x_user_id: Optional[str] = Header(None)) -> str:
    """Require authenticated user"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    return x_user_id

def require_admin(x_user_role: Optional[str] = Header(None)):
    """Require admin role"""
    if x_user_role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

# ============================================================================
# USER ENDPOINTS - Payment Management
# ============================================================================

@app.get("/payments/my", response_model=List[PaymentResponse])
async def get_my_payments(
    user_id: str = Depends(require_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[PaymentStatus] = None,
    db = Depends(get_db)
):
    """Get current user's payments"""
    payments = await get_user_payments(
        db,
        user_id=user_id,
        skip=skip,
        limit=limit,
        status=status
    )
    return [PaymentResponse.from_orm(p) for p in payments]

@app.get("/payments/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: str,
    user_id: str = Depends(require_user),
    user_role: str = Depends(get_current_user_role),
    db = Depends(get_db)
):
    """Get payment by ID"""
    payment = await get_payment_by_id(db, payment_id)
    
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    # Users can only see their own payments, admins can see all
    if user_role != "admin" and payment.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return PaymentResponse.from_orm(payment)

# ============================================================================
# INTERNAL ENDPOINTS - For service-to-service communication
# ============================================================================

# @app.post("/internal/payments/initiate")
# async def initiate_payment(request: dict, db = Depends(get_db)):
#     """
#     Initiate a payment for an order
#     Called by Order Service
#     """
#     user_id = request.get("user_id")
#     order_id = request.get("order_id")
#     amount = Decimal(str(request.get("amount")))
#     currency = request.get("currency", "USD")
#     payment_method = request.get("payment_method", "card")
    
#     if not all([user_id, order_id, amount]):
#         raise HTTPException(
#             status_code=400,
#             detail="user_id, order_id, and amount are required"
#         )
    
#     # Create payment record
#     payment_data = PaymentCreate(
#         user_id=user_id,
#         order_id=order_id,
#         amount=amount,
#         currency=currency,
#         payment_method=PaymentMethod(payment_method),
#         status=PaymentStatus.PENDING
#     )
    
#     payment = await create_payment(db, payment_data)
    
#     logger.info(f"Initiated payment {payment.id} for order {order_id}")
    
#     return {
#         "payment_id": str(payment.id),
#         "status": payment.status.value,
#         "amount": float(payment.amount),
#         "currency": payment.currency
#     }

# @app.post("/internal/payments/{payment_id}/process")
# async def process_payment(payment_id: str, request: dict, db = Depends(get_db)):
#     """
#     Process a payment
#     Called by Order Service
#     This simulates payment processing - in production, integrate with Stripe/PayPal
#     """
#     payment = await get_payment_by_id(db, payment_id)
    
#     if not payment:
#         raise HTTPException(status_code=404, detail="Payment not found")
    
#     if payment.status != PaymentStatus.PENDING:
#         raise HTTPException(
#             status_code=400,
#             detail=f"Payment already {payment.status.value}"
#         )
    
#     # Simulate payment processing
#     # In production: call Stripe, PayPal, etc.
#     success = request.get("simulate_success", True)
    
#     if success:
#         # Payment successful
#         payment = await update_payment_status(
#             db,
#             payment_id,
#             PaymentStatus.COMPLETED
#         )
        
#         # Generate transaction ID (in production, this comes from payment gateway)
#         payment.transaction_id = f"TXN-{payment.id}"
#         await db.commit()
#         await db.refresh(payment)
        
#         logger.info(f"Payment {payment_id} processed successfully")
        
#         return {
#             "success": True,
#             "payment_id": str(payment.id),
#             "status": payment.status.value,
#             "transaction_id": payment.transaction_id
#         }
#     else:
#         # Payment failed
#         payment = await update_payment_status(
#             db,
#             payment_id,
#             PaymentStatus.FAILED
#         )
        
#         payment.failure_reason = request.get("failure_reason", "Payment declined")
#         await db.commit()
        
#         logger.warning(f"Payment {payment_id} failed")
        
#         return {
#             "success": False,
#             "payment_id": str(payment.id),
#             "status": payment.status.value,
#             "failure_reason": payment.failure_reason
#         }

# @app.post("/internal/payments/{payment_id}/refund")
# async def refund_payment_internal(
#     payment_id: str,
#     request: dict,
#     db = Depends(get_db)
# ):
#     """
#     Refund a payment
#     Called by Order Service when order is cancelled
#     """
#     reason = request.get("reason", "Order cancelled")
    
#     payment = await process_refund(db, payment_id, reason)
    
#     if not payment:
#         raise HTTPException(status_code=404, detail="Payment not found")
    
#     logger.info(f"Refunded payment {payment_id}")
    
#     return {
#         "success": True,
#         "payment_id": str(payment.id),
#         "status": payment.status.value,
#         "refunded_amount": float(payment.amount)
#     }

# @app.get("/internal/payments/order/{order_id}")
# async def get_payment_by_order(order_id: str, db = Depends(get_db)):
#     """
#     Get payment for an order
#     Called by Order Service
#     """
#     payment = await get_payment_by_order_id(db, order_id)
    
#     if not payment:
#         return {"payment": None}
    
#     return {
#         "payment": {
#             "id": str(payment.id),
#             "status": payment.status.value,
#             "amount": float(payment.amount),
#             "currency": payment.currency,
#             "transaction_id": payment.transaction_id
#         }
#     }

# ============================================================================
# ADMIN ENDPOINTS - Payment Administration
# ============================================================================

@app.get("/admin/payments", dependencies=[Depends(require_admin)])
async def list_all_payments(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    status: Optional[PaymentStatus] = None,
    user_id: Optional[str] = None,
    db = Depends(get_db)
):
    """List all payments (admin only)"""
    from crud import get_all_payments
    
    payments = await get_all_payments(
        db,
        skip=skip,
        limit=limit,
        status=status,
        user_id=user_id
    )
    return [PaymentResponse.from_orm(p) for p in payments]

@app.post("/admin/payments/{payment_id}/refund", dependencies=[Depends(require_admin)])
async def admin_refund_payment(
    payment_id: str,
    reason: str = "Admin refund",
    db = Depends(get_db)
):
    """Refund a payment (admin only)"""
    payment = await process_refund(db, payment_id, reason)
    
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    return PaymentResponse.from_orm(payment)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8003, reload=True)