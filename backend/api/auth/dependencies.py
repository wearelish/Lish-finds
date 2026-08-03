"""
Authentication dependencies for FastAPI endpoints.

Provides dependency functions for authentication and authorization.
"""

from typing import Optional
from uuid import UUID

import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import AuthenticationException, AuthorizationException
from database.connection import get_db_session
from models.user import User, UserRole
from services.auth import AuthService

logger = structlog.get_logger(__name__)

# HTTP Bearer token scheme
security = HTTPBearer(auto_error=False)


async def get_auth_service(
    session: AsyncSession = Depends(get_db_session)
) -> AuthService:
    """Get authentication service instance."""
    return AuthService(session)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    auth_service: AuthService = Depends(get_auth_service)
) -> User:
    """Get current authenticated user from JWT token."""
    
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        user = await auth_service.get_current_user(credentials.credentials)
        return user
        
    except AuthenticationException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current active user (raises error if user is inactive)."""
    
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user account"
        )
    
    return current_user


async def get_current_verified_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """Get current verified user (raises error if email not verified)."""
    
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required"
        )
    
    return current_user


async def get_current_business_user(
    current_user: User = Depends(get_current_verified_user)
) -> User:
    """Get current business user (requires business role or admin)."""
    
    if current_user.role not in [UserRole.BUSINESS, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Business account required"
        )
    
    return current_user


async def get_current_business_owner(
    current_user: User = Depends(get_current_business_user)
) -> User:
    """Get current business owner (business user with ownership verification)."""
    
    # Additional checks could be added here to verify business ownership
    # For now, any business user is considered a potential business owner
    return current_user


async def get_current_admin_user(
    current_user: User = Depends(get_current_verified_user)
) -> User:
    """Get current admin user (requires admin role)."""
    
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access required"
        )
    
    return current_user


def require_user_role(required_role: UserRole):
    """Dependency factory for role-based access control."""
    
    async def _check_role(
        current_user: User = Depends(get_current_verified_user)
    ) -> User:
        """Check if user has required role or is admin."""
        
        if current_user.role != required_role and current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires {required_role.value} role or administrator access"
            )
        
        return current_user
    
    return _check_role


def require_resource_ownership(resource_owner_id_param: str = "user_id"):
    """Dependency factory for resource ownership check."""
    
    def _dependency(resource_owner_id: UUID, current_user: User = Depends(get_current_verified_user)) -> User:
        """Check if user owns the resource or is admin."""
        
        if current_user.id != resource_owner_id and current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: insufficient permissions"
            )
        
        return current_user
    
    # Set the parameter name for FastAPI dependency injection
    _dependency.__name__ = f"check_ownership_{resource_owner_id_param}"
    return _dependency


async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    auth_service: AuthService = Depends(get_auth_service)
) -> Optional[User]:
    """Get current user if authenticated, None otherwise (for optional auth)."""
    
    if not credentials:
        return None
    
    try:
        user = await auth_service.get_current_user(credentials.credentials)
        return user if user.is_active else None
        
    except AuthenticationException:
        # Invalid token - return None instead of raising error
        return None