"""
Simplified Authentication Module
Gateway handles JWT, delegates user logic to user-service
"""
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import logging
import re
import httpx

from core.config import settings

logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)

# ============================================================================
# SIMPLE PATH-BASED ACCESS CONTROL
# ============================================================================

# Public paths that don't require authentication
PUBLIC_PATHS = [
    r"^/api/v1/user-service/auth/register$",
    r"^/api/v1/user-service/auth/login$",
    r"^/api/v1/user-service/auth/forgot-password$",
    r"^/api/v1/campaign-service/campaigns.*",  # Public product browsing (GET only in handler)
    r".*/health$",
    r".*/docs.*",
]

# Admin-only paths
ADMIN_PATHS = [
    r"^/api/v1/user-service/users.*",  # User management
    r"^/api/v1/campaign-service/admin/.*",
    r"^/api/v1/donation-service/admin/.*",
]

def is_public_path(service: str, path: str) -> bool:
    """Check if path is public"""
    full_path = f"{service}/{path}"
    for pattern in PUBLIC_PATHS:
        if re.match(pattern, full_path):
            return True
    return False

def requires_admin(service: str, path: str) -> bool:
    """Check if path requires admin role"""
    full_path = f"{service}/{path}"
    for pattern in ADMIN_PATHS:
        if re.match(pattern, full_path):
            return True
    return False

# ============================================================================
# JWT TOKEN HANDLING
# ============================================================================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(seconds=settings.JWT_EXPIRATION)
    
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM
    )
    
    return encoded_jwt

def decode_token(token: str) -> Dict:
    """Decode and validate JWT token"""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        # Check expiration
        exp = payload.get("exp")
        if exp and datetime.fromtimestamp(exp) < datetime.utcnow():
            raise HTTPException(status_code=401, detail="Token expired")
        
        return payload
    
    except JWTError as e:
        logger.error(f"JWT decode error: {str(e)}")
        raise HTTPException(
            status_code=401,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def verify_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security)
) -> Optional[Dict]:
    """Verify JWT token (optional)"""
    if not credentials:
        return None
    
    try:
        token = credentials.credentials
        return decode_token(token)
    except HTTPException:
        raise

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> Dict:
    """Get current user (required)"""
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return await verify_token(credentials)

async def check_access(
    service_name: str,
    path: str,
    method: str,
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security)
) -> Optional[Dict]:
    """
    Simple access control:
    - Public paths: no auth needed
    - Admin paths: admin role required
    - Everything else: any authenticated user
    """
    # Check if public
    if is_public_path(service_name, path):
        # Special case: product browsing only public for GET
        if service_name == "product-service" and method != "GET":
            if not credentials:
                raise HTTPException(status_code=401, detail="Authentication required")
            return await verify_token(credentials)
        return None
    
    # Require authentication for non-public paths
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    user = await verify_token(credentials)
    
    # Check admin requirement
    if requires_admin(service_name, path):
        if user.get("role") != "admin":
            raise HTTPException(
                status_code=403,
                detail="Admin access required"
            )
    
    return user