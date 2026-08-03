"""
User repository for database operations.

Implements the repository pattern for user-related database operations.
Enhanced with query profiling and performance monitoring.
"""

from typing import List, Optional
from uuid import UUID

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.exceptions import UserNotFoundException, DatabaseException
from models.user import User, UserRole
from database.performance import profile_query

logger = structlog.get_logger(__name__)


class UserRepository:
    """Repository for user database operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    @profile_query("create_user")
    async def create_user(self, user_data: dict) -> User:
        """Create a new user in the database."""
        try:
            user = User(**user_data)
            self.session.add(user)
            await self.session.commit()
            await self.session.refresh(user)
            
            logger.info(
                "User created successfully",
                user_id=user.id,
                email=user.email,
                role=user.role
            )
            
            return user
            
        except Exception as e:
            await self.session.rollback()
            logger.error(
                "Failed to create user",
                error=str(e),
                email=user_data.get("email"),
                exc_info=True
            )
            raise DatabaseException(f"Failed to create user: {str(e)}")
    
    @profile_query("get_user_by_id")
    async def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        """Get user by ID."""
        try:
            stmt = select(User).where(User.id == user_id)
            result = await self.session.execute(stmt)
            user = result.scalar_one_or_none()
            
            if user:
                logger.debug("User retrieved by ID", user_id=user_id)
            
            return user
            
        except Exception as e:
            logger.error(
                "Failed to get user by ID",
                user_id=user_id,
                error=str(e),
                exc_info=True
            )
            raise DatabaseException(f"Failed to retrieve user: {str(e)}")
    
    @profile_query("get_user_by_email")
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email address."""
        try:
            stmt = select(User).where(User.email == email.lower())
            result = await self.session.execute(stmt)
            user = result.scalar_one_or_none()
            
            if user:
                logger.debug("User retrieved by email", email=email)
            
            return user
            
        except Exception as e:
            logger.error(
                "Failed to get user by email",
                email=email,
                error=str(e),
                exc_info=True
            )
            raise DatabaseException(f"Failed to retrieve user: {str(e)}")
    
    async def get_user_by_verification_token(self, token: str) -> Optional[User]:
        """Get user by verification token."""
        try:
            stmt = select(User).where(User.verification_token == token)
            result = await self.session.execute(stmt)
            user = result.scalar_one_or_none()
            
            return user
            
        except Exception as e:
            logger.error(
                "Failed to get user by verification token",
                error=str(e),
                exc_info=True
            )
            raise DatabaseException(f"Failed to retrieve user: {str(e)}")
    
    async def get_user_by_reset_token(self, token: str) -> Optional[User]:
        """Get user by password reset token."""
        try:
            stmt = select(User).where(User.reset_password_token == token)
            result = await self.session.execute(stmt)
            user = result.scalar_one_or_none()
            
            return user
            
        except Exception as e:
            logger.error(
                "Failed to get user by reset token",
                error=str(e),
                exc_info=True
            )
            raise DatabaseException(f"Failed to retrieve user: {str(e)}")
    
    async def update_user(self, user_id: UUID, user_data: dict) -> User:
        """Update user information."""
        try:
            # Check if user exists
            user = await self.get_user_by_id(user_id)
            if not user:
                raise UserNotFoundException("User not found")
            
            # Update user data
            stmt = (
                update(User)
                .where(User.id == user_id)
                .values(**user_data)
                .returning(User)
            )
            
            result = await self.session.execute(stmt)
            updated_user = result.scalar_one()
            await self.session.commit()
            
            logger.info(
                "User updated successfully",
                user_id=user_id,
                updated_fields=list(user_data.keys())
            )
            
            return updated_user
            
        except UserNotFoundException:
            raise
        except Exception as e:
            await self.session.rollback()
            logger.error(
                "Failed to update user",
                user_id=user_id,
                error=str(e),
                exc_info=True
            )
            raise DatabaseException(f"Failed to update user: {str(e)}")
    
    async def verify_email(self, user_id: UUID) -> User:
        """Mark user email as verified."""
        return await self.update_user(
            user_id,
            {
                "is_verified": True,
                "verification_token": None
            }
        )
    
    async def set_verification_token(self, user_id: UUID, token: str) -> User:
        """Set email verification token for user."""
        return await self.update_user(user_id, {"verification_token": token})
    
    async def set_reset_token(self, user_id: UUID, token: str) -> User:
        """Set password reset token for user."""
        return await self.update_user(user_id, {"reset_password_token": token})
    
    async def update_password(self, user_id: UUID, hashed_password: str) -> User:
        """Update user password and clear reset token."""
        return await self.update_user(
            user_id,
            {
                "hashed_password": hashed_password,
                "reset_password_token": None
            }
        )
    
    async def deactivate_user(self, user_id: UUID) -> User:
        """Deactivate user account."""
        return await self.update_user(user_id, {"is_active": False})
    
    async def activate_user(self, user_id: UUID) -> User:
        """Activate user account."""
        return await self.update_user(user_id, {"is_active": True})
    
    async def get_users_by_role(self, role: UserRole, limit: int = 100) -> List[User]:
        """Get users by role with optional limit."""
        try:
            stmt = (
                select(User)
                .where(User.role == role)
                .limit(limit)
            )
            result = await self.session.execute(stmt)
            users = result.scalars().all()
            
            return list(users)
            
        except Exception as e:
            logger.error(
                "Failed to get users by role",
                role=role,
                error=str(e),
                exc_info=True
            )
            raise DatabaseException(f"Failed to retrieve users: {str(e)}")
    
    async def get_user_with_businesses(self, user_id: UUID) -> Optional[User]:
        """Get user with their businesses loaded."""
        try:
            stmt = (
                select(User)
                .options(selectinload(User.businesses))
                .where(User.id == user_id)
            )
            result = await self.session.execute(stmt)
            user = result.scalar_one_or_none()
            
            return user
            
        except Exception as e:
            logger.error(
                "Failed to get user with businesses",
                user_id=user_id,
                error=str(e),
                exc_info=True
            )
            raise DatabaseException(f"Failed to retrieve user: {str(e)}")
    
    async def email_exists(self, email: str) -> bool:
        """Check if email already exists in the database."""
        try:
            stmt = select(User.id).where(User.email == email.lower())
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none() is not None
            
        except Exception as e:
            logger.error(
                "Failed to check email existence",
                email=email,
                error=str(e),
                exc_info=True
            )
            raise DatabaseException(f"Failed to check email: {str(e)}")
    
    async def delete_user(self, user_id: UUID) -> bool:
        """Delete user from database (soft delete - deactivate instead)."""
        try:
            # We don't actually delete users, just deactivate them
            await self.deactivate_user(user_id)
            
            logger.info("User deactivated (soft delete)", user_id=user_id)
            return True
            
        except UserNotFoundException:
            return False
        except Exception as e:
            logger.error(
                "Failed to delete user",
                user_id=user_id,
                error=str(e),
                exc_info=True
            )
            raise DatabaseException(f"Failed to delete user: {str(e)}")