"""
PostgreSQL-based search engine for LishFind businesses.

Implements full-text search with geospatial filtering and ranking.
"""

import time
from datetime import datetime, time as time_obj
from decimal import Decimal
from typing import List, Optional, Dict, Any, Tuple

import pytz
import structlog
from sqlalchemy import text, select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from geoalchemy2.functions import ST_DWithin, ST_Distance

from models.business import Business, BusinessStatus, PriceRange
from search.models import SearchQuery, SearchResult, BusinessSearchResult, SearchFilters, SortOrder
from ranking.service import RankingService
from ranking.models import RankingAlgorithm

logger = structlog.get_logger(__name__)


class SearchEngine:
    """PostgreSQL-based search engine with full-text search and geospatial filtering."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.ranking_service = RankingService(session)
        
    async def search_businesses(self, query: SearchQuery) -> SearchResult:
        """
        Execute business search with filters and ranking.
        
        Args:
            query: Complete search query with intent and filters
            
        Returns:
            SearchResult with matching businesses and metadata
        """
        
        start_time = time.time()
        
        try:
            # Build the search query
            search_stmt, count_stmt = await self._build_search_query(query)
            
            # Execute search and count queries
            search_result = await self.session.execute(search_stmt)
            count_result = await self.session.execute(count_stmt)
            
            businesses_data = search_result.fetchall()
            total_count = count_result.scalar()
            
            # Convert to business results
            businesses = []
            business_ids = []
            
            for row in businesses_data:
                business_result = await self._convert_to_search_result(row, query)
                businesses.append(business_result)
                business_ids.append(business_result.id)
            
            # Apply intelligent ranking if we have results
            if businesses and query.sort_by in [SortOrder.RELEVANCE, SortOrder.POPULARITY]:
                try:
                    # Determine ranking algorithm based on sort order
                    if query.sort_by == SortOrder.RELEVANCE:
                        algorithm = RankingAlgorithm.BALANCED
                    else:
                        algorithm = RankingAlgorithm.POPULARITY_PRIORITY
                    
                    # Prepare user location for ranking
                    user_location = None
                    if query.filters.latitude and query.filters.longitude:
                        user_location = {
                            'latitude': query.filters.latitude,
                            'longitude': query.filters.longitude
                        }
                    
                    # Get ranking results
                    ranking_results = await self.ranking_service.rank_search_results(
                        business_ids=business_ids,
                        algorithm=algorithm,
                        user_id=query.user_id,
                        user_location=user_location
                    )
                    
                    # Reorder businesses based on ranking results
                    if ranking_results:
                        business_lookup = {b.id: b for b in businesses}
                        ranked_businesses = []
                        
                        for ranking_result in ranking_results:
                            business = business_lookup.get(ranking_result.business_id)
                            if business:
                                # Update business with ranking score
                                business.relevance_score = ranking_result.final_score
                                ranked_businesses.append(business)
                        
                        businesses = ranked_businesses
                        
                        logger.debug(
                            "Applied intelligent ranking to search results",
                            original_count=len(business_ids),
                            ranked_count=len(businesses),
                            algorithm=algorithm.value
                        )
                        
                except Exception as e:
                    logger.warning(
                        "Intelligent ranking failed, using default order",
                        error=str(e)
                    )
                    # Continue with original business order
            
            # Calculate pagination
            total_pages = (total_count + query.page_size - 1) // query.page_size
            
            search_time_ms = int((time.time() - start_time) * 1000)
            
            logger.info(
                "Business search completed",
                query=query.text_query,
                total_results=total_count,
                page=query.page,
                search_time_ms=search_time_ms,
                user_id=query.user_id
            )
            
            return SearchResult(
                businesses=businesses,
                total_count=total_count,
                page=query.page,
                page_size=query.page_size,
                total_pages=total_pages,
                query_used=query.text_query,
                filters_applied=query.filters,
                sort_order=query.sort_by,
                search_time_ms=search_time_ms
            )
            
        except Exception as e:
            search_time_ms = int((time.time() - start_time) * 1000)
            
            logger.error(
                "Business search failed",
                query=query.text_query,
                error=str(e),
                search_time_ms=search_time_ms,
                exc_info=True
            )
            
            # Return empty results on error
            return SearchResult(
                businesses=[],
                total_count=0,
                page=query.page,
                page_size=query.page_size, 
                total_pages=0,
                query_used=query.text_query,
                filters_applied=query.filters,
                sort_order=query.sort_by,
                search_time_ms=search_time_ms
            )
    
    async def _build_search_query(self, query: SearchQuery) -> Tuple[Any, Any]:
        """Build PostgreSQL search query with filters and sorting."""
        
        # Base query
        base_query = select(Business).where(
            and_(
                Business.status == BusinessStatus.VERIFIED,
                Business.verified == True
            )
        )
        
        # Apply filters
        base_query = await self._apply_filters(base_query, query.filters)
        
        # Apply text search
        if query.text_query.strip():
            base_query = await self._apply_text_search(base_query, query.text_query)
        
        # Build count query (without pagination and sorting)
        count_query = select(func.count()).select_from(base_query.alias())
        
        # Apply sorting
        search_query = await self._apply_sorting(base_query, query)
        
        # Apply pagination
        offset = (query.page - 1) * query.page_size
        search_query = search_query.offset(offset).limit(query.page_size)
        
        return search_query, count_query
    
    async def _apply_filters(self, query_stmt, filters: SearchFilters):
        """Apply search filters to the query."""
        
        conditions = []
        
        # Category filters
        if filters.categories:
            conditions.append(Business.category.in_(filters.categories))
        
        if filters.exclude_categories:
            conditions.append(~Business.category.in_(filters.exclude_categories))
        
        # Quality filters
        if filters.min_rating:
            conditions.append(Business.rating >= filters.min_rating)
        
        if filters.min_review_count:
            conditions.append(Business.review_count >= filters.min_review_count)
        
        if filters.verified_only:
            conditions.append(Business.verified == True)
        
        # Geographic filters
        if filters.city:
            conditions.append(Business.city.ilike(f"%{filters.city}%"))
        
        # Location-based filtering (if coordinates provided)
        if filters.latitude and filters.longitude and filters.radius_km:
            # Use PostGIS for distance filtering
            user_point = f"POINT({filters.longitude} {filters.latitude})"
            distance_condition = ST_DWithin(
                Business.location,
                user_point,
                filters.radius_km * 1000  # Convert km to meters
            )
            conditions.append(distance_condition)
        
        # Price range filters
        if filters.price_range:
            conditions.append(Business.price_range.in_(filters.price_range))
        
        # Amenities filters
        if filters.required_amenities:
            for amenity in filters.required_amenities:
                # Check if amenity exists in the amenities array
                conditions.append(Business.amenities.contains([amenity]))
        
        # Opening hours filters
        if filters.open_now:
            # This is simplified - in reality you'd check against current time
            # For now, we'll assume businesses with opening_hours data are open
            conditions.append(Business.opening_hours.is_not(None))
        
        # Apply all conditions
        if conditions:
            query_stmt = query_stmt.where(and_(*conditions))
        
        return query_stmt
    
    async def _apply_text_search(self, query_stmt, text_query: str):
        """Apply full-text search to the query."""
        
        # Clean and prepare search text
        search_text = text_query.strip().lower()
        
        # Use PostgreSQL full-text search
        # Create a combined search vector from multiple fields
        search_conditions = []
        
        # Search in business name (highest priority)
        search_conditions.append(
            func.to_tsvector('english', Business.name).match(
                func.plainto_tsquery('english', search_text)
            )
        )
        
        # Search in description
        search_conditions.append(
            func.to_tsvector('english', func.coalesce(Business.description, '')).match(
                func.plainto_tsquery('english', search_text)
            )
        )
        
        # Search in category
        search_conditions.append(Business.category.ilike(f"%{search_text}%"))
        
        # Search in services array
        search_conditions.append(
            func.array_to_string(Business.services, ' ').ilike(f"%{search_text}%")
        )
        
        # Search in amenities array
        search_conditions.append(
            func.array_to_string(Business.amenities, ' ').ilike(f"%{search_text}%")
        )
        
        # Combine search conditions with OR
        query_stmt = query_stmt.where(or_(*search_conditions))
        
        return query_stmt
    
    async def _apply_sorting(self, query_stmt, query: SearchQuery):
        """Apply sorting to the search query."""
        
        if query.sort_by == SortOrder.RELEVANCE:
            # Sort by text search relevance and rating
            if query.text_query.strip():
                # Calculate relevance score
                relevance_score = (
                    func.ts_rank(
                        func.to_tsvector('english', Business.name),
                        func.plainto_tsquery('english', query.text_query)
                    ) * 2 +  # Name matches are more important
                    func.ts_rank(
                        func.to_tsvector('english', func.coalesce(Business.description, '')),
                        func.plainto_tsquery('english', query.text_query)
                    )
                ).label('relevance_score')
                
                query_stmt = query_stmt.add_columns(relevance_score)
                query_stmt = query_stmt.order_by(
                    relevance_score.desc(),
                    Business.rating.desc().nulls_last(),
                    Business.review_count.desc()
                )
            else:
                # No text query, sort by rating and popularity
                query_stmt = query_stmt.order_by(
                    Business.rating.desc().nulls_last(),
                    Business.review_count.desc(),
                    Business.popularity_score.desc().nulls_last()
                )
        
        elif query.sort_by == SortOrder.DISTANCE:
            # Sort by distance (requires user location)
            if query.filters.latitude and query.filters.longitude:
                user_point = f"POINT({query.filters.longitude} {query.filters.latitude})"
                distance = ST_Distance(Business.location, user_point).label('distance')
                query_stmt = query_stmt.add_columns(distance)
                query_stmt = query_stmt.order_by(distance.asc())
            else:
                # Fallback to rating if no location
                query_stmt = query_stmt.order_by(Business.rating.desc().nulls_last())
        
        elif query.sort_by == SortOrder.RATING:
            query_stmt = query_stmt.order_by(
                Business.rating.desc().nulls_last(),
                Business.review_count.desc()
            )
        
        elif query.sort_by == SortOrder.POPULARITY:
            query_stmt = query_stmt.order_by(
                Business.popularity_score.desc().nulls_last(),
                Business.rating.desc().nulls_last()
            )
        
        elif query.sort_by == SortOrder.NEWEST:
            query_stmt = query_stmt.order_by(Business.created_at.desc())
        
        # Add secondary sorting by ID for consistent results
        query_stmt = query_stmt.order_by(Business.id)
        
        return query_stmt
    
    async def _convert_to_search_result(self, row, query: SearchQuery) -> BusinessSearchResult:
        """Convert database row to BusinessSearchResult."""
        
        business = row[0] if isinstance(row, tuple) else row
        
        # Calculate distance if location-based search
        distance_km = None
        if len(row) > 1 and query.filters.latitude and query.filters.longitude:
            # Distance is in the second column when sorting by distance
            distance_meters = row[1] if isinstance(row, tuple) and len(row) > 1 else None
            if distance_meters is not None:
                distance_km = float(distance_meters) / 1000.0  # Convert to km
        
        # Calculate relevance score if available
        relevance_score = None
        if len(row) > 1 and query.sort_by == SortOrder.RELEVANCE:
            relevance_score = float(row[1]) if isinstance(row, tuple) and len(row) > 1 else None
        
        # Check if currently open (simplified check)
        is_open_now = await self._check_if_open_now(business)
        
        return BusinessSearchResult(
            id=business.id,
            name=business.name,
            category=business.category,
            description=business.description,
            latitude=business.latitude,
            longitude=business.longitude,
            address=business.address,
            city=business.city,
            distance_km=distance_km,
            rating=business.rating,
            review_count=business.review_count,
            verified=business.verified,
            is_open_now=is_open_now,
            price_range=business.price_range,
            phone=business.phone,
            website=business.website,
            photos=business.photos,
            amenities=business.amenities,
            services=business.services,
            relevance_score=relevance_score,
            popularity_score=business.popularity_score,
            opening_hours=business.opening_hours
        )
    
    async def _check_if_open_now(self, business) -> Optional[bool]:
        """Check if business is currently open based on opening hours."""
        
        if not business.opening_hours:
            return None
        
        try:
            # Get current time in Indian timezone
            ist = pytz.timezone('Asia/Kolkata')
            now = datetime.now(ist)
            current_day = now.strftime('%A').lower()
            current_time = now.strftime('%H:%M')
            
            day_hours = business.opening_hours.get(current_day, {})
            
            # Check if closed for the day
            if day_hours.get('closed', False):
                return False
            
            # Check opening hours
            open_time = day_hours.get('open')
            close_time = day_hours.get('close')
            
            if open_time and close_time:
                # Handle cases where business closes after midnight
                if close_time < open_time:  # e.g., 22:00 to 02:00
                    return current_time >= open_time or current_time <= close_time
                else:
                    return open_time <= current_time <= close_time
            
            # If no specific hours, assume open
            return True
            
        except Exception as e:
            logger.warning(
                "Error checking business hours",
                business_id=business.id,
                error=str(e)
            )
            return None
    
    async def get_search_suggestions(self, partial_query: str, limit: int = 5) -> List[str]:
        """Get search suggestions based on partial query."""
        
        try:
            # Simple approach: search for businesses that match partial query
            # and extract common patterns
            
            suggestions = []
            
            if len(partial_query) >= 2:
                # Search for business names and categories that start with the partial query
                stmt = select(Business.name, Business.category).where(
                    and_(
                        Business.status == BusinessStatus.VERIFIED,
                        or_(
                            Business.name.ilike(f"{partial_query}%"),
                            Business.category.ilike(f"{partial_query}%")
                        )
                    )
                ).limit(limit * 2)  # Get more than needed to filter
                
                result = await self.session.execute(stmt)
                rows = result.fetchall()
                
                # Extract suggestions
                seen = set()
                for row in rows:
                    name, category = row
                    
                    # Add business name if it starts with query
                    if name.lower().startswith(partial_query.lower()) and name not in seen:
                        suggestions.append(name)
                        seen.add(name)
                    
                    # Add category-based suggestions
                    category_suggestion = f"{category} near me"
                    if category_suggestion not in seen:
                        suggestions.append(category_suggestion)
                        seen.add(category_suggestion)
                    
                    if len(suggestions) >= limit:
                        break
            
            return suggestions[:limit]
            
        except Exception as e:
            logger.error(
                "Error generating search suggestions",
                partial_query=partial_query,
                error=str(e)
            )
            return []
    
    async def get_search_aggregations(self, query: SearchQuery) -> Dict[str, Any]:
        """Get search result aggregations for faceted search."""
        
        try:
            # Build base query without pagination
            base_query = select(Business).where(
                and_(
                    Business.status == BusinessStatus.VERIFIED,
                    Business.verified == True
                )
            )
            
            # Apply filters (except the ones we want to aggregate on)
            base_query = await self._apply_filters(base_query, query.filters)
            
            # Apply text search
            if query.text_query.strip():
                base_query = await self._apply_text_search(base_query, query.text_query)
            
            # Get category aggregations
            category_stmt = select(
                Business.category,
                func.count(Business.id).label('count')
            ).select_from(base_query.alias()).group_by(Business.category).order_by(func.count(Business.id).desc())
            
            category_result = await self.session.execute(category_stmt)
            categories = {row[0]: row[1] for row in category_result.fetchall()}
            
            # Get price range aggregations
            price_stmt = select(
                Business.price_range,
                func.count(Business.id).label('count')
            ).select_from(base_query.alias()).where(
                Business.price_range.is_not(None)
            ).group_by(Business.price_range).order_by(func.count(Business.id).desc())
            
            price_result = await self.session.execute(price_stmt)
            price_ranges = {row[0]: row[1] for row in price_result.fetchall()}
            
            # Get rating aggregations
            rating_stmt = select(
                func.floor(Business.rating).label('rating_floor'),
                func.count(Business.id).label('count')
            ).select_from(base_query.alias()).where(
                Business.rating.is_not(None)
            ).group_by(func.floor(Business.rating)).order_by('rating_floor')
            
            rating_result = await self.session.execute(rating_stmt)
            ratings = {f"{int(row[0])}+ stars": row[1] for row in rating_result.fetchall()}
            
            return {
                'categories': categories,
                'price_ranges': price_ranges,
                'ratings': ratings,
                'amenities': {},  # Would need more complex query for amenities
                'areas': {}       # Would need area-based aggregation
            }
            
        except Exception as e:
            logger.error(
                "Error generating search aggregations",
                query=query.text_query,
                error=str(e)
            )
            return {
                'categories': {},
                'price_ranges': {},
                'ratings': {},
                'amenities': {},
                'areas': {}
            }