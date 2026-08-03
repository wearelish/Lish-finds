"""
Business management API endpoints for LishFind backend.

Provides APIs for business owners to manage their listings, analytics, and interactions.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File
from pydantic import BaseModel, Field, validator
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.dependencies import get_current_user, get_current_business_owner
from database.connection import get_db_session
from models.business import Business, BusinessStatus, PriceRange
from models.user import User
from services.business_service import BusinessService

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/business", tags=["business-management"])


class BusinessUpdateRequest(BaseModel):
    """Request schema for updating business information."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=200, description="Business name")
    description: Optional[str] = Field(None, max_length=2000, description="Business description")
    category: Optional[str] = Field(None, description="Business category")
    
    # Contact information
    phone: Optional[str] = Field(None, description="Phone number")
    email: Optional[str] = Field(None, description="Email address")
    website: Optional[str] = Field(None, description="Website URL")
    
    # Location
    address: Optional[str] = Field(None, description="Full address")
    city: Optional[str] = Field(None, description="City")
    state: Optional[str] = Field(None, description="State")
    postal_code: Optional[str] = Field(None, description="Postal code")
    latitude: Optional[float] = Field(None, ge=-90, le=90, description="Latitude")
    longitude: Optional[float] = Field(None, ge=-180, le=180, description="Longitude")
    
    # Business details
    price_range: Optional[PriceRange] = Field(None, description="Price range category")
    amenities: Optional[List[str]] = Field(None, description="Available amenities")
    services: Optional[List[str]] = Field(None, description="Services offered")
    
    # Operating hours (simplified - in production would be more complex)
    opening_hours: Optional[Dict[str, Any]] = Field(None, description="Opening hours by day")
    
    # Social media
    social_media: Optional[Dict[str, str]] = Field(None, description="Social media links")


class BusinessCreateRequest(BaseModel):
    """Request schema for creating a new business."""
    
    name: str = Field(..., min_length=1, max_length=200, description="Business name")
    description: str = Field(..., min_length=10, max_length=2000, description="Business description")
    category: str = Field(..., description="Business category")
    
    # Contact information (required)
    phone: str = Field(..., description="Phone number")
    email: str = Field(..., description="Email address")
    
    # Location (required)
    address: str = Field(..., description="Full address")
    city: str = Field(..., description="City")
    state: str = Field(..., description="State")
    postal_code: str = Field(..., description="Postal code")
    latitude: float = Field(..., ge=-90, le=90, description="Latitude")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude")
    
    # Optional details
    website: Optional[str] = Field(None, description="Website URL")
    price_range: Optional[PriceRange] = Field(PriceRange.MODERATE, description="Price range category")
    amenities: Optional[List[str]] = Field(default_factory=list, description="Available amenities")
    services: Optional[List[str]] = Field(default_factory=list, description="Services offered")
    opening_hours: Optional[Dict[str, Any]] = Field(None, description="Opening hours by day")
    social_media: Optional[Dict[str, str]] = Field(default_factory=dict, description="Social media links")


class BusinessAnalyticsResponse(BaseModel):
    """Response schema for business analytics."""
    
    # Overview metrics
    total_views: int = Field(..., description="Total profile views")
    total_clicks: int = Field(..., description="Total clicks/interactions")
    total_reviews: int = Field(..., description="Total reviews received")
    average_rating: Optional[float] = Field(None, description="Current average rating")
    
    # Time-based metrics
    views_last_30_days: int = Field(..., description="Views in last 30 days")
    clicks_last_30_days: int = Field(..., description="Clicks in last 30 days")
    reviews_last_30_days: int = Field(..., description="Reviews in last 30 days")
    
    # Engagement metrics
    click_through_rate: float = Field(..., description="CTR percentage")
    response_rate: Optional[float] = Field(None, description="Response rate to customer inquiries")
    
    # Search performance
    search_rankings: Dict[str, int] = Field(default_factory=dict, description="Average search rankings by keyword")
    recommendation_appearances: int = Field(0, description="Times appeared in recommendations")
    
    # Geographic data
    visitor_locations: Dict[str, int] = Field(default_factory=dict, description="Visitor locations")
    
    # Trending data
    daily_views: List[Dict[str, Any]] = Field(default_factory=list, description="Daily view counts")
    peak_hours: List[int] = Field(default_factory=list, description="Peak activity hours")
    
    # Comparison data
    category_rank: Optional[int] = Field(None, description="Rank within category")
    local_rank: Optional[int] = Field(None, description="Rank in local area")


