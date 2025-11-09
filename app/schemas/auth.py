from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime

class UserRegistration(BaseModel):
    """User registration schema"""
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=72)
    confirm_password: str = Field(..., min_length=6, max_length=72)
    first_name: str = Field(..., min_length=2, max_length=50)
    last_name: Optional[str] = Field(default='', max_length=50)
    phone: str = Field(..., min_length=10, max_length=15)
    date_of_birth: str = Field(..., description="Format: YYYY-MM-DD")
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v
    
    @validator('phone')
    def validate_phone(cls, v):
        cleaned = v.replace(' ', '').replace('-', '').replace('+', '')
        if not cleaned.isdigit():
            raise ValueError('Phone must contain only digits')
        if len(cleaned) < 10:
            raise ValueError('Phone must be at least 10 digits')
        return v
    
    @validator('date_of_birth')
    def validate_dob(cls, v):
        try:
            datetime.strptime(v, '%Y-%m-%d')
        except ValueError:
            raise ValueError('Date of birth must be in YYYY-MM-DD format')
        return v


class UserLogin(BaseModel):
    """User login schema"""
    email: EmailStr
    password: str = Field(..., max_length=72)


class AdminLogin(BaseModel):
    """Admin login schema"""
    email: EmailStr
    password: str = Field(..., max_length=72)


class ChangePassword(BaseModel):
    """Change password schema"""
    current_password: str = Field(..., max_length=72)
    new_password: str = Field(..., min_length=6, max_length=72)
    confirm_new_password: str = Field(..., min_length=6, max_length=72)
    
    @validator('confirm_new_password')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v


class UserResponse(BaseModel):
    """User response schema"""
    id: str
    email: EmailStr
    first_name: str
    last_name: str
    phone: str
    date_of_birth: str
    role: str
    wallet_balance: Optional[float] = None
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None


class TokenResponse(BaseModel):
    """Token response schema"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class RefreshTokenRequest(BaseModel):
    """Refresh token request schema"""
    refresh_token: str


# Schema for account deletion (requires password confirmation)
class DeleteAccountRequest(BaseModel):
    password: str
    confirmation: str  # Must type "DELETE" to confirm


