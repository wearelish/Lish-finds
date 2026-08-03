"""
Review model for business reviews and ratings.

Supports review analysis for AI recommendation system.
"""

from __future__ import annotations
from enum import Enum
from typing import Dict, List, Optional, TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean, ForeignKey, Integer, String, Text, JSON, DECIMAL
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import mapped_column, relationship

if TYPE_CHECKING:
    from sqlalchemy.orm import Mapped
else:
    from typing import Any as Mapped

from models.base import BaseModel


class ReviewSource(str, Enum):
    """Source of the review."""
    LISHFIND = "lishfind"
    GOOGLE = "google"
    ZOMATO = "zomato"
    SWIGGY = "swiggy"
    IMPORTED = "imported"


class ReviewSentiment(str, Enum):
    """AI-analyzed sentiment of the review."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    MIXED = "mixed"


class Review(BaseModel):
    """Review model for business ratings and feedback."""
    
    __tablename__ = "reviews"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        nullable=False
    )
    
    # Review content
    rating: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Rating from 1 to 5"
    )
    title: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    content: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    
    # Review metadata
    source: Mapped[ReviewSource] = mapped_column(
        String(20),
        default=ReviewSource.LISHFIND,
        nullable=False,
        index=True
    )
    verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )
    helpful_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )
    
    # AI analysis
    sentiment: Mapped[Optional[ReviewSentiment]] = mapped_column(
        String(20),
        nullable=True,
        index=True
    )
    sentiment_score: Mapped[Optional[float]] = mapped_column(
        DECIMAL(3, 2),
        nullable=True,
        comment="Sentiment score from -1.00 to 1.00"
    )
    keywords: Mapped[Optional[List[str]]] = mapped_column(
        JSON,
        nullable=True,
        comment="AI-extracted keywords from review"
    )
    topics: Mapped[Optional[Dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="AI-identified topics and their scores"
    )
    
    # External review metadata (for imported reviews)
    external_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="ID from external platform"
    )
    external_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="URL to original review"
    )
    author_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Author name for external reviews"
    )
    
    # Relationships
    user_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
        index=True
    )
    user: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="reviews"
    )
    
    business_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("businesses.id"),
        nullable=False,
        index=True
    )
    business: Mapped["Business"] = relationship(
        "Business",
        back_populates="reviews"
    )
    
    def __repr__(self) -> str:
        return f"<Review(id={self.id}, business_id={self.business_id}, rating={self.rating})>"
    
    def is_positive(self) -> bool:
        """Check if review is positive (4-5 stars)."""
        return self.rating >= 4
    
    def is_negative(self) -> bool:
        """Check if review is negative (1-2 stars)."""
        return self.rating <= 2
    
    def get_display_name(self) -> str:
        """Get display name for the review author."""
        if self.user and self.user.full_name:
            return self.user.full_name
        elif self.author_name:
            return self.author_name
        else:
            return "Anonymous"


class SavedBusiness(BaseModel):
    """Model for user's saved/favorite businesses."""
    
    __tablename__ = "saved_businesses"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        nullable=False
    )
    
    # Relationships
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )
    user: Mapped["User"] = relationship(
        "User",
        back_populates="saved_businesses"
    )
    
    business_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("businesses.id"),
        nullable=False,
        index=True
    )
    business: Mapped["Business"] = relationship(
        "Business",
        back_populates="saved_by"
    )
    
    # Optional notes from user
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    
    def __repr__(self) -> str:
        return f"<SavedBusiness(user_id={self.user_id}, business_id={self.business_id})>"


class SearchHistory(BaseModel):
    """Model for tracking user search history and preferences."""
    
    __tablename__ = "search_history"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        nullable=False
    )
    
    # Search details
    query: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    intent_data: Mapped[Optional[Dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="AI-parsed intent from the search query"
    )
    results_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )
    
    # Location context
    search_location: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    
    # User relationship
    user_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
        index=True
    )
    user: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="search_history"
    )
    
    # Session tracking for anonymous users
    session_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True
    )
    
    def __repr__(self) -> str:
        return f"<SearchHistory(id={self.id}, query={self.query[:50]}...)>"