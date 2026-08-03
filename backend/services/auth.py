"""
Authentication service for LishFind Backend.

Handles user authentication, registration, password management, and JWT tokens.
"""

from datetime import datetime, timedelta
from typing import Optional, Tuple
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.exceptions import (
    AuthenticationException, 
    AuthorizationException, 
    ValidationException,
    UserNotFoundException
)
from core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token,
    generate_verification_token,
    generate_reset_token
)
from models.user import User, UserRole
from repositories.user import UserRepository
from schemas.requests.auth import (
    UserRegistrationRequest,
    UserLoginRequest,
    PasswordResetRequest,
    PasswordResetConfirmRequest,
    PasswordChangeRequest
)
from services.email import EmailService

logger = structlog.get_logger(__name__)


class AuthService:
    """Service for authentication operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)
        self.email_service = EmailService()
    
    async def register_user(self, registration_data: UserRegistrationRequest) -> User:
        """Register a new user."""
        
        # Check if email already exists
        if await self.user_repo.email_exists(registration_data.email):
            raise ValidationException("Email address is already registered")
        
        # Generate verification token
        verification_token = generate_verification_token()
        
        # Create user data
        user_data = {
            "email": registration_data.email.lower(),
            "hashed_password": get_password_hash(registration_data.password),
            "full_name": registration_data.full_name,
            "phone": registration_data.phone,
            "role": registration_data.role,
            "verification_token": verification_token,
            "is_verified": False,  # Email verification required
            "is_active": True
        }
        
        # Create user
        user = await self.user_repo.create_user(user_data)
        
        # Send verification email (don't fail registration if email fails)
        try:
            await self.email_service.send_verification_email(
                user.email, 
                user.full_name or "User", 
                verification_token
            )
            logger.info("Verification email sent", user_id=user.id, email=user.email)
        except Exception as e:
            logger.warning(
                "Failed to send verification email", 
                user_id=user.id,
                email=user.email,
                error=str(e)
            )
        
        logger.info(
            "User registered successfully", 
            user_id=user.id,
            email=user.email,
            role=user.role
        )
        
        return user
    
    async def authenticate_user(
        self, 
        login_data: UserLoginRequest
    ) -> Tuple[User, str, str]:
        """Authenticate user and return tokens."""
        
        # Get user by email
        user = await self.user_repo.get_user_by_email(login_data.email)
        if not user:
            raise AuthenticationException("Invalid email or password")
        
        # Verify password
        if not verify_password(login_data.password, user.hashed_password):
            logger.warning(
                "Failed login attempt - invalid password",
                email=login_data.email
            )
            raise AuthenticationException("Invalid email or password")
        
        # Check if user is active
        if not user.is_active:
            raise AuthenticationException("Account is deactivated")
        
        # Create tokens
        token_data = {"sub": str(user.id), "email": user.email, "role": user.role.value}
        
        # Adjust token expiration for "remember me"
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        
        if login_data.remember_me:
            # Extend token lifetime for "remember me"
            access_token_expires = timedelta(hours=24)  # 24 hours
            refresh_token_expires = timedelta(days=90)  # 90 days
        
        access_token = create_access_token(token_data, expires_delta=access_token_expires)
        refresh_token = create_refresh_token(token_data, expires_delta=refresh_token_expires)
        
        logger.info(
            "User authenticated successfully",
            user_id=user.id,
            email=user.email,
            remember_me=login_data.remember_me
        )
        
        return user, access_token, refresh_token
    
    async def verify_email(self, token: str) -> User:
        """Verify user email with token."""
        
        # Find user by verification token
        user = await self.user_repo.get_user_by_verification_token(token)
        if not user:
            raise ValidationException("Invalid or expired verification token")
        
        # Check if already verified
        if user.is_verified:
            raise ValidationException("Email is already verified")
        
        # Mark email as verified
        user = await self.user_repo.verify_email(user.id)
        
        logger.info("Email verified successfully", user_id=user.id, email=user.email)
        
        return user
    
    async def resend_verification_email(self, email: str) -> None:
        """Resend verification email to user."""
        
        # Get user by email
        user = await self.user_repo.get_user_by_email(email)
        if not user:
            raise UserNotFoundException("User not found")
        
        # Check if already verified
        if user.is_verified:
            raise ValidationException("Email is already verified")
        
        # Generate new verification token
        verification_token = generate_verification_token()
        await self.user_repo.set_verification_token(user.id, verification_token)
        
        # Send verification email
        await self.email_service.send_verification_email(
            user.email,
            user.full_name or "User",
            verification_token
        )
        
        logger.info(
            "Verification email resent", 
            user_id=user.id,
            email=user.email
        )
    
    async def initiate_password_reset(self, request: PasswordResetRequest) -> None:
        """Initiate password reset process."""
        
        # Get user by email
        user = await self.user_repo.get_user_by_email(request.email)
        if not user:
            # Don't reveal if email exists or not for security
            logger.warning(
                "Password reset requested for non-existent email",
                email=request.email
            )
            return
        
        # Check if user is active
        if not user.is_active:
            logger.warning(
                "Password reset requested for inactive user",
                email=request.email,
                user_id=user.id
            )
            return
        
        # Generate reset token
        reset_token = generate_reset_token()
        await self.user_repo.set_reset_token(user.id, reset_token)
        
        # Send reset email
        try:
            await self.email_service.send_password_reset_email(
                user.email,
                user.full_name or "User",
                reset_token
            )
            logger.info(
                "Password reset email sent",
                user_id=user.id,
                email=user.email
            )
        except Exception as e:
            logger.error(
                "Failed to send password reset email",
                user_id=user.id,
                email=user.email,
                error=str(e)
            )
            raise ValidationException("Failed to send password reset email")
    
    async def confirm_password_reset(self, request: PasswordResetConfirmRequest) -> None:
        """Confirm password reset with token and new password."""
        
        # Find user by reset token
        user = await self.user_repo.get_user_by_reset_token(request.token)
        if not user:
            raise ValidationException("Invalid or expired reset token")
        
        # Check if user is active
        if not user.is_active:
            raise AuthenticationException("Account is deactivated")
        
        # Update password
        new_password_hash = get_password_hash(request.new_password)
        await self.user_repo.update_password(user.id, new_password_hash)
        
        logger.info(
            "Password reset completed",
            user_id=user.id,
            email=user.email
        )
    
    async def change_password(
        self, 
        user_id: UUID, 
        request: PasswordChangeRequest
    ) -> None:
        """Change user password (requires current password)."""
        
        # Get user
        user = await self.user_repo.get_user_by_id(user_id)
        if not user:
            raise UserNotFoundException("User not found")
        
        # Verify current password
        if not verify_password(request.current_password, user.hashed_password):
            raise AuthenticationException("Current password is incorrect")
        
        # Update to new password
        new_password_hash = get_password_hash(request.new_password)
        await self.user_repo.update_password(user.id, new_password_hash)
        
        logger.info("Password changed successfully", user_id=user.id)
    
    async def refresh_access_token(self, refresh_token: str) -> str:
        """Create new access token from refresh token."""
        
        # Verify refresh token
        payload = verify_token(refresh_token, token_type="refresh")
        if not payload:
            raise AuthenticationException("Invalid or expired refresh token")
        
        # Get user to verify they still exist and are active
        user_id = UUID(payload["sub"])
        user = await self.user_repo.get_user_by_id(user_id)
        if not user or not user.is_active:
            raise AuthenticationException("User not found or inactive")
        
        # Create new access token
        token_data = {
            "sub": str(user.id), 
            "email": user.email, 
            "role": user.role.value
        }
        access_token = create_access_token(token_data)
        
        logger.debug("Access token refreshed", user_id=user.id)
        
        return access_token
    
    async def get_current_user(self, token: str) -> User:
        """Get current user from access token."""
        
        # Verify token
        payload = verify_token(token, token_type="access")
        if not payload:
            raise AuthenticationException("Invalid or expired access token")
        
        # Get user
        user_id = UUID(payload["sub"])
        user = await self.user_repo.get_user_by_id(user_id)
        if not user or not user.is_active:
            raise AuthenticationException("User not found or inactive")
        
        return user
    
    def check_user_permissions(
        self, 
        user: User, 
        required_role: UserRole = None,
        resource_owner_id: UUID = None
    ) -> None:
        """Check if user has required permissions."""
        
        # Check if user is active
        if not user.is_active:
            raise AuthorizationException("Account is deactivated")
        
        # Check role requirement
        if required_role:
            if user.role != required_role and user.role != UserRole.ADMIN:
                raise AuthorizationException(
                    f"Requires {required_role.value} role or admin access"
                )
        
        # Check resource ownership (user can access their own resources)
        if resource_owner_id:
            if user.id != resource_owner_id and user.role != UserRole.ADMIN:
                raise AuthorizationException(
                    "Access denied: insufficient permissions"
                )
    
    async def deactivate_user(self, user_id: UUID, current_user: User) -> None:
        """Deactivate a user account (admin only)."""
        
        # Check permissions (only admin can deactivate users)
        self.check_user_permissions(current_user, required_role=UserRole.ADMIN)
        
        # Cannot deactivate self
        if user_id == current_user.id:
            raise ValidationException("Cannot deactivate your own account")
        
        # Deactivate user
        await self.user_repo.deactivate_user(user_id)
        
        logger.info(
            "User deactivated by admin",
            target_user_id=user_id,
            admin_user_id=current_user.id
        )