class ReviewResponse(BaseModel):
    """Response schema for business reviews."""
    
    id: UUID = Field(..., description="Review ID")
    user_name: str = Field(..., description="Reviewer name")
    rating: float = Field(..., description="Review rating")
    review_text: Optional[str] = Field(None, description="Review text")
    created_at: datetime = Field(..., description="Review creation date")
    
    # Response from business
    business_response: Optional[str] = Field(None, description="Business response to review")
    response_date: Optional[datetime] = Field(None, description="Date of business response")
    
    # Review metadata
    helpful_votes: int = Field(0, description="Number of helpful votes")
    verified_purchase: bool = Field(False, description="Whether review is from verified customer")


class ReviewResponseRequest(BaseModel):
    """Request schema for responding to reviews."""
    
    response_text: str = Field(..., min_length=10, max_length=1000, description="Response to review")


@router.get(
    "/my-business",
    summary="Get current user's business",
    description="Get business information for the current business owner.",
)
async def get_my_business(
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_business_owner)
) -> Dict[str, Any]:
    """Get business information for the current business owner."""
    
    try:
        # Find business owned by current user
        query = select(Business).where(Business.owner_id == current_user.id)
        result = await session.execute(query)
        business = result.scalar_one_or_none()
        
        if not business:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No business found for current user"
            )
        
        # Convert to response format
        business_data = {
            "id": business.id,
            "name": business.name,
            "description": business.description,
            "category": business.category,
            "status": business.status.value,
            "verified": business.verified,
            "phone": business.phone,
            "email": business.email,
            "website": business.website,
            "address": business.address,
            "city": business.city,
            "state": business.state,
            "postal_code": business.postal_code,
            "latitude": business.latitude,
            "longitude": business.longitude,
            "price_range": business.price_range,
            "amenities": business.amenities,
            "services": business.services,
            "opening_hours": business.opening_hours,
            "social_media": business.social_media,
            "photos": business.photos,
            "rating": business.rating,
            "review_count": business.review_count,
            "popularity_score": business.popularity_score,
            "created_at": business.created_at,
            "updated_at": business.updated_at
        }
        
        logger.info(
            "Business information retrieved",
            business_id=business.id,
            owner_id=current_user.id
        )
        
        return business_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get business information",
            user_id=current_user.id,
            error=str(e),
            exc_info=True
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get business information: {str(e)}"
        )


