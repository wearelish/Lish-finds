"""
Business model for LishFind business listings and management.

Supports geospatial queries using PostGIS for location-based search.
"""

from __future__ import annotations
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, TYPE_CHECKING
from uuid import UUID, uuid4

from geoalchemy2 import Geography
from sqlalchemy import (
    ARRAY, Boolean, DECIMAL, ForeignKey, Integer, String, Text, JSON
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import mapped_column, relationship

if TYPE_CHECKING:
    from sqlalchemy.orm import Mapped
else:
    from typing import Any as Mapped

from models.base import BaseModel


class BusinessStatus(str, Enum):
    """Business verification and status."""
    PENDING = "pending"
    VERIFIED = "verified"
    SUSPENDED = "suspended"
    CLOSED = "closed"


class PriceRange(str, Enum):
    """Price range categories."""
    BUDGET = "budget"        # Under ₹500
    MODERATE = "moderate"    # ₹500 - ₹1500
    EXPENSIVE = "expensive"  # ₹1500 - ₹3000
    LUXURY = "luxury"        # Above ₹3000


class Business(BaseModel):
    """Business model for listings in LishFind."""
    
    __tablename__ = "businesses"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        nullable=False
    )
    
    # Basic information
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    category: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True
    )
    subcategory: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )
    
    # Location (PostGIS geography)
    location: Mapped[Optional[str]] = mapped_column(
        Geography("POINT", srid=4326),
        nullable=True,
        index=True
    )
    latitude: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(10, 8),
        nullable=True
    )
    longitude: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(11, 8),
        nullable=True
    )
    
    # Address information
    address: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    city: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True
    )
    state: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )
    postal_code: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True
    )
    country: Mapped[str] = mapped_column(
        String(100),
        default="India",
        nullable=False
    )
    
    # Contact information
    phone: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True
    )
    email: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    website: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True
    )
    
    # Social media
    instagram: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    facebook: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    whatsapp: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True
    )
    
    # Business details
    opening_hours: Mapped[Optional[Dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="JSON object with opening hours for each day"
    )
    services: Mapped[Optional[List[str]]] = mapped_column(
        ARRAY(String),
        nullable=True
    )
    amenities: Mapped[Optional[List[str]]] = mapped_column(
        ARRAY(String),
        nullable=True
    )
    price_range: Mapped[Optional[PriceRange]] = mapped_column(
        String(20),
        nullable=True
    )
    
    # Media
    photos: Mapped[Optional[List[str]]] = mapped_column(
        ARRAY(String),
        nullable=True,
        comment="Array of photo URLs"
    )
    logo_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True
    )
    
    # Status and verification
    status: Mapped[BusinessStatus] = mapped_column(
        String(20),
        default=BusinessStatus.PENDING,
        nullable=False,
        index=True
    )
    verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True
    )
    claimed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )
    
    # Ratings and popularity
    rating: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(3, 2),
        nullable=True,
        comment="Average rating (0.00 to 5.00)"
    )
    review_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )
    popularity_score: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(5, 2),
        nullable=True,
        comment="Calculated popularity score for ranking"
    )
    
    # SEO and search
    slug: Mapped[Optional[str]] = mapped_column(
        String(255),
        unique=True,
        nullable=True,
        index=True
    )
    keywords: Mapped[Optional[List[str]]] = mapped_column(
        ARRAY(String),
        nullable=True,
        comment="Keywords for search optimization"
    )
    
    # Relationships
    owner_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
        index=True
    )
    owner: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="businesses"
    )
    
    reviews: Mapped[List["Review"]] = relationship(
        "Review",
        back_populates="business",
        cascade="all, delete-orphan"
    )
    
    saved_by: Mapped[List["SavedBusiness"]] = relationship(
        "SavedBusiness",
        back_populates="business",
        cascade="all, delete-orphan"
    )
    
    analytics: Mapped[List["BusinessAnalytics"]] = relationship(
        "BusinessAnalytics",
        back_populates="business",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<Business(id={self.id}, name={self.name}, category={self.category})>"
    
    def is_open_now(self) -> bool:
        """Check if business is currently open based on opening hours."""
        from datetime import datetime
        import pytz
        
        if not self.opening_hours:
            return True  # Assume open if no hours specified
        
        # Get current time in Indian timezone
        ist = pytz.timezone('Asia/Kolkata')
        now = datetime.now(ist)
        current_day = now.strftime('%A').lower()
        current_time = now.strftime('%H:%M')
        
        day_hours = self.opening_hours.get(current_day)
        if not day_hours:
            return False
        
        # Handle closed days
        if day_hours.get('closed', False):
            return False
        
        # Check if current time is within opening hours
        open_time = day_hours.get('open')
        close_time = day_hours.get('close')
        
        if open_time and close_time:
            return open_time <= current_time <= close_time
        
        return True
    
    def calculate_completeness(self) -> float:
        """Calculate business profile completeness percentage."""
        total_fields = 15
        completed_fields = 0
        
        # Check required fields
        if self.name:
            completed_fields += 1
        if self.description:
            completed_fields += 1
        if self.category:
            completed_fields += 1
        if self.location:
            completed_fields += 1
        if self.address:
            completed_fields += 1
        if self.phone:
            completed_fields += 1
        if self.opening_hours:
            completed_fields += 1
        if self.photos:
            completed_fields += 1
        if self.services:
            completed_fields += 1
        if self.price_range:
            completed_fields += 1
        if self.website:
            completed_fields += 1
        if self.email:
            completed_fields += 1
        if self.instagram or self.facebook:
            completed_fields += 1
        if self.amenities:
            completed_fields += 1
        if self.logo_url:
            completed_fields += 1
        
        return (completed_fields / total_fields) * 100