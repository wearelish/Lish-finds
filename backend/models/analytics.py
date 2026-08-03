"""
Analytics models for business performance tracking and insights.

Tracks business metrics, search analytics, and user engagement.
"""

from __future__ import annotations
from datetime import date
from enum import Enum
from typing import Dict, Optional, TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    Date, ForeignKey, Integer, String, DECIMAL, JSON
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import mapped_column, relationship

if TYPE_CHECKING:
    from sqlalchemy.orm import Mapped
else:
    from typing import Any as Mapped

from models.base import BaseModel


class AnalyticsEvent(str, Enum):
    """Types of analytics events."""
    VIEW = "view"
    CLICK = "click"
    CALL = "call"
    DIRECTIONS = "directions"
    WEBSITE_VISIT = "website_visit"
    PHOTO_VIEW = "photo_view"
    REVIEW_READ = "review_read"
    SAVE = "save"
    SHARE = "share"


class BusinessAnalytics(BaseModel):
    """Daily analytics for business performance."""
    
    __tablename__ = "business_analytics"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        nullable=False
    )
    
    # Date for analytics
    date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True
    )
    
    # View metrics
    profile_views: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )
    search_appearances: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )
    photo_views: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )
    
    # Engagement metrics
    phone_clicks: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )
    direction_requests: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )
    website_clicks: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )
    saves: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )
    
    # Review metrics
    reviews_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )
    average_rating: Mapped[Optional[float]] = mapped_column(
        DECIMAL(3, 2),
        nullable=True
    )
    
    # Search metrics
    search_rank_avg: Mapped[Optional[float]] = mapped_column(
        DECIMAL(5, 2),
        nullable=True,
        comment="Average search ranking position"
    )
    search_keywords: Mapped[Optional[Dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="Keywords that led to this business"
    )
    
    # Relationship
    business_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("businesses.id"),
        nullable=False,
        index=True
    )
    business: Mapped["Business"] = relationship(
        "Business",
        back_populates="analytics"
    )
    
    def __repr__(self) -> str:
        return f"<BusinessAnalytics(business_id={self.business_id}, date={self.date})>"
    
    def calculate_engagement_rate(self) -> float:
        """Calculate engagement rate based on views and actions."""
        if self.profile_views == 0:
            return 0.0
        
        total_actions = (
            self.phone_clicks + 
            self.direction_requests + 
            self.website_clicks + 
            self.saves
        )
        
        return (total_actions / self.profile_views) * 100


class SearchAnalytics(BaseModel):
    """Analytics for search queries and results."""
    
    __tablename__ = "search_analytics"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        nullable=False
    )
    
    # Date for analytics
    date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True
    )
    
    # Search query details
    query_text: Mapped[str] = mapped_column(
        String(500),
        nullable=False
    )
    query_category: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True
    )
    query_intent: Mapped[Optional[Dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="Parsed intent data"
    )
    
    # Search performance
    results_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )
    avg_response_time_ms: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True
    )
    
    # User engagement with results
    clicks_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )
    click_through_rate: Mapped[Optional[float]] = mapped_column(
        DECIMAL(5, 2),
        nullable=True
    )
    
    # Geographic data
    search_location: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    
    # Search source
    search_source: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="web, mobile_app, api, etc."
    )
    
    def __repr__(self) -> str:
        return f"<SearchAnalytics(date={self.date}, query={self.query_text[:50]})>"


class UserEngagement(BaseModel):
    """Track user engagement events for analytics."""
    
    __tablename__ = "user_engagement"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        nullable=False
    )
    
    # Event details
    event_type: Mapped[AnalyticsEvent] = mapped_column(
        String(50),
        nullable=False,
        index=True
    )
    event_data: Mapped[Optional[Dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="Additional event metadata"
    )
    
    # User context
    user_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
        index=True
    )
    session_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True
    )
    
    # Business context
    business_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("businesses.id"),
        nullable=True,
        index=True
    )
    
    # Technical context
    user_agent: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True
    )
    ip_address: Mapped[Optional[str]] = mapped_column(
        String(45),
        nullable=True
    )
    referrer: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True
    )
    
    def __repr__(self) -> str:
        return f"<UserEngagement(event_type={self.event_type}, business_id={self.business_id})>"