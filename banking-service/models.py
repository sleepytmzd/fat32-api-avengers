"""
Banking Service Database Models
"""
from sqlalchemy import Column, String, Numeric
from sqlalchemy.ext.declarative import declarative_base
from decimal import Decimal
from pydantic import BaseModel
from typing import Optional

Base = declarative_base()

class BankAccount(Base):
    """Bank account model - simplified for demo"""
    __tablename__ = "bank_accounts"
    
    user_id = Column(String, primary_key=True, index=True)
    balance = Column(Numeric(precision=10, scale=2), default=1000.00, nullable=False)

# Pydantic models
class BankAccountCreate(BaseModel):
    initial_balance: Decimal = Decimal("1000.00")

class BankAccountResponse(BaseModel):
    user_id: str
    balance: Decimal
    
    class Config:
        from_attributes = True

class DebitRequest(BaseModel):
    user_id: str
    amount: Decimal

class DebitResponse(BaseModel):
    success: bool
    new_balance: Optional[Decimal] = None
    message: str
