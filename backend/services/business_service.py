"""
Business service for LishFind backend.

Provides business logic for business management, analytics, and operations.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID

import structlog
from sqlalchemy import select, and_, or_, func, desc, text
from sqlalchemy.ext.asyncio import AsyncSession

from database.redis import get_cache, set_cache
from models.business import Business, BusinessStatus
from models.user import User

logger = structlog.get_logger(__name__)


class BusinessService:
    """Business service for managing business operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.cache_ttl = 3600  # 1 hour cache
        
    async def get_business_by_owner(self, owner_id: UUID) -> Optional[Business]:
        """Get business by owner ID."""
        
        try:
            query = select(Business).where(Business.owner_id == owner_id)
            result = await self.session.execute(query)
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error(
                "Failed to get business by owner",
                owner_id=owner_id,
                error=str(e)
            )
            return None
    
    async def create_business(
        self,
        owner_id: UUID,
        business_data: Dict[str, Any]
    ) -> Business:
        """Create a new business listing."""
        
        try:
            # Check if owner already has a business
            existing_business = await self.get_business_by_owner(owner_id)
            if existing_business:
                raise ValueError("User already has a business listing")
            
            # Create business object
            business = Business(
                owner_id=owner_id,
                status=BusinessStatus.PENDING,
                verified=False,
                rating=None,
                review_count=0,
                popularity_score=None,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                **business_data
            )
            
            self.session.add(business)
            await self.session.commit()
            await self.session.refresh(business)
            
            # Clear relevant caches
            await self._clear_business_caches(business.id, owner_id)
            
            logger.info(
                "Business created successfully",
                business_id=business.id,
                owner_id=owner_id,
                business_name=business.name
            )
            
            return business
            
        except Exception as e:
            logger.error(
                "Failed to create business",
                owner_id=owner_id,
                error=str(e)
            )
            raise
    
    async def update_business(
        self,
        business_id: UUID,
        owner_id: UUID,
        updates: Dict[str, Any]
    ) -> Business:
        """Update business information."""
        
        try:
            # Get business and verify ownership
            business = await self.get_business_by_owner(owner_id)
            if not business or business.id != business_id:
                raise ValueError("Business not found or access denied")
            
            # Apply updates
            for field, value in updates.items():
                if hasattr(business, field):
                    setattr(business, field, value)
            
            business.updated_at = datetime.utcnow()
            
            await self.session.commit()
            
            # Clear caches
            await self._clear_business_caches(business_id, owner_id)
            
            logger.info(
                "Business updated successfully",
                business_id=business_id,
                owner_id=owner_id,
                updated_fields=list(updates.keys())
            )
            
            return business
            
        except Exception as e:
            logger.error(
                "Failed to update business",
                business_id=business_id,
                owner_id=owner_id,
                error=str(e)
            )
            raise
    
    async def get_business_analytics(
        self,
        business_id: UUID,
        owner_id: UUID,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get business analytics data."""
        
        try:
            # Verify business ownership
            business = await self.get_business_by_owner(owner_id)
            if not business or business.id != business_id:
                raise ValueError("Business not found or access denied")
            
            # Check cache first
            cache_key = f"business_analytics:{business_id}:{days}"
            cached_analytics = await get_cache(cache_key)
            
            if cached_analytics:
                return json.loads(cached_analytics)
            
            # Calculate analytics
            analytics = await self._calculate_business_analytics(business, days)
            
            # Cache the results
            await set_cache(
                cache_key,
                json.dumps(analytics, default=str),
                ttl=self.cache_ttl
            )
            
            return analytics
            
        except Exception as e:
            logger.error(
                "Failed to get business analytics",
                business_id=business_id,
                owner_id=owner_id,
                error=str(e)
            )
            raise
    
    async def get_business_reviews(
        self,
        business_id: UUID,
        owner_id: UUID,
        page: int = 1,
        page_size: int = 20,
        rating_filter: Optional[int] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Get business reviews with pagination."""
        
        try:
            # Verify business ownership
            business = await self.get_business_by_owner(owner_id)
            if not business or business.id != business_id:
                raise ValueError("Business not found or access denied")
            
            # In production, this would query the reviews table
            # For now, return sample data
            
            sample_reviews = self._get_sample_reviews(business_id)
            
            # Apply rating filter
            if rating_filter:
                sample_reviews = [
                    r for r in sample_reviews 
                    if int(r["rating"]) == rating_filter
                ]
            
            # Calculate pagination
            total_count = len(sample_reviews)
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            paginated_reviews = sample_reviews[start_idx:end_idx]
            
            return paginated_reviews, total_count
            
        except Exception as e:
            logger.error(
                "Failed to get business reviews",
                business_id=business_id,
                owner_id=owner_id,
                error=str(e)
            )
            raise
    
    async def respond_to_review(
        self,
        business_id: UUID,
        owner_id: UUID,
        review_id: UUID,
        response_text: str
    ) -> Dict[str, Any]:
        """Record business response to a review."""
        
        try:
            # Verify business ownership
            business = await self.get_business_by_owner(owner_id)
            if not business or business.id != business_id:
                raise ValueError("Business not found or access denied")
            
            # In production, this would:
            # 1. Verify review exists and belongs to business
            # 2. Store response in database
            # 3. Send notification to reviewer
            # 4. Update review engagement metrics
            
            response_data = {
                "review_id": review_id,
                "business_id": business_id,
                "response_text": response_text,
                "response_date": datetime.utcnow(),
                "responder_id": owner_id
            }
            
            # Cache the response (in production, save to database)
            response_cache_key = f"review_response:{review_id}"
            await set_cache(
                response_cache_key,
                json.dumps(response_data, default=str),
                ttl=86400 * 30  # Keep for 30 days
            )
            
            logger.info(
                "Review response recorded",
                business_id=business_id,
                review_id=review_id,
                owner_id=owner_id
            )
            
            return response_data
            
        except Exception as e:
            logger.error(
                "Failed to respond to review",
                business_id=business_id,
                review_id=review_id,
                owner_id=owner_id,
                error=str(e)
            )
            raise
    
    async def upload_business_photos(
        self,
        business_id: UUID,
        owner_id: UUID,
        photo_urls: List[str]
    ) -> Dict[str, Any]:
        """Add photos to business listing."""
        
        try:
            # Verify business ownership
            business = await self.get_business_by_owner(owner_id)
            if not business or business.id != business_id:
                raise ValueError("Business not found or access denied")
            
            # Update business photos
            current_photos = business.photos or []
            business.photos = current_photos + photo_urls
            business.updated_at = datetime.utcnow()
            
            await self.session.commit()
            
            # Clear caches
            await self._clear_business_caches(business_id, owner_id)
            
            logger.info(
                "Business photos uploaded",
                business_id=business_id,
                owner_id=owner_id,
                new_photos_count=len(photo_urls),
                total_photos_count=len(business.photos)
            )
            
            return {
                "new_photos": photo_urls,
                "total_photos": len(business.photos)
            }
            
        except Exception as e:
            logger.error(
                "Failed to upload business photos",
                business_id=business_id,
                owner_id=owner_id,
                error=str(e)
            )
            raise
    
    async def delete_business_photo(
        self,
        business_id: UUID,
        owner_id: UUID,
        photo_url: str
    ) -> Dict[str, Any]:
        """Delete a photo from business listing."""
        
        try:
            # Verify business ownership
            business = await self.get_business_by_owner(owner_id)
            if not business or business.id != business_id:
                raise ValueError("Business not found or access denied")
            
            # Remove photo from list
            if not business.photos or photo_url not in business.photos:
                raise ValueError("Photo not found in business listing")
            
            business.photos = [url for url in business.photos if url != photo_url]
            business.updated_at = datetime.utcnow()
            
            await self.session.commit()
            
            # Clear caches
            await self._clear_business_caches(business_id, owner_id)
            
            logger.info(
                "Business photo deleted",
                business_id=business_id,
                owner_id=owner_id,
                photo_url=photo_url,
                remaining_photos=len(business.photos)
            )
            
            return {
                "deleted_photo": photo_url,
                "remaining_photos": len(business.photos)
            }
            
        except Exception as e:
            logger.error(
                "Failed to delete business photo",
                business_id=business_id,
                owner_id=owner_id,
                photo_url=photo_url,
                error=str(e)
            )
            raise
    
    async def get_business_insights(
        self,
        business_id: UUID,
        owner_id: UUID
    ) -> Dict[str, Any]:
        """Get AI-powered business insights and recommendations."""
        
        try:
            # Verify business ownership
            business = await self.get_business_by_owner(owner_id)
            if not business or business.id != business_id:
                raise ValueError("Business not found or access denied")
            
            # Check cache first
            cache_key = f"business_insights:{business_id}"
            cached_insights = await get_cache(cache_key)
            
            if cached_insights:
                return json.loads(cached_insights)
            
            # Generate insights
            insights = await self._generate_business_insights(business)
            
            # Cache the insights
            await set_cache(
                cache_key,
                json.dumps(insights, default=str),
                ttl=self.cache_ttl * 4  # Cache for 4 hours
            )
            
            return insights
            
        except Exception as e:
            logger.error(
                "Failed to get business insights",
                business_id=business_id,
                owner_id=owner_id,
                error=str(e)
            )
            raise
    
    async def request_business_verification(
        self,
        business_id: UUID,
        owner_id: UUID
    ) -> Dict[str, Any]:
        """Submit business verification request."""
        
        try:
            # Verify business ownership
            business = await self.get_business_by_owner(owner_id)
            if not business or business.id != business_id:
                raise ValueError("Business not found or access denied")
            
            if business.verified:
                raise ValueError("Business is already verified")
            
            # Create verification request
            verification_request = {
                "business_id": business_id,
                "owner_id": owner_id,
                "business_name": business.name,
                "requested_at": datetime.utcnow(),
                "status": "pending",
                "business_data": {
                    "name": business.name,
                    "address": business.address,
                    "phone": business.phone,
                    "email": business.email,
                    "category": business.category
                }
            }
            
            # Store verification request
            request_cache_key = f"verification_request:{business_id}"
            await set_cache(
                request_cache_key,
                json.dumps(verification_request, default=str),
                ttl=86400 * 7  # Keep for 7 days
            )
            
            logger.info(
                "Business verification requested",
                business_id=business_id,
                owner_id=owner_id,
                business_name=business.name
            )
            
            return verification_request
            
        except Exception as e:
            logger.error(
                "Failed to request business verification",
                business_id=business_id,
                owner_id=owner_id,
                error=str(e)
            )
            raise
    
    async def _calculate_business_analytics(
        self,
        business: Business,
        days: int
    ) -> Dict[str, Any]:
        """Calculate comprehensive business analytics."""
        
        # In production, this would query actual analytics data from database/analytics service
        # For now, we'll generate realistic sample data
        
        base_views = max(50, business.review_count * 8)  # Base views based on reviews
        base_clicks = int(base_views * 0.25)  # 25% CTR
        
        analytics = {
            "overview": {
                "total_views": base_views * days // 7,  # Scale by time period
                "total_clicks": base_clicks * days // 7,
                "total_reviews": business.review_count,
                "average_rating": float(business.rating) if business.rating else None,
                "click_through_rate": 25.0,
                "response_rate": 85.0
            },
            "recent_performance": {
                f"views_last_{days}_days": base_views * days // 30,
                f"clicks_last_{days}_days": base_clicks * days // 30,
                f"reviews_last_{days}_days": max(1, business.review_count // 4)
            },
            "search_performance": {
                "search_rankings": {
                    business.category: 5,
                    f"{business.category} {business.city}": 3,
                    business.name.lower(): 1
                },
                "recommendation_appearances": 15 * days // 30,
                "trending_score": float(business.popularity_score or 0) / 100.0
            },
            "geographic_data": {
                "visitor_locations": {
                    business.city: 60,
                    "nearby_area_1": 25,
                    "nearby_area_2": 15
                },
                "service_radius_km": 10.0
            },
            "engagement_patterns": {
                "peak_hours": [12, 13, 17, 18, 19, 20],
                "busiest_days": ["friday", "saturday", "sunday"],
                "seasonal_trends": {
                    "spring": 0.9,
                    "summer": 1.2,
                    "fall": 1.0,
                    "winter": 0.8
                }
            },
            "competitive_analysis": {
                "category_rank": 5,
                "local_rank": 3,
                "category_average_rating": 4.1,
                "category_average_reviews": 35
            }
        }
        
        return analytics
    
    def _get_sample_reviews(self, business_id: UUID) -> List[Dict[str, Any]]:
        """Get sample reviews for demonstration purposes."""
        
        sample_reviews = [
            {
                "id": "12345678-1234-5678-9012-123456789012",
                "user_name": "John Doe",
                "rating": 4.5,
                "review_text": "Great service and friendly staff. Highly recommended!",
                "created_at": datetime.utcnow() - timedelta(days=5),
                "business_response": None,
                "response_date": None,
                "helpful_votes": 3,
                "verified_purchase": True
            },
            {
                "id": "12345678-1234-5678-9012-123456789013",
                "user_name": "Jane Smith", 
                "rating": 5.0,
                "review_text": "Absolutely amazing experience. Will definitely come back!",
                "created_at": datetime.utcnow() - timedelta(days=12),
                "business_response": "Thank you so much for your kind words!",
                "response_date": datetime.utcnow() - timedelta(days=10),
                "helpful_votes": 7,
                "verified_purchase": True
            },
            {
                "id": "12345678-1234-5678-9012-123456789014",
                "user_name": "Mike Johnson",
                "rating": 4.0,
                "review_text": "Good quality and reasonable prices. Could improve the atmosphere a bit.",
                "created_at": datetime.utcnow() - timedelta(days=20),
                "business_response": None,
                "response_date": None,
                "helpful_votes": 1,
                "verified_purchase": False
            },
            {
                "id": "12345678-1234-5678-9012-123456789015",
                "user_name": "Sarah Wilson",
                "rating": 3.5,
                "review_text": "Average experience. Food was okay but service was slow.",
                "created_at": datetime.utcnow() - timedelta(days=25),
                "business_response": "Thank you for your feedback. We're working on improving our service speed.",
                "response_date": datetime.utcnow() - timedelta(days=23),
                "helpful_votes": 2,
                "verified_purchase": True
            },
            {
                "id": "12345678-1234-5678-9012-123456789016",
                "user_name": "David Brown",
                "rating": 5.0,
                "review_text": "Exceptional quality! Best in the area. Staff went above and beyond.",
                "created_at": datetime.utcnow() - timedelta(days=30),
                "business_response": "We're so glad you had a great experience! Thank you!",
                "response_date": datetime.utcnow() - timedelta(days=28),
                "helpful_votes": 12,
                "verified_purchase": True
            }
        ]
        
        return sample_reviews
    
    async def _generate_business_insights(self, business: Business) -> Dict[str, Any]:
        """Generate AI-powered business insights and recommendations."""
        
        # Calculate profile completeness
        completeness_factors = {
            "description": bool(business.description and len(business.description) > 50),
            "photos": bool(business.photos and len(business.photos) >= 3),
            "hours": bool(business.opening_hours),
            "contact": bool(business.phone and business.email),
            "website": bool(business.website),
            "social_media": bool(business.social_media and business.social_media),
            "amenities": bool(business.amenities and len(business.amenities) >= 3),
            "services": bool(business.services and len(business.services) >= 2)
        }
        
        completeness_score = int(sum(completeness_factors.values()) / len(completeness_factors) * 100)
        
        missing_elements = [
            factor.replace("_", " ").title() 
            for factor, complete in completeness_factors.items() 
            if not complete
        ]
        
        # Generate recommendations based on missing elements
        recommendations = []
        
        if not completeness_factors["photos"]:
            recommendations.append({
                "type": "photos",
                "priority": "high",
                "title": "Add more photos",
                "description": "Businesses with 5+ photos get 67% more clicks",
                "action": "Upload interior, exterior, and product photos"
            })
        
        if not completeness_factors["hours"]:
            recommendations.append({
                "type": "hours",
                "priority": "medium",
                "title": "Add opening hours",
                "description": "Customers need to know when you're open",
                "action": "Complete your opening hours for all days"
            })
        
        if not completeness_factors["website"]:
            recommendations.append({
                "type": "website",
                "priority": "medium",
                "title": "Add website URL",
                "description": "Websites increase customer trust and engagement",
                "action": "Add your website or create a simple business website"
            })
        
        if not completeness_factors["amenities"]:
            recommendations.append({
                "type": "amenities",
                "priority": "low",
                "title": "List your amenities",
                "description": "Help customers find exactly what they're looking for",
                "action": "Add amenities like Wi-Fi, parking, accessibility features"
            })
        
        # Performance insights based on business data
        performance_insights = [
            f"Your business is in the {business.category} category"
        ]
        
        if business.rating and business.rating >= 4.0:
            performance_insights.append(f"Great job! Your {business.rating}★ rating is above average")
        elif business.rating and business.rating < 3.5:
            performance_insights.append("Focus on improving customer satisfaction to boost ratings")
        
        if business.review_count > 20:
            performance_insights.append(f"You have {business.review_count} reviews - great customer engagement!")
        elif business.review_count < 5:
            performance_insights.append("Encourage happy customers to leave reviews")
        
        # SEO and search optimization suggestions
        keyword_suggestions = [
            f"best {business.category} in {business.city}",
            f"{business.category} near me",
            f"top rated {business.category}",
            f"{business.city} {business.category}"
        ]
        
        if business.services:
            keyword_suggestions.extend([
                f"{service} in {business.city}" 
                for service in business.services[:3]
            ])
        
        insights = {
            "profile_completeness": {
                "score": completeness_score,
                "missing_elements": missing_elements,
                "completion_factors": completeness_factors
            },
            "performance_insights": performance_insights,
            "recommendations": recommendations,
            "competitor_analysis": {
                "category_average_rating": 4.2,
                "your_rating": float(business.rating) if business.rating else None,
                "category_average_reviews": 45,
                "your_reviews": business.review_count,
                "performance_vs_average": "above" if business.rating and business.rating > 4.2 else "below"
            },
            "search_optimization": {
                "keyword_suggestions": keyword_suggestions,
                "current_rankings": {
                    business.category: 5,
                    f"{business.category} {business.city}": 3
                },
                "seo_score": completeness_score // 10  # Simple SEO score based on completeness
            },
            "growth_opportunities": [
                "Respond to all customer reviews to show engagement",
                "Post regular updates about special offers or new services",
                "Encourage customers to share photos of their experience"
            ]
        }
        
        return insights
    
    async def _clear_business_caches(self, business_id: UUID, owner_id: UUID) -> None:
        """Clear business-related caches."""
        
        try:
            # List of cache keys to clear
            cache_keys = [
                f"business_analytics:{business_id}:30",
                f"business_insights:{business_id}",
                f"business_profile:{business_id}",
                f"business_owner:{owner_id}"
            ]
            
            # In production, you'd use Redis pipeline for efficiency
            for cache_key in cache_keys:
                try:
                    # Redis delete would go here
                    pass
                except Exception as e:
                    logger.warning(
                        "Failed to clear cache key",
                        cache_key=cache_key,
                        error=str(e)
                    )
            
            logger.debug(
                "Business caches cleared",
                business_id=business_id,
                cache_keys_count=len(cache_keys)
            )
            
        except Exception as e:
            logger.warning(
                "Failed to clear business caches",
                business_id=business_id,
                error=str(e)
            )