"""
User model for LishFind authentication and user management.

Supports different user roles: regular users, business owners, and administrators.
"""

from __future__ import annotations
from enum import Enum
from typing import List, Optional, TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Enum as SQLEnum, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import mapped_column, relationship

if TYPE_CHECKING:
    from sqlalchemy.orm import Mapped
else:
    from typing import Any as Mapped

from models.base import BaseModel


class UserRole(str, Enum):
    """User roles in the system."""
    USER = "user"
    BUSINESS = "business"  
    ADMIN = "admin"


class User(BaseModel):
    """User model for authentication and profile management."""
    
    __tablename__ = "users"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        nullable=False
    )
    
    # Authentication fields
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )
    
    # Profile fields
    full_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    phone: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True
    )
    
    # Role and permissions
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole),
        default=UserRole.USER,
        nullable=False
    )
    
    # Verification tokens
    verification_token: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    reset_password_token: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    
    # User preferences
    preferences: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="JSON string for user preferences"
    )
    
    # Relationships
    businesses: Mapped[List["Business"]] = relationship(
        "Business",
        back_populates="owner",
        cascade="all, delete-orphan"
    )
    
    reviews: Mapped[List["Review"]] = relationship(
        "Review",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    saved_businesses: Mapped[List["SavedBusiness"]] = relationship(
        "SavedBusiness",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    search_history: Mapped[List["SearchHistory"]] = relationship(
        "SearchHistory",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"
    
    def is_business_owner(self) -> bool:
        """Check if user is a business owner."""
        return self.role == UserRole.BUSINESS
    
    def is_admin(self) -> bool:
        """Check if user is an administrator."""
        return self.role == UserRole.ADMIN
    
    def can_manage_business(self, business_id: UUID) -> bool:
        """Check if user can manage a specific business."""
        if self.is_admin():
            return True
        
        if self.is_business_owner():
            return any(b.id == business_id for b in self.businesses)
        
        return False