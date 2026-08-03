"""
High-level search service for LishFind backend.

Integrates intent extraction with search engine and provides caching.
"""

import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from ai.intent.models import SearchIntent
from ai.intent.service import IntentService
from database.redis import get_cache, set_cache
from search.engine import SearchEngine
from search.models import SearchQuery, SearchResult, SearchFilters, SortOrder

logger = structlog.get_logger(__name__)


class SearchService:
    """High-level search service combining intent extraction and search."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.search_engine = SearchEngine(session)
        self.intent_service = IntentService()
        self.cache_ttl = 1800  # 30 minutes cache for search results
    
    async def search_with_intent(
        self,
        query_text: str,
        user_id: Optional[UUID] = None,
        session_id: Optional[str] = None,
        user_location: Optional[Dict[str, Any]] = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: Optional[SortOrder] = None
    ) -> SearchResult:
        """
        Perform intelligent search with intent extraction.
        
        Args:
            query_text: Natural language search query
            user_id: Optional user ID for personalization
            session_id: Session ID for anonymous users
            user_location: User's current location
            page: Page number for pagination
            page_size: Results per page
            sort_by: Sort order preference
            
        Returns:
            SearchResult with businesses and metadata
        """
        
        try:
            # Check cache first
            cache_key = self._generate_search_cache_key(
                query_text, user_location, page, page_size, sort_by
            )
            
            cached_result = await self._get_cached_search_result(cache_key)
            if cached_result:
                logger.info(
                    "Search result served from cache",
                    query=query_text,
                    cache_key=cache_key
                )
                return cached_result
            
            # Extract intent from query
            intent_result = await self.intent_service.extract_search_intent(
                query_text,
                user_id=user_id,
                session_id=session_id,
                user_location=user_location
            )
            
            if not intent_result.success:
                logger.warning(
                    "Intent extraction failed, using fallback search",
                    query=query_text,
                    error=intent_result.error_message
                )
            
            # Convert intent to search filters
            search_filters = await self._convert_intent_to_filters(
                intent_result.intent, user_location
            )
            
            # Determine sort order
            if sort_by is None:
                sort_by = self._determine_sort_order(intent_result.intent)
            
            # Create search query
            search_query = SearchQuery(
                text_query=query_text,
                intent=intent_result.intent,
                filters=search_filters,
                sort_by=sort_by,
                page=page,
                page_size=page_size,
                user_id=user_id,
                session_id=session_id
            )
            
            # Execute search
            search_result = await self.search_engine.search_businesses(search_query)
            
            # Cache successful results
            if search_result.total_count > 0:
                await self._cache_search_result(cache_key, search_result)
            
            # Log search analytics
            await self._log_search_analytics(
                query_text, intent_result.intent, search_result, user_id, session_id
            )
            
            return search_result
            
        except Exception as e:
            logger.error(
                "Search with intent failed",
                query=query_text,
                user_id=user_id,
                error=str(e),
                exc_info=True
            )
            
            # Fallback to simple text search
            return await self._fallback_search(query_text, page, page_size)
    
    async def search_with_filters(
        self,
        query_text: str,
        filters: SearchFilters,
        sort_by: SortOrder = SortOrder.RELEVANCE,
        page: int = 1,
        page_size: int = 20,
        user_id: Optional[UUID] = None
    ) -> SearchResult:
        """
        Perform search with explicit filters (bypassing intent extraction).
        
        Args:
            query_text: Search query text
            filters: Explicit search filters
            sort_by: Sort order
            page: Page number
            page_size: Results per page
            user_id: Optional user ID
            
        Returns:
            SearchResult with businesses
        """
        
        try:
            search_query = SearchQuery(
                text_query=query_text,
                filters=filters,
                sort_by=sort_by,
                page=page,
                page_size=page_size,
                user_id=user_id
            )
            
            return await self.search_engine.search_businesses(search_query)
            
        except Exception as e:
            logger.error(
                "Search with filters failed",
                query=query_text,
                error=str(e),
                exc_info=True
            )
            
            return await self._fallback_search(query_text, page, page_size)
    
    async def get_search_suggestions(self, partial_query: str) -> List[str]:
        """Get search suggestions for autocomplete."""
        
        try:
            # Combine intent-based suggestions with search engine suggestions
            intent_suggestions = await self.intent_service.get_query_suggestions(partial_query)
            search_suggestions = await self.search_engine.get_search_suggestions(partial_query)
            
            # Merge and deduplicate
            all_suggestions = intent_suggestions + search_suggestions
            unique_suggestions = []
            seen = set()
            
            for suggestion in all_suggestions:
                if suggestion.lower() not in seen:
                    unique_suggestions.append(suggestion)
                    seen.add(suggestion.lower())
            
            return unique_suggestions[:10]  # Return top 10
            
        except Exception as e:
            logger.error(
                "Error getting search suggestions",
                partial_query=partial_query,
                error=str(e)
            )
            return []
    
    async def get_search_facets(
        self, 
        query_text: str, 
        base_filters: Optional[SearchFilters] = None
    ) -> Dict[str, Any]:
        """Get search facets/aggregations for filter UI."""
        
        try:
            # Create base search query
            filters = base_filters or SearchFilters()
            
            search_query = SearchQuery(
                text_query=query_text,
                filters=filters,
                page=1,
                page_size=1  # We only need aggregations
            )
            
            return await self.search_engine.get_search_aggregations(search_query)
            
        except Exception as e:
            logger.error(
                "Error getting search facets",
                query=query_text,
                error=str(e)
            )
            return {}
    
    async def _convert_intent_to_filters(
        self, 
        intent: SearchIntent, 
        user_location: Optional[Dict[str, Any]] = None
    ) -> SearchFilters:
        """Convert search intent to search filters."""
        
        filters = SearchFilters()
        
        # Category filters
        if intent.primary_category:
            filters.categories = [intent.primary_category.value]
            
        if intent.secondary_categories:
            if not filters.categories:
                filters.categories = []
            filters.categories.extend([cat.value for cat in intent.secondary_categories])
        
        # Location filters
        if intent.location:
            if intent.location.city:
                filters.city = intent.location.city
            if intent.location.max_distance_km:
                filters.radius_km = intent.location.max_distance_km
            if intent.location.coordinates:
                filters.latitude = intent.location.coordinates.get("latitude")
                filters.longitude = intent.location.coordinates.get("longitude")
        
        # Use user location if no specific location in intent
        if not filters.latitude and user_location:
            filters.latitude = user_location.get("latitude")
            filters.longitude = user_location.get("longitude")
            # Default radius if location but no specific radius
            if not filters.radius_km and (filters.latitude or filters.longitude):
                filters.radius_km = 10.0  # 10km default
        
        # Time filters
        if intent.time:
            filters.open_now = intent.time.open_now
            if intent.time.specific_time:
                filters.open_at_time = intent.time.specific_time
        
        # Budget filters
        if intent.budget:
            if intent.budget.price_range:
                filters.price_range = [intent.budget.price_range.value]
            if intent.budget.max_budget:
                filters.max_budget = intent.budget.max_budget
        
        # Quality filters
        if intent.min_rating:
            filters.min_rating = intent.min_rating
        
        filters.verified_only = intent.verified_only
        
        # Amenities
        if intent.required_amenities:
            filters.required_amenities = intent.required_amenities
        
        if intent.preferred_amenities:
            filters.preferred_amenities = intent.preferred_amenities
        
        # Dietary and accessibility
        if intent.dietary_preferences:
            filters.dietary_preferences = intent.dietary_preferences
        
        if intent.accessibility_needs:
            filters.accessibility_needs = intent.accessibility_needs
        
        return filters
    
    def _determine_sort_order(self, intent: SearchIntent) -> SortOrder:
        """Determine appropriate sort order based on intent."""
        
        # If user specified location preferences, prioritize distance
        if intent.location and (intent.location.coordinates or intent.location.max_distance_km):
            return SortOrder.DISTANCE
        
        # If looking for high-quality places, sort by rating
        if intent.min_rating and intent.min_rating >= 4.0:
            return SortOrder.RATING
        
        # If budget-conscious, might want to sort by price
        if intent.budget and intent.budget.price_range in ['budget']:
            return SortOrder.PRICE_LOW_TO_HIGH
        
        # Default to relevance for text searches
        return SortOrder.RELEVANCE
    
    async def _fallback_search(
        self, 
        query_text: str, 
        page: int = 1, 
        page_size: int = 20
    ) -> SearchResult:
        """Fallback simple search when intent extraction fails."""
        
        try:
            # Create basic search query
            search_query = SearchQuery(
                text_query=query_text,
                filters=SearchFilters(),
                sort_by=SortOrder.RELEVANCE,
                page=page,
                page_size=page_size
            )
            
            return await self.search_engine.search_businesses(search_query)
            
        except Exception as e:
            logger.error(
                "Fallback search failed",
                query=query_text,
                error=str(e)
            )
            
            # Return empty results as last resort
            return SearchResult(
                businesses=[],
                total_count=0,
                page=page,
                page_size=page_size,
                total_pages=0,
                query_used=query_text,
                filters_applied=SearchFilters(),
                sort_order=SortOrder.RELEVANCE,
                search_time_ms=0
            )
    
    def _generate_search_cache_key(
        self,
        query_text: str,
        user_location: Optional[Dict[str, Any]],
        page: int,
        page_size: int,
        sort_by: Optional[SortOrder]
    ) -> str:
        """Generate cache key for search results."""
        
        # Normalize query text
        normalized_query = query_text.lower().strip()
        
        # Include location in cache key
        location_key = ""
        if user_location and user_location.get("city"):
            location_key = f"_{user_location['city'].lower()}"
        
        # Include pagination and sorting
        cache_key = (
            f"search:{hash(normalized_query)}{location_key}_"
            f"{page}_{page_size}_{sort_by.value if sort_by else 'relevance'}"
        )
        
        return cache_key
    
    async def _get_cached_search_result(self, cache_key: str) -> Optional[SearchResult]:
        """Get cached search result."""
        
        try:
            cached_data = await get_cache(cache_key)
            if cached_data:
                data = json.loads(cached_data)
                return SearchResult(**data)
        except Exception as e:
            logger.warning(
                "Error retrieving cached search result",
                cache_key=cache_key,
                error=str(e)
            )
        
        return None
    
    async def _cache_search_result(self, cache_key: str, result: SearchResult) -> None:
        """Cache search result."""
        
        try:
            # Convert to dict for JSON serialization
            result_dict = result.dict()
            cached_data = json.dumps(result_dict, default=str)
            
            await set_cache(cache_key, cached_data, ttl=self.cache_ttl)
            
            logger.debug("Search result cached", cache_key=cache_key)
            
        except Exception as e:
            logger.warning(
                "Error caching search result",
                cache_key=cache_key,
                error=str(e)
            )
    
    async def _log_search_analytics(
        self,
        query: str,
        intent: SearchIntent,
        result: SearchResult,
        user_id: Optional[UUID] = None,
        session_id: Optional[str] = None
    ) -> None:
        """Log search analytics for reporting and optimization."""
        
        try:
            # This would typically be sent to an analytics service
            # or background task queue
            
            analytics_data = {
                "query": query,
                "intent_category": intent.primary_category.value if intent.primary_category else None,
                "intent_confidence": intent.confidence_score,
                "results_count": result.total_count,
                "search_time_ms": result.search_time_ms,
                "user_id": str(user_id) if user_id else None,
                "session_id": session_id,
                "page": result.page,
                "sort_order": result.sort_order.value,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            logger.info(
                "Search analytics logged",
                **{k: v for k, v in analytics_data.items() if k not in ["timestamp"]}
            )
            
        except Exception as e:
            logger.warning(
                "Error logging search analytics",
                query=query,
                error=str(e)
            )