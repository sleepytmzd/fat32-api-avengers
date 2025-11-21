"""
Banking Service - Account management and balance operations
"""
import asyncio
from fastapi import FastAPI, HTTPException, Header, Depends
from typing import Optional
import logging
from decimal import Decimal

from database import get_db, init_db, close_db
from models import BankAccount, BankAccountCreate, BankAccountResponse, DebitRequest, DebitResponse
from crud import (
    create_account,
    get_account_by_user_id,
    check_balance,
    debit_account,
    credit_account
)
from config import settings
from prometheus_fastapi_instrumentator import Instrumentator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Banking Service",
    description="Bank account management and balance operations",
    version="1.0.0"
)

# Initialize tracing
try:
    from middleware.tracing import init_tracing
    
    if settings.TRACING_ENABLED:
        init_tracing(app, service_name=settings.SERVICE_NAME, jaeger_endpoint=settings.JAEGER_ENDPOINT)
        logger.info(f"Tracing initialized successfully - Service: {settings.SERVICE_NAME}")
    else:
        logger.info("Tracing disabled by configuration")
except Exception as e:
    logger.warning(f"Failed to initialize tracing: {e}")

Instrumentator().instrument(app).expose(app, endpoint="/metrics")

@app.on_event("startup")
async def startup():
    """Initialize database on startup"""
    logger.info("Initializing Banking Service...")
    await init_db()
    logger.info("Banking Service started successfully")

@app.on_event("shutdown")
async def shutdown():
    """Cleanup"""
    await close_db()
    logger.info("Banking Service stopped")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "banking-service"}

# ============================================================================
# Helper Functions
# ============================================================================

def get_current_user_id(x_user_id: Optional[str] = Header(None)) -> Optional[str]:
    """Extract user ID from gateway header"""
    return x_user_id

def require_user(x_user_id: Optional[str] = Header(None)) -> str:
    """Require authenticated user"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    return x_user_id

# ============================================================================
# User Endpoints
# ============================================================================

@app.post("/accounts", response_model=BankAccountResponse)
async def create_bank_account(
    account_data: BankAccountCreate,
    user_id: str = Depends(require_user),
    db = Depends(get_db)
):
    """Create a new bank account for authenticated user"""
    # Check if account already exists
    existing = await get_account_by_user_id(db, user_id)
    if existing:
        raise HTTPException(status_code=400, detail="Account already exists for this user")
    
    account = await create_account(db, user_id, account_data)
    return BankAccountResponse.from_orm(account)

@app.get("/accounts/my", response_model=BankAccountResponse)
async def get_my_account(
    user_id: str = Depends(require_user),
    db = Depends(get_db)
):
    """Get authenticated user's bank account"""
    account = await get_account_by_user_id(db, user_id)
    
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    return BankAccountResponse.from_orm(account)

# ============================================================================
# Internal Endpoints - For service-to-service communication
# ============================================================================

@app.post("/internal/debit", response_model=DebitResponse)
async def debit_user_account(
    request: DebitRequest,
    db = Depends(get_db)
):
    """
    Debit amount from user account
    Called by Payment Service
    """
    success, message, new_balance = await debit_account(
        db,
        user_id=request.user_id,
        amount=request.amount
    )
    
    return DebitResponse(
        success=success,
        new_balance=new_balance if success else None,
        message=message
    )

@app.post("/internal/credit")
async def credit_user_account(
    request: DebitRequest,  # Reuse same model
    db = Depends(get_db)
):
    """
    Credit amount to user account
    Called by Payment Service for refunds
    """
    success, message, new_balance = await credit_account(
        db,
        user_id=request.user_id,
        amount=request.amount
    )
    
    return {
        "success": success,
        "new_balance": float(new_balance) if success else None,
        "message": message
    }

@app.get("/internal/balance/{user_id}")
async def check_user_balance(
    user_id: str,
    amount: Decimal,
    db = Depends(get_db)
):
    """
    Check if user has sufficient balance
    Called by Payment Service
    """
    has_balance, message = await check_balance(db, user_id, amount)
    
    account = await get_account_by_user_id(db, user_id)
    
    return {
        "has_sufficient_balance": has_balance,
        "message": message,
        "current_balance": float(account.balance) if account else 0
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8006, reload=True)
