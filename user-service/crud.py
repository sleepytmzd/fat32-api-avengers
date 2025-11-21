"""
User Service - CRUD Operations
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List
from models import User, UserCreate, UserUpdate
from utils import hash_password, verify_password
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# CREATE
# ============================================================================

async def create_user(db: AsyncSession, user_data: UserCreate) -> User:
    """Create a new user"""
    # Hash password
    hashed_password = hash_password(user_data.password)
    
    # Create user object
    user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        role=user_data.role or "user"
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    logger.info(f"Created user: {user.email}")
    return user

# ============================================================================
# READ
# ============================================================================

async def get_user_by_id(db: AsyncSession, user_id: str) -> Optional[User]:
    """Get user by ID"""
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    return result.scalar_one_or_none()

async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """Get user by email"""
    result = await db.execute(
        select(User).where(User.email == email)
    )
    return result.scalar_one_or_none()

async def get_all_users(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100
) -> List[User]:
    """Get all users with pagination"""
    result = await db.execute(
        select(User).offset(skip).limit(limit)
    )
    return result.scalars().all()

# ============================================================================
# UPDATE
# ============================================================================

async def update_user(
    db: AsyncSession,
    user_id: str,
    user_data: UserUpdate
) -> User:
    """Update user"""
    user = await get_user_by_id(db, user_id)
    if not user:
        return None
    
    # Update fields
    update_data = user_data.dict(exclude_unset=True)
    
    # Handle password separately
    if "password" in update_data:
        update_data["hashed_password"] = hash_password(update_data.pop("password"))
    
    for field, value in update_data.items():
        setattr(user, field, value)
    
    await db.commit()
    await db.refresh(user)
    
    logger.info(f"Updated user: {user.email}")
    return user

# ============================================================================
# DELETE
# ============================================================================

async def delete_user(db: AsyncSession, user_id: str) -> bool:
    """Delete user"""
    user = await get_user_by_id(db, user_id)
    if not user:
        return False
    
    await db.delete(user)
    await db.commit()
    
    logger.info(f"Deleted user: {user.email}")
    return True

# ============================================================================
# AUTHENTICATION
# ============================================================================

async def validate_user_credentials(
    db: AsyncSession,
    email: str,
    password: str
) -> Optional[User]:
    """Validate user credentials"""
    user = await get_user_by_email(db, email)
    
    if not user:
        return None
    
    if not verify_password(password, user.hashed_password):
        return None
    
    return user