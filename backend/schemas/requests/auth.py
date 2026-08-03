"""
Authentication request schemas for LishFind API.

Defines request models for login, registration, password reset, etc.
"""

from typing import Optional

from pydantic import BaseModel, EmailStr, Field, validator

from models.user import UserRole


class UserRegistrationRequest(BaseModel):
    """Request schema for user registration."""
    
    email: EmailStr = Field(
        ...,
        description="User's email address",
        example="user@example.com"
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="Password (minimum 8 characters)",
        example="strongpassword123"
    )
    full_name: Optional[str] = Field(
        None,
        min_length=2,
        max_length=255,
        description="User's full name",
        example="John Doe"
    )
    phone: Optional[str] = Field(
        None,
        pattern=r"^\+?[1-9]\d{1,14}$",
        description="Phone number with country code",
        example="+91-9876543210"
    )
    role: UserRole = Field(
        UserRole.USER,
        description="User role (user, business, admin)",
        example="user"
    )
    
    @validator("password")
    def validate_password(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        
        # Check for at least one number and one letter
        has_letter = any(c.isalpha() for c in v)
        has_number = any(c.isdigit() for c in v)
        
        if not has_letter:
            raise ValueError("Password must contain at least one letter")
        if not has_number:
            raise ValueError("Password must contain at least one number")
        
        return v
    
    @validator("full_name")
    def validate_full_name(cls, v):
        """Validate full name."""
        if v and len(v.strip()) < 2:
            raise ValueError("Full name must be at least 2 characters long")
        return v.strip() if v else v


class UserLoginRequest(BaseModel):
    """Request schema for user login."""
    
    email: EmailStr = Field(
        ...,
        description="User's email address",
        example="user@example.com"
    )
    password: str = Field(
        ...,
        description="User's password",
        example="strongpassword123"
    )
    remember_me: bool = Field(
        False,
        description="Whether to remember the user for longer session",
        example=False
    )


class PasswordResetRequest(BaseModel):
    """Request schema for password reset initiation."""
    
    email: EmailStr = Field(
        ...,
        description="User's email address for password reset",
        example="user@example.com"
    )


class PasswordResetConfirmRequest(BaseModel):
    """Request schema for password reset confirmation."""
    
    token: str = Field(
        ...,
        description="Password reset token received via email",
        example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    )
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="New password (minimum 8 characters)",
        example="newstrongpassword123"
    )
    
    @validator("new_password")
    def validate_new_password(cls, v):
        """Validate new password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        
        has_letter = any(c.isalpha() for c in v)
        has_number = any(c.isdigit() for c in v)
        
        if not has_letter:
            raise ValueError("Password must contain at least one letter")
        if not has_number:
            raise ValueError("Password must contain at least one number")
        
        return v


class PasswordChangeRequest(BaseModel):
    """Request schema for changing password (authenticated user)."""
    
    current_password: str = Field(
        ...,
        description="Current password for verification",
        example="currentpassword123"
    )
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="New password (minimum 8 characters)",
        example="newstrongpassword123"
    )
    
    @validator("new_password")
    def validate_new_password(cls, v):
        """Validate new password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        
        has_letter = any(c.isalpha() for c in v)
        has_number = any(c.isdigit() for c in v)
        
        if not has_letter:
            raise ValueError("Password must contain at least one letter")
        if not has_number:
            raise ValueError("Password must contain at least one number")
        
        return v


class EmailVerificationRequest(BaseModel):
    """Request schema for email verification."""
    
    token: str = Field(
        ...,
        description="Email verification token",
        example="abc123def456ghi789"
    )


class RefreshTokenRequest(BaseModel):
    """Request schema for token refresh."""
    
    refresh_token: str = Field(
        ...,
        description="Refresh token to get new access token",
        example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    )


class ResendVerificationRequest(BaseModel):
    """Request schema for resending verification email."""
    
    email: EmailStr = Field(
        ...,
        description="User's email address",
        example="user@example.com"
    )