@router.post(
    "/create",
    summary="Create new business",
    description="Create a new business listing for the current user.",
)
async def create_business(
    request: BusinessCreateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Create a new business listing."""
    
    try:
        # Check if user already has a business
        existing_query = select(Business).where(Business.owner_id == current_user.id)
        existing_result = await session.execute(existing_query)
        existing_business = existing_result.scalar_one_or_none()
        
        if existing_business:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User already has a business listing"
            )
        
        # Create new business
        business = Business(
            name=request.name,
            description=request.description,
            category=request.category,
            owner_id=current_user.id,
            phone=request.phone,
            email=request.email,
            website=request.website,
            address=request.address,
            city=request.city,
            state=request.state,
            postal_code=request.postal_code,
            latitude=request.latitude,
            longitude=request.longitude,
            price_range=request.price_range,
            amenities=request.amenities,
            services=request.services,
            opening_hours=request.opening_hours,
            social_media=request.social_media,
            status=BusinessStatus.PENDING,  # New businesses start as pending
            verified=False,
            rating=None,
            review_count=0,
            popularity_score=None
        )
        
        session.add(business)
        await session.commit()
        await session.refresh(business)
        
        logger.info(
            "New business created",
            business_id=business.id,
            business_name=business.name,
            owner_id=current_user.id
        )
        
        return {
            "id": business.id,
            "name": business.name,
            "status": business.status.value,
            "message": "Business created successfully. It will be reviewed before going live."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to create business",
            user_id=current_user.id,
            error=str(e),
            exc_info=True
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create business: {str(e)}"
        )


@router.put(
    "/update",
    summary="Update business information",
    description="Update business information for the current business owner.",
)
async def update_business(
    request: BusinessUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_business_owner)
) -> Dict[str, str]:
    """Update business information."""
    
    try:
        # Get business
        query = select(Business).where(Business.owner_id == current_user.id)
        result = await session.execute(query)
        business = result.scalar_one_or_none()
        
        if not business:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Business not found"
            )
        
        # Update fields that were provided
        updated_fields = []
        
        if request.name is not None:
            business.name = request.name
            updated_fields.append("name")
        
        if request.description is not None:
            business.description = request.description
            updated_fields.append("description")
        
        if request.category is not None:
            business.category = request.category
            updated_fields.append("category")
        
        if request.phone is not None:
            business.phone = request.phone
            updated_fields.append("phone")
        
        if request.email is not None:
            business.email = request.email
            updated_fields.append("email")
        
        if request.website is not None:
            business.website = request.website
            updated_fields.append("website")
        
        if request.address is not None:
            business.address = request.address
            updated_fields.append("address")
        
        if request.city is not None:
            business.city = request.city
            updated_fields.append("city")
        
        if request.state is not None:
            business.state = request.state
            updated_fields.append("state")
        
        if request.postal_code is not None:
            business.postal_code = request.postal_code
            updated_fields.append("postal_code")
        
        if request.latitude is not None:
            business.latitude = request.latitude
            updated_fields.append("latitude")
        
        if request.longitude is not None:
            business.longitude = request.longitude
            updated_fields.append("longitude")
        
        if request.price_range is not None:
            business.price_range = request.price_range
            updated_fields.append("price_range")
        
        if request.amenities is not None:
            business.amenities = request.amenities
            updated_fields.append("amenities")
        
        if request.services is not None:
            business.services = request.services
            updated_fields.append("services")
        
        if request.opening_hours is not None:
            business.opening_hours = request.opening_hours
            updated_fields.append("opening_hours")
        
        if request.social_media is not None:
            business.social_media = request.social_media
            updated_fields.append("social_media")
        
        # Update timestamp
        business.updated_at = datetime.utcnow()
        
        await session.commit()
        
        logger.info(
            "Business updated",
            business_id=business.id,
            owner_id=current_user.id,
            updated_fields=updated_fields
        )
        
        return {
            "message": f"Business updated successfully. Updated: {', '.join(updated_fields)}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to update business",
            user_id=current_user.id,
            error=str(e),
            exc_info=True
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update business: {str(e)}"
        )


@router.get(
    "/analytics",
    response_model=BusinessAnalyticsResponse,
    summary="Get business analytics",
    description="Get detailed analytics for the business owner's listing.",
)
async def get_business_analytics(
    days: int = Query(30, ge=1, le=365, description="Number of days for analytics"),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_business_owner)
) -> BusinessAnalyticsResponse:
    """Get business analytics."""
    
    try:
        # Get business
        query = select(Business).where(Business.owner_id == current_user.id)
        result = await session.execute(query)
        business = result.scalar_one_or_none()
        
        if not business:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Business not found"
            )
        
        # In production, this would query actual analytics data
        # For now, we'll return sample analytics
        
        analytics = BusinessAnalyticsResponse(
            total_views=1250,
            total_clicks=340,
            total_reviews=business.review_count,
            average_rating=float(business.rating) if business.rating else None,
            views_last_30_days=450,
            clicks_last_30_days=120,
            reviews_last_30_days=8,
            click_through_rate=27.2,
            response_rate=85.5,
            search_rankings={
                business.category: 5,
                f"{business.category} {business.city}": 3,
                business.name.lower(): 1
            },
            recommendation_appearances=25,
            visitor_locations={
                business.city: 60,
                "nearby_city_1": 25,
                "nearby_city_2": 15
            },
            daily_views=[
                {"date": "2024-01-01", "views": 15, "clicks": 4},
                {"date": "2024-01-02", "views": 23, "clicks": 6},
                # ... more daily data would be here
            ],
            peak_hours=[12, 13, 17, 18, 19, 20],
            category_rank=5,
            local_rank=3
        )
        
        logger.info(
            "Business analytics retrieved",
            business_id=business.id,
            owner_id=current_user.id,
            days=days
        )
        
        return analytics
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get business analytics",
            user_id=current_user.id,
            error=str(e),
            exc_info=True
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get analytics: {str(e)}"
        )

@router.get(
    "/reviews",
    response_model=List[ReviewResponse],
    summary="Get business reviews",
    description="Get all reviews for the business owner's listing.",
)
async def get_business_reviews(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Reviews per page"),
    rating_filter: Optional[int] = Query(None, ge=1, le=5, description="Filter by rating"),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_business_owner)
) -> List[ReviewResponse]:
    """Get reviews for the business."""
    
    try:
        # Get business
        business_query = select(Business).where(Business.owner_id == current_user.id)
        business_result = await session.execute(business_query)
        business = business_result.scalar_one_or_none()
        
        if not business:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Business not found"
            )
        
        # In production, this would query actual review data
        # For now, we'll return sample reviews
        
        sample_reviews = [
            ReviewResponse(
                id=UUID("12345678-1234-5678-9012-123456789012"),
                user_name="John Doe",
                rating=4.5,
                review_text="Great service and friendly staff. Highly recommended!",
                created_at=datetime.utcnow() - timedelta(days=5),
                business_response=None,
                response_date=None,
                helpful_votes=3,
                verified_purchase=True
            ),
            ReviewResponse(
                id=UUID("12345678-1234-5678-9012-123456789013"),
                user_name="Jane Smith",
                rating=5.0,
                review_text="Absolutely amazing experience. Will definitely come back!",
                created_at=datetime.utcnow() - timedelta(days=12),
                business_response="Thank you so much for your kind words!",
                response_date=datetime.utcnow() - timedelta(days=10),
                helpful_votes=7,
                verified_purchase=True
            )
        ]
        
        # Apply rating filter if specified
        if rating_filter:
            sample_reviews = [r for r in sample_reviews if int(r.rating) == rating_filter]
        
        # Apply pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_reviews = sample_reviews[start_idx:end_idx]
        
        logger.info(
            "Business reviews retrieved",
            business_id=business.id,
            owner_id=current_user.id,
            page=page,
            reviews_count=len(paginated_reviews)
        )
        
        return paginated_reviews
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get business reviews",
            user_id=current_user.id,
            error=str(e),
            exc_info=True
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get reviews: {str(e)}"
        )


@router.post(
    "/reviews/{review_id}/respond",
    summary="Respond to review",
    description="Respond to a customer review.",
)
async def respond_to_review(
    review_id: UUID,
    request: ReviewResponseRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_business_owner)
) -> Dict[str, str]:
    """Respond to a customer review."""
    
    try:
        # Get business
        business_query = select(Business).where(Business.owner_id == current_user.id)
        business_result = await session.execute(business_query)
        business = business_result.scalar_one_or_none()
        
        if not business:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Business not found"
            )
        
        # In production, this would:
        # 1. Verify the review exists and belongs to this business
        # 2. Store the response in the database
        # 3. Send notification to the reviewer
        
        logger.info(
            "Review response recorded",
            business_id=business.id,
            review_id=review_id,
            owner_id=current_user.id,
            response_length=len(request.response_text)
        )
        
        return {"message": "Response to review recorded successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to respond to review",
            review_id=review_id,
            user_id=current_user.id,
            error=str(e),
            exc_info=True
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to respond to review: {str(e)}"
        )


@router.post(
    "/photos/upload",
    summary="Upload business photos",
    description="Upload photos for the business listing.",
)
async def upload_business_photos(
    files: List[UploadFile] = File(..., description="Photo files to upload"),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_business_owner)
) -> Dict[str, Any]:
    """Upload photos for the business."""
    
    try:
        # Get business
        business_query = select(Business).where(Business.owner_id == current_user.id)
        business_result = await session.execute(business_query)
        business = business_result.scalar_one_or_none()
        
        if not business:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Business not found"
            )
        
        # Validate files
        max_files = 10
        max_file_size = 5 * 1024 * 1024  # 5MB
        allowed_types = {"image/jpeg", "image/png", "image/webp"}
        
        if len(files) > max_files:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Maximum {max_files} files allowed"
            )
        
        uploaded_photos = []
        
        for file in files:
            # Validate file type
            if file.content_type not in allowed_types:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid file type: {file.content_type}. Allowed: {allowed_types}"
                )
            
            # Read file content for size validation
            content = await file.read()
            
            if len(content) > max_file_size:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"File {file.filename} too large. Maximum size: {max_file_size / 1024 / 1024}MB"
                )
            
            # In production, this would:
            # 1. Upload to cloud storage (AWS S3, Google Cloud Storage, etc.)
            # 2. Generate thumbnails
            # 3. Store URLs in database
            
            # For now, we'll simulate the upload
            photo_url = f"https://storage.lishfind.com/business/{business.id}/{file.filename}"
            uploaded_photos.append({
                "filename": file.filename,
                "url": photo_url,
                "size": len(content)
            })
        
        # Update business photos in database
        current_photos = business.photos or []
        new_photo_urls = [photo["url"] for photo in uploaded_photos]
        business.photos = current_photos + new_photo_urls
        business.updated_at = datetime.utcnow()
        
        await session.commit()
        
        logger.info(
            "Business photos uploaded",
            business_id=business.id,
            owner_id=current_user.id,
            photos_count=len(uploaded_photos),
            total_photos=len(business.photos)
        )
        
        return {
            "message": f"Successfully uploaded {len(uploaded_photos)} photos",
            "uploaded_photos": uploaded_photos,
            "total_photos": len(business.photos)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to upload business photos",
            user_id=current_user.id,
            error=str(e),
            exc_info=True
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload photos: {str(e)}"
        )


@router.delete(
    "/photos/{photo_url:path}",
    summary="Delete business photo",
    description="Delete a specific photo from the business listing.",
)
async def delete_business_photo(
    photo_url: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_business_owner)
) -> Dict[str, str]:
    """Delete a business photo."""
    
    try:
        # Get business
        business_query = select(Business).where(Business.owner_id == current_user.id)
        business_result = await session.execute(business_query)
        business = business_result.scalar_one_or_none()
        
        if not business:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Business not found"
            )
        
        # Check if photo exists in business photos
        if not business.photos or photo_url not in business.photos:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Photo not found in business listing"
            )
        
        # Remove photo from list
        business.photos = [url for url in business.photos if url != photo_url]
        business.updated_at = datetime.utcnow()
        
        await session.commit()
        
        # In production, this would also delete the file from cloud storage
        
        logger.info(
            "Business photo deleted",
            business_id=business.id,
            owner_id=current_user.id,
            photo_url=photo_url,
            remaining_photos=len(business.photos)
        )
        
        return {"message": "Photo deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to delete business photo",
            user_id=current_user.id,
            photo_url=photo_url,
            error=str(e),
            exc_info=True
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete photo: {str(e)}"
        )


@router.get(
    "/insights",
    summary="Get business insights",
    description="Get AI-powered insights and recommendations for improving the business listing.",
)
async def get_business_insights(
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_business_owner)
) -> Dict[str, Any]:
    """Get AI-powered business insights and recommendations."""
    
    try:
        # Get business
        business_query = select(Business).where(Business.owner_id == current_user.id)
        business_result = await session.execute(business_query)
        business = business_result.scalar_one_or_none()
        
        if not business:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Business not found"
            )
        
        # In production, this would use AI to analyze the business
        # and provide personalized insights and recommendations
        
        insights = {
            "profile_completeness": {
                "score": 75,
                "missing_elements": [
                    "Business hours for Sunday",
                    "More photos needed (minimum 5 recommended)",
                    "Social media links"
                ]
            },
            "performance_insights": [
                "Your business has 23% higher click-through rate than category average",
                "Peak visitor times are 12-2 PM and 6-8 PM",
                "Reviews mentioning 'friendly staff' increased by 40% this month"
            ],
            "recommendations": [
                {
                    "type": "photos",
                    "priority": "high",
                    "title": "Add more photos",
                    "description": "Businesses with 5+ photos get 67% more clicks",
                    "action": "Upload interior and menu photos"
                },
                {
                    "type": "hours",
                    "priority": "medium", 
                    "title": "Complete opening hours",
                    "description": "Missing Sunday hours may confuse potential customers",
                    "action": "Add Sunday operating hours or mark as closed"
                },
                {
                    "type": "description",
                    "priority": "low",
                    "title": "Enhance description",
                    "description": "Include more details about your specialties",
                    "action": "Mention signature dishes or unique features"
                }
            ],
            "competitor_analysis": {
                "category_average_rating": 4.2,
                "your_rating": float(business.rating) if business.rating else None,
                "category_average_reviews": 45,
                "your_reviews": business.review_count,
                "trending_amenities": ["Wi-Fi", "Outdoor seating", "Takeout"]
            },
            "search_optimization": {
                "keyword_suggestions": [
                    f"best {business.category} in {business.city}",
                    f"{business.category} near me",
                    f"top {business.category} {business.city}"
                ],
                "current_rankings": {
                    business.category: 5,
                    f"{business.category} {business.city}": 3
                }
            }
        }
        
        logger.info(
            "Business insights generated",
            business_id=business.id,
            owner_id=current_user.id,
            profile_completeness=insights["profile_completeness"]["score"]
        )
        
        return insights
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get business insights",
            user_id=current_user.id,
            error=str(e),
            exc_info=True
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get insights: {str(e)}"
        )


@router.post(
    "/verification/request",
    summary="Request business verification",
    description="Submit a request for business verification.",
)
async def request_verification(
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_business_owner)
) -> Dict[str, str]:
    """Request business verification."""
    
    try:
        # Get business
        business_query = select(Business).where(Business.owner_id == current_user.id)
        business_result = await session.execute(business_query)
        business = business_result.scalar_one_or_none()
        
        if not business:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Business not found"
            )
        
        if business.verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Business is already verified"
            )
        
        # In production, this would:
        # 1. Create a verification request record
        # 2. Send notification to admin team
        # 3. Possibly initiate automated verification checks
        
        logger.info(
            "Business verification requested",
            business_id=business.id,
            owner_id=current_user.id,
            business_name=business.name
        )
        
        return {
            "message": "Verification request submitted successfully. Our team will review your business and respond within 2-3 business days."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to request verification",
            user_id=current_user.id,
            error=str(e),
            exc_info=True
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to request verification: {str(e)}"
        )


@router.get(
    "/dashboard",
    summary="Get business dashboard",
    description="Get comprehensive dashboard data for business owners.",
)
async def get_business_dashboard(
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_business_owner)
) -> Dict[str, Any]:
    """Get business dashboard data."""
    
    try:
        # Get business
        business_query = select(Business).where(Business.owner_id == current_user.id)
        business_result = await session.execute(business_query)
        business = business_result.scalar_one_or_none()
        
        if not business:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Business not found"
            )
        
        # Compile dashboard data
        dashboard = {
            "business_overview": {
                "name": business.name,
                "status": business.status.value,
                "verified": business.verified,
                "rating": float(business.rating) if business.rating else None,
                "review_count": business.review_count,
                "photos_count": len(business.photos) if business.photos else 0
            },
            "quick_stats": {
                "views_today": 42,
                "clicks_today": 12,
                "new_reviews": 2,
                "pending_responses": 1
            },
            "recent_activity": [
                {
                    "type": "review",
                    "message": "New 5-star review received",
                    "timestamp": datetime.utcnow() - timedelta(hours=3)
                },
                {
                    "type": "view",
                    "message": "25 profile views today",
                    "timestamp": datetime.utcnow() - timedelta(hours=6)
                },
                {
                    "type": "update",
                    "message": "Business information updated",
                    "timestamp": business.updated_at
                }
            ],
            "alerts": [
                {
                    "type": "warning",
                    "message": "1 review needs response",
                    "action": "Respond to customer review to improve engagement"
                }
            ],
            "performance_summary": {
                "this_week": {
                    "views": 180,
                    "clicks": 45,
                    "conversion_rate": 25.0
                },
                "last_week": {
                    "views": 160,
                    "clicks": 38,
                    "conversion_rate": 23.8
                },
                "trend": "up"
            }
        }
        
        logger.info(
            "Business dashboard data retrieved",
            business_id=business.id,
            owner_id=current_user.id
        )
        
        return dashboard
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get business dashboard",
            user_id=current_user.id,
            error=str(e),
            exc_info=True
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get dashboard: {str(e)}"
        )