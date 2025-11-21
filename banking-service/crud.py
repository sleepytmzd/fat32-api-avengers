"""
Banking Service CRUD Operations
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import BankAccount, BankAccountCreate
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

async def create_account(db: AsyncSession, user_id: str, account_data: BankAccountCreate) -> BankAccount:
    """Create a new bank account"""
    account = BankAccount(
        user_id=user_id,
        balance=account_data.initial_balance
    )
    
    db.add(account)
    await db.commit()
    await db.refresh(account)
    
    logger.info(f"Created bank account for user {user_id} with balance {account_data.initial_balance}")
    return account

async def get_account_by_user_id(db: AsyncSession, user_id: str) -> BankAccount:
    """Get bank account by user ID"""
    result = await db.execute(
        select(BankAccount).where(BankAccount.user_id == user_id)
    )
    return result.scalar_one_or_none()

async def check_balance(db: AsyncSession, user_id: str, amount: Decimal) -> tuple[bool, str]:
    """Check if user has sufficient balance"""
    account = await get_account_by_user_id(db, user_id)
    
    if not account:
        return False, "Account not found"
    
    if account.balance < amount:
        return False, f"Insufficient balance. Available: {account.balance}, Required: {amount}"
    
    return True, "Sufficient balance"

async def debit_account(db: AsyncSession, user_id: str, amount: Decimal) -> tuple[bool, str, Decimal]:
    """Debit amount from user account"""
    account = await get_account_by_user_id(db, user_id)
    
    if not account:
        return False, "Account not found", Decimal("0")
    
    if account.balance < amount:
        return False, f"Insufficient balance. Available: {account.balance}, Required: {amount}", account.balance
    
    # Deduct the amount
    account.balance -= amount
    await db.commit()
    await db.refresh(account)
    
    logger.info(f"Debited {amount} from user {user_id}. New balance: {account.balance}")
    return True, "Transaction successful", account.balance

async def credit_account(db: AsyncSession, user_id: str, amount: Decimal) -> tuple[bool, str, Decimal]:
    """Credit amount to user account"""
    account = await get_account_by_user_id(db, user_id)
    
    if not account:
        return False, "Account not found", Decimal("0")
    
    # Add the amount
    account.balance += amount
    await db.commit()
    await db.refresh(account)
    
    logger.info(f"Credited {amount} to user {user_id}. New balance: {account.balance}")
    return True, "Transaction successful", account.balance

