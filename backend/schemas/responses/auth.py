"""
Authentication response schemas for LishFind API.

Defines response models for authentication endpoints.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from models.user import UserRole


class UserResponse(BaseModel):
    """Response schema for user data."""
    
    id: UUID = Field(
        ...,
        description="User's unique identifier",
        example="123e4567-e89b-12d3-a456-426614174000"
    )
    email: str = Field(
        ...,
        description="User's email address",
        example="user@example.com"
    )
    full_name: Optional[str] = Field(
        None,
        description="User's full name",
        example="John Doe"
    )
    phone: Optional[str] = Field(
        None,
        description="User's phone number",
        example="+91-9876543210"
    )
    role: UserRole = Field(
        ...,
        description="User's role in the system",
        example="user"
    )
    is_active: bool = Field(
        ...,
        description="Whether the user account is active",
        example=True
    )
    is_verified: bool = Field(
        ...,
        description="Whether the user's email is verified",
        example=True
    )
    created_at: datetime = Field(
        ...,
        description="When the user account was created",
        example="2024-01-01T00:00:00Z"
    )
    
    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Response schema for authentication tokens."""
    
    access_token: str = Field(
        ...,
        description="JWT access token for authenticated requests",
        example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    )
    refresh_token: str = Field(
        ...,
        description="JWT refresh token for getting new access tokens",
        example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    )
    token_type: str = Field(
        "bearer",
        description="Token type (always 'bearer')",
        example="bearer"
    )
    expires_in: int = Field(
        ...,
        description="Token expiration time in seconds",
        example=1800
    )
    user: UserResponse = Field(
        ...,
        description="User information"
    )


class LoginResponse(TokenResponse):
    """Response schema for successful login."""
    pass


class RegistrationResponse(BaseModel):
    """Response schema for successful registration."""
    
    message: str = Field(
        ...,
        description="Success message",
        example="Registration successful. Please check your email for verification instructions."
    )
    user: UserResponse = Field(
        ...,
        description="Created user information"
    )


class LogoutResponse(BaseModel):
    """Response schema for logout."""
    
    message: str = Field(
        ...,
        description="Logout confirmation message",
        example="Successfully logged out"
    )


class PasswordResetResponse(BaseModel):
    """Response schema for password reset initiation."""
    
    message: str = Field(
        ...,
        description="Password reset confirmation message",
        example="Password reset instructions sent to your email"
    )


class PasswordResetConfirmResponse(BaseModel):
    """Response schema for password reset confirmation."""
    
    message: str = Field(
        ...,
        description="Password reset success message",
        example="Password has been reset successfully"
    )


class PasswordChangeResponse(BaseModel):
    """Response schema for password change."""
    
    message: str = Field(
        ...,
        description="Password change success message",
        example="Password changed successfully"
    )


class EmailVerificationResponse(BaseModel):
    """Response schema for email verification."""
    
    message: str = Field(
        ...,
        description="Email verification success message",
        example="Email verified successfully"
    )
    user: UserResponse = Field(
        ...,
        description="Updated user information"
    )


class RefreshTokenResponse(BaseModel):
    """Response schema for token refresh."""
    
    access_token: str = Field(
        ...,
        description="New JWT access token",
        example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    )
    token_type: str = Field(
        "bearer",
        description="Token type (always 'bearer')",
        example="bearer"
    )
    expires_in: int = Field(
        ...,
        description="Token expiration time in seconds",
        example=1800
    )


class ResendVerificationResponse(BaseModel):
    """Response schema for resending verification email."""
    
    message: str = Field(
        ...,
        description="Verification email resend confirmation",
        example="Verification email sent successfully"
    )