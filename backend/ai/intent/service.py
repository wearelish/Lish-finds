"""
Intent service for managing search intent extraction and caching.

Provides high-level interface for intent extraction with caching and analytics.
"""

import json
from typing import Dict, Any, Optional, List
from uuid import UUID

import structlog

from ai.intent.extractor import IntentExtractor
from ai.intent.models import SearchIntent, IntentExtractionResult, IntentCategory
from database.redis import get_cache, set_cache
from models.analytics import SearchAnalytics
from repositories.user import UserRepository

logger = structlog.get_logger(__name__)


class IntentService:
    """Service for managing intent extraction operations."""
    
    def __init__(self):
        self.extractor = IntentExtractor()
        self.cache_ttl = 3600  # 1 hour cache for similar queries
    
    async def extract_search_intent(
        self, 
        query: str, 
        user_id: Optional[UUID] = None,
        session_id: Optional[str] = None,
        user_location: Optional[Dict[str, Any]] = None
    ) -> IntentExtractionResult:
        """
        Extract search intent with caching and user context.
        
        Args:
            query: User search query
            user_id: Optional authenticated user ID
            session_id: Session ID for anonymous users
            user_location: User's current location
            
        Returns:
            IntentExtractionResult with extracted intent
        """
        
        # Check cache first
        cache_key = self._generate_cache_key(query, user_location)
        cached_result = await self._get_cached_intent(cache_key)
        
        if cached_result:
            logger.info(
                "Intent extraction served from cache",
                query=query,
                cache_key=cache_key
            )
            return cached_result
        
        # Build user context
        user_context = await self._build_user_context(user_id, user_location)
        
        # Extract intent
        result = await self.extractor.extract_intent(query, user_context)
        
        # Cache successful results
        if result.success and result.intent.confidence_score > 0.5:
            await self._cache_intent_result(cache_key, result)
        
        # Log analytics (don't await to avoid blocking)
        self._log_search_analytics(query, result, user_id, session_id)
        
        return result
    
    async def get_query_suggestions(
        self, 
        partial_query: str,
        user_id: Optional[UUID] = None
    ) -> List[str]:
        """
        Generate query suggestions based on partial input.
        
        Args:
            partial_query: Partial search query
            user_id: Optional user ID for personalized suggestions
            
        Returns:
            List of suggested complete queries
        """
        
        # Get common patterns for the detected category
        try:
            # Quick intent extraction for category detection
            if len(partial_query) > 3:
                temp_result = await self.extract_search_intent(partial_query, user_id)
                category = temp_result.intent.primary_category
            else:
                category = None
            
            # Generate suggestions based on category and common patterns
            suggestions = self._generate_suggestions(partial_query, category)
            
            logger.debug(
                "Query suggestions generated",
                partial_query=partial_query,
                category=category,
                suggestions_count=len(suggestions)
            )
            
            return suggestions[:5]  # Return top 5 suggestions
            
        except Exception as e:
            logger.error(
                "Error generating query suggestions",
                partial_query=partial_query,
                error=str(e)
            )
            return []
    
    async def analyze_intent_trends(
        self, 
        time_period_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Analyze search intent trends over a time period.
        
        Args:
            time_period_hours: Hours to look back for trend analysis
            
        Returns:
            Dictionary with trend analysis data
        """
        
        try:
            # This would integrate with analytics repository
            # For now, return mock data structure
            
            trends = {
                "popular_categories": {
                    "restaurant": 45,
                    "cafe": 25,
                    "shopping": 15,
                    "entertainment": 10,
                    "other": 5
                },
                "common_keywords": [
                    "wifi", "parking", "open now", "budget friendly", 
                    "good food", "near me", "family friendly"
                ],
                "peak_search_times": {
                    "morning": 15,
                    "afternoon": 35, 
                    "evening": 40,
                    "night": 10
                },
                "average_confidence": 0.75,
                "total_searches": 1250
            }
            
            logger.info(
                "Intent trends analysis completed",
                time_period_hours=time_period_hours,
                total_searches=trends["total_searches"]
            )
            
            return trends
            
        except Exception as e:
            logger.error(
                "Error analyzing intent trends",
                time_period_hours=time_period_hours,
                error=str(e),
                exc_info=True
            )
            return {}
    
    def _generate_cache_key(self, query: str, user_location: Optional[Dict] = None) -> str:
        """Generate cache key for intent extraction."""
        
        # Normalize query for caching
        normalized_query = query.lower().strip()
        
        # Include location in cache key if provided
        location_key = ""
        if user_location and user_location.get("city"):
            location_key = f"_{user_location['city'].lower()}"
        
        return f"intent:{hash(normalized_query)}{location_key}"
    
    async def _get_cached_intent(self, cache_key: str) -> Optional[IntentExtractionResult]:
        """Get cached intent result."""
        
        try:
            cached_data = await get_cache(cache_key)
            if cached_data:
                data = json.loads(cached_data)
                return IntentExtractionResult(**data)
        except Exception as e:
            logger.warning(
                "Error retrieving cached intent",
                cache_key=cache_key,
                error=str(e)
            )
        
        return None
    
    async def _cache_intent_result(self, cache_key: str, result: IntentExtractionResult) -> None:
        """Cache intent extraction result."""
        
        try:
            # Convert to dict for JSON serialization
            result_dict = result.dict()
            cached_data = json.dumps(result_dict, default=str)
            
            await set_cache(cache_key, cached_data, ttl=self.cache_ttl)
            
            logger.debug("Intent result cached", cache_key=cache_key)
            
        except Exception as e:
            logger.warning(
                "Error caching intent result",
                cache_key=cache_key,
                error=str(e)
            )
    
    async def _build_user_context(
        self, 
        user_id: Optional[UUID], 
        user_location: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Build user context for intent extraction."""
        
        context = {}
        
        # Add location context
        if user_location:
            context["location"] = user_location
        
        # Add user preferences if available
        if user_id:
            try:
                # This would fetch user preferences from repository
                # For now, just add user_id
                context["user_id"] = str(user_id)
                context["has_user_context"] = True
            except Exception as e:
                logger.warning(
                    "Error building user context",
                    user_id=user_id,
                    error=str(e)
                )
        
        return context
    
    def _log_search_analytics(
        self, 
        query: str, 
        result: IntentExtractionResult,
        user_id: Optional[UUID] = None,
        session_id: Optional[str] = None
    ) -> None:
        """Log search analytics (async background task)."""
        
        try:
            # This would be implemented as a background task
            # to avoid blocking the response
            
            logger.info(
                "Search analytics logged",
                query=query,
                success=result.success,
                confidence=result.intent.confidence_score,
                category=result.intent.primary_category,
                user_id=user_id,
                session_id=session_id
            )
            
        except Exception as e:
            logger.warning(
                "Error logging search analytics",
                query=query,
                error=str(e)
            )
    
    def _generate_suggestions(
        self, 
        partial_query: str, 
        category: Optional[IntentCategory]
    ) -> List[str]:
        """Generate query suggestions based on partial input and category."""
        
        suggestions = []
        partial_lower = partial_query.lower()
        
        # Category-specific suggestions
        if category == IntentCategory.RESTAURANT:
            patterns = [
                f"{partial_query} with good food",
                f"{partial_query} near me",
                f"{partial_query} for family dinner",
                f"{partial_query} with parking",
                f"{partial_query} open now"
            ]
        elif category == IntentCategory.CAFE:
            patterns = [
                f"{partial_query} with Wi-Fi",
                f"{partial_query} for work",
                f"{partial_query} with outdoor seating",
                f"{partial_query} quiet atmosphere",
                f"{partial_query} good coffee"
            ]
        elif category == IntentCategory.SHOPPING:
            patterns = [
                f"{partial_query} mall",
                f"{partial_query} market",
                f"{partial_query} with parking",
                f"{partial_query} good deals",
                f"{partial_query} brand stores"
            ]
        else:
            # Generic suggestions
            patterns = [
                f"{partial_query} near me",
                f"{partial_query} open now",
                f"{partial_query} with parking",
                f"{partial_query} good reviews",
                f"{partial_query} budget friendly"
            ]
        
        # Add common completions
        common_completions = {
            "rest": ["restaurant near me", "restaurant for dinner", "restaurant with parking"],
            "cafe": ["cafe with Wi-Fi", "cafe for work", "cafe with good coffee"],
            "food": ["food delivery", "food near me", "food court"],
            "shop": ["shopping mall", "shopping center", "shop near me"],
            "bar": ["bar with live music", "bar for drinks", "bar open now"]
        }
        
        for key, completions in common_completions.items():
            if partial_lower.startswith(key):
                patterns.extend(completions)
        
        # Filter and deduplicate
        suggestions = list(set([p for p in patterns if len(p) > len(partial_query)]))
        
        return suggestions[:10]  # Return top 10