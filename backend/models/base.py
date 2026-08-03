"""
Base model class for SQLAlchemy models.

Provides common fields and functionality for all database models.
"""

from __future__ import annotations
from datetime import datetime
from typing import Any, TYPE_CHECKING

from sqlalchemy import DateTime, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import DeclarativeBase, mapped_column

if TYPE_CHECKING:
    from sqlalchemy.orm import Mapped
else:
    from typing import Any as Mapped


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


class BaseModel(Base):
    """Base model with common fields for all entities."""
    
    __abstract__ = True
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    
    def to_dict(self) -> dict[str, Any]:
        """Convert model instance to dictionary."""
        return {
            column.key: getattr(self, column.key)
            for column in self.__table__.columns
        }