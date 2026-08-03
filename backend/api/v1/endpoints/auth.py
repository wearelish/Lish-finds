"""
Authentication endpoints for LishFind API.

Provides endpoints for user registration, login, password management, and email verification.
"""

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.dependencies import (
    get_auth_service, 
    get_current_user, 
    get_current_active_user
)
from core.config import settings
from core.exceptions import (
    AuthenticationException,
    ValidationException,
    UserNotFoundException
)
from database.connection import get_db_session
from schemas.requests.auth import (
    UserRegistrationRequest,
    UserLoginRequest,
    PasswordResetRequest,
    PasswordResetConfirmRequest,
    PasswordChangeRequest,
    EmailVerificationRequest,
    RefreshTokenRequest,
    ResendVerificationRequest
)
from schemas.responses.auth import (
    RegistrationResponse,
    LoginResponse,
    LogoutResponse,
    PasswordResetResponse,
    PasswordResetConfirmResponse,
    PasswordChangeResponse,
    EmailVerificationResponse,
    RefreshTokenResponse,
    ResendVerificationResponse,
    UserResponse
)
from services.auth import AuthService
from services.email import EmailService

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.post(
    "/register",
    response_model=RegistrationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new user",
    description="Register a new user account. Email verification will be required.",
)
async def register(
    registration_data: UserRegistrationRequest,
    auth_service: AuthService = Depends(get_auth_service)
) -> RegistrationResponse:
    """Register a new user account."""
    
    try:
        user = await auth_service.register_user(registration_data)
        
        return RegistrationResponse(
            message="Registration successful. Please check your email for verification instructions.",
            user=UserResponse.model_validate(user)
        )
        
    except ValidationException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="User login",
    description="Authenticate user and receive access and refresh tokens.",
)
async def login(
    login_data: UserLoginRequest,
    auth_service: AuthService = Depends(get_auth_service)
) -> LoginResponse:
    """Authenticate user and return tokens."""
    
    try:
        user, access_token, refresh_token = await auth_service.authenticate_user(login_data)
        
        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=UserResponse.model_validate(user)
        )
        
    except AuthenticationException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"}
        )


@router.post(
    "/logout",
    response_model=LogoutResponse,
    summary="User logout",
    description="Logout current user (client should discard tokens).",
)
async def logout(
    current_user = Depends(get_current_user)
) -> LogoutResponse:
    """Logout user (tokens should be discarded on client side)."""
    
    # Note: With JWT tokens, we can't invalidate them server-side easily
    # The client should discard the tokens
    # In a production system, you might want to maintain a blacklist of tokens
    
    logger.info("User logged out", user_id=current_user.id)
    
    return LogoutResponse(
        message="Successfully logged out"
    )


@router.post(
    "/refresh",
    response_model=RefreshTokenResponse,
    summary="Refresh access token",
    description="Get a new access token using a refresh token.",
)
async def refresh_token(
    refresh_request: RefreshTokenRequest,
    auth_service: AuthService = Depends(get_auth_service)
) -> RefreshTokenResponse:
    """Refresh access token using refresh token."""
    
    try:
        access_token = await auth_service.refresh_access_token(
            refresh_request.refresh_token
        )
        
        return RefreshTokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        
    except AuthenticationException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )


@router.post(
    "/verify-email",
    response_model=EmailVerificationResponse,
    summary="Verify email address",
    description="Verify user email address using verification token.",
)
async def verify_email(
    verification_data: EmailVerificationRequest,
    auth_service: AuthService = Depends(get_auth_service)
) -> EmailVerificationResponse:
    """Verify user email address."""
    
    try:
        user = await auth_service.verify_email(verification_data.token)
        
        # Send welcome email after verification
        email_service = EmailService()
        if user.role.value == "business":
            await email_service.send_business_welcome_email(
                user.email,
                user.full_name or "Business Owner"
            )
        else:
            await email_service.send_welcome_email(
                user.email,
                user.full_name or "User"
            )
        
        return EmailVerificationResponse(
            message="Email verified successfully",
            user=UserResponse.model_validate(user)
        )
        
    except ValidationException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post(
    "/resend-verification",
    response_model=ResendVerificationResponse,
    summary="Resend verification email",
    description="Resend email verification to user.",
)
async def resend_verification(
    resend_data: ResendVerificationRequest,
    auth_service: AuthService = Depends(get_auth_service)
) -> ResendVerificationResponse:
    """Resend email verification."""
    
    try:
        await auth_service.resend_verification_email(resend_data.email)
        
        return ResendVerificationResponse(
            message="Verification email sent successfully"
        )
        
    except (UserNotFoundException, ValidationException) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post(
    "/reset-password",
    response_model=PasswordResetResponse,
    summary="Request password reset",
    description="Request password reset email for user account.",
)
async def request_password_reset(
    reset_request: PasswordResetRequest,
    auth_service: AuthService = Depends(get_auth_service)
) -> PasswordResetResponse:
    """Request password reset email."""
    
    try:
        await auth_service.initiate_password_reset(reset_request)
        
        return PasswordResetResponse(
            message="Password reset instructions sent to your email"
        )
        
    except Exception:
        # Always return success message to prevent email enumeration
        return PasswordResetResponse(
            message="Password reset instructions sent to your email"
        )


@router.post(
    "/reset-password/confirm",
    response_model=PasswordResetConfirmResponse,
    summary="Confirm password reset",
    description="Reset password using reset token and new password.",
)
async def confirm_password_reset(
    reset_data: PasswordResetConfirmRequest,
    auth_service: AuthService = Depends(get_auth_service)
) -> PasswordResetConfirmResponse:
    """Confirm password reset with token."""
    
    try:
        await auth_service.confirm_password_reset(reset_data)
        
        return PasswordResetConfirmResponse(
            message="Password has been reset successfully"
        )
        
    except ValidationException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post(
    "/change-password",
    response_model=PasswordChangeResponse,
    summary="Change password",
    description="Change password for authenticated user (requires current password).",
)
async def change_password(
    password_data: PasswordChangeRequest,
    current_user = Depends(get_current_active_user),
    auth_service: AuthService = Depends(get_auth_service)
) -> PasswordChangeResponse:
    """Change user password."""
    
    try:
        await auth_service.change_password(current_user.id, password_data)
        
        return PasswordChangeResponse(
            message="Password changed successfully"
        )
        
    except AuthenticationException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user",
    description="Get information about the currently authenticated user.",
)
async def get_current_user_info(
    current_user = Depends(get_current_user)
) -> UserResponse:
    """Get current user information."""
    
    return UserResponse.model_validate(current_user)


@router.get(
    "/profile",
    response_model=UserResponse,
    summary="Get user profile",
    description="Get detailed user profile (verified users only).",
)
async def get_user_profile(
    current_user = Depends(get_current_active_user)
) -> UserResponse:
    """Get detailed user profile."""
    
    return UserResponse.model_validate(current_user)