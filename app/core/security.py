from datetime import datetime, timedelta
from typing import Optional, Dict
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import settings
from app.core.database import get_database
from app.models.user import User
import logging

logger = logging.getLogger(__name__)
security = HTTPBearer()

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict):
    """Create JWT refresh token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Optional[Dict]:
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        return None




async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db=Depends(get_database)
) -> dict:
    """Get current authenticated user"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token = credentials.credentials
    payload = verify_token(token)
    
    if payload is None or payload.get("type") != "access":
        raise credentials_exception
    
    user_email = payload.get("email")  
    
    if user_email is None:
        raise credentials_exception
    
    user_model = User(db)
    user = await user_model.get_user_by_email(user_email)
    
    if user is None:
        raise credentials_exception
    
    return user

async def get_current_admin_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db=Depends(get_database)
) -> dict:
    """Get current authenticated admin user"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Admin access required",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token = credentials.credentials
    logger.info(f"🔍 ADMIN Token received: {token[:20]}...")
    
    payload = verify_token(token)
    logger.info(f"🔍 ADMIN Payload decoded: {payload}")
    
    if payload is None or payload.get("type") != "access":
        logger.error("❌ ADMIN Token validation failed")
        raise credentials_exception
    
    user_email = payload.get("email")
    user_role = payload.get("role")
    logger.info(f"🔍 ADMIN Email: {user_email}, Role: {user_role}")
    
    if user_email is None or user_role != "admin":
        logger.error(f"❌ ADMIN Role check failed: email={user_email}, role={user_role}")
        raise credentials_exception
    
    user_model = User(db)
    user = await user_model.get_user_by_email(user_email)
    logger.info(f"🔍 ADMIN User found: {user is not None}")
    
    if user is None or user.get("role") != "admin":
        logger.error(f"❌ ADMIN User lookup failed or not admin")
        raise credentials_exception
    
    logger.info(f"✅ ADMIN authenticated: {user.get('email')}")
    return user


def create_tokens(user: Dict) -> Dict:
    """Create both access and refresh tokens"""
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    token_data = {
        "sub": str(user["id"]),
        "email": user["email"],
        "role": user["role"]
    }
    
    access_token = create_access_token(data=token_data, expires_delta=access_token_expires)
    refresh_token = create_refresh_token(data=token_data)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

