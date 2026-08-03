"""
Search and intent extraction endpoints.

Provides APIs for search intent extraction, query suggestions, business search, and search analytics.
"""

from typing import Dict, List, Optional, Any

import structlog
from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ai.intent.models import SearchIntent, IntentExtractionResult
from ai.intent.service import IntentService
from api.auth.dependencies import get_optional_current_user, get_current_admin_user
from database.connection import get_db_session
from models.user import User
from search.models import SearchResult, SearchFilters, SortOrder
from search.service import SearchService

logger = structlog.get_logger(__name__)

router = APIRouter()


class SearchIntentRequest(BaseModel):
    """Request schema for search intent extraction."""
    
    query: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Natural language search query",
        example="Find a quiet café with Wi-Fi under ₹300 that is open now"
    )
    user_location: Optional[Dict[str, Any]] = Field(
        None,
        description="User's current location",
        example={"city": "New Delhi", "latitude": 28.6139, "longitude": 77.2090}
    )


class SearchIntentResponse(BaseModel):
    """Response schema for search intent extraction."""
    
    success: bool = Field(..., description="Whether intent extraction was successful")
    intent: SearchIntent = Field(..., description="Extracted search intent")
    processing_time_ms: int = Field(..., description="Time taken for extraction")
    error_message: Optional[str] = Field(None, description="Error message if extraction failed")
    
    
class QuerySuggestionsResponse(BaseModel):
    """Response schema for query suggestions."""
    
    suggestions: List[str] = Field(..., description="List of suggested queries")
    partial_query: str = Field(..., description="The partial query that was provided")


class SearchTrendsResponse(BaseModel):
    """Response schema for search trends."""
    
    popular_categories: Dict[str, int] = Field(..., description="Popular search categories")
    common_keywords: List[str] = Field(..., description="Most common search keywords")
    peak_search_times: Dict[str, int] = Field(..., description="Peak search times distribution")
    average_confidence: float = Field(..., description="Average intent extraction confidence")
    total_searches: int = Field(..., description="Total number of searches")


@router.post(
    "/extract-intent",
    response_model=SearchIntentResponse,
    summary="Extract search intent",
    description="Extract structured intent from natural language search query.",
)
async def extract_search_intent(
    request: SearchIntentRequest,
    current_user: Optional[User] = Depends(get_optional_current_user)
) -> SearchIntentResponse:
    """Extract search intent from natural language query."""
    
    try:
        intent_service = IntentService()
        
        # Extract intent with user context
        result = await intent_service.extract_search_intent(
            query=request.query,
            user_id=current_user.id if current_user else None,
            user_location=request.user_location
        )
        
        logger.info(
            "Search intent extraction requested",
            query=request.query,
            user_id=current_user.id if current_user else None,
            success=result.success,
            confidence=result.intent.confidence_score
        )
        
        return SearchIntentResponse(
            success=result.success,
            intent=result.intent,
            processing_time_ms=result.processing_time_ms or 0,
            error_message=result.error_message
        )
        
    except Exception as e:
        logger.error(
            "Search intent extraction failed",
            query=request.query,
            user_id=current_user.id if current_user else None,
            error=str(e),
            exc_info=True
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Intent extraction failed: {str(e)}"
        )


@router.get(
    "/suggestions",
    response_model=QuerySuggestionsResponse,
    summary="Get query suggestions",
    description="Get search query suggestions based on partial input.",
)
async def get_query_suggestions(
    q: str = Query(
        ...,
        min_length=1,
        max_length=100,
        description="Partial search query",
        example="quiet cafe"
    ),
    current_user: Optional[User] = Depends(get_optional_current_user)
) -> QuerySuggestionsResponse:
    """Get query suggestions for autocomplete."""
    
    try:
        intent_service = IntentService()
        
        # Get suggestions
        suggestions = await intent_service.get_query_suggestions(
            partial_query=q,
            user_id=current_user.id if current_user else None
        )
        
        logger.debug(
            "Query suggestions generated",
            partial_query=q,
            user_id=current_user.id if current_user else None,
            suggestions_count=len(suggestions)
        )
        
        return QuerySuggestionsResponse(
            suggestions=suggestions,
            partial_query=q
        )
        
    except Exception as e:
        logger.error(
            "Query suggestions failed",
            partial_query=q,
            user_id=current_user.id if current_user else None,
            error=str(e)
        )
        
        # Return empty suggestions on error instead of failing
        return QuerySuggestionsResponse(
            suggestions=[],
            partial_query=q
        )


@router.get(
    "/trends",
    response_model=SearchTrendsResponse,
    summary="Get search trends",
    description="Get search trends and analytics (admin only).",
)
async def get_search_trends(
    hours: int = Query(
        24,
        ge=1,
        le=168,  # Max 1 week
        description="Time period in hours to analyze trends"
    ),
    current_user: User = Depends(get_current_admin_user)
) -> SearchTrendsResponse:
    """Get search trends and analytics."""
    
    try:
        intent_service = IntentService()
        
        # Get trends analysis
        trends = await intent_service.analyze_intent_trends(
            time_period_hours=hours
        )
        
        logger.info(
            "Search trends requested",
            admin_user_id=current_user.id,
            time_period_hours=hours,
            total_searches=trends.get("total_searches", 0)
        )
        
        return SearchTrendsResponse(
            popular_categories=trends.get("popular_categories", {}),
            common_keywords=trends.get("common_keywords", []),
            peak_search_times=trends.get("peak_search_times", {}),
            average_confidence=trends.get("average_confidence", 0.0),
            total_searches=trends.get("total_searches", 0)
        )
        
    except Exception as e:
        logger.error(
            "Search trends analysis failed",
            admin_user_id=current_user.id,
            time_period_hours=hours,
            error=str(e),
            exc_info=True
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Trends analysis failed: {str(e)}"
        )


@router.post(
    "/test-intent",
    summary="Test intent extraction",
    description="Test intent extraction with various queries (admin only).",
)
async def test_intent_extraction(
    queries: List[str] = Body(
        ...,
        min_items=1,
        max_items=10,
        description="List of test queries",
        example=[
            "Find a romantic restaurant for dinner",
            "Coffee shop with Wi-Fi near me", 
            "Budget shopping mall with parking"
        ]
    ),
    current_user: User = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """Test intent extraction with multiple queries."""
    
    try:
        intent_service = IntentService()
        
        results = []
        
        for query in queries:
            result = await intent_service.extract_search_intent(query)
            
            results.append({
                "query": query,
                "success": result.success,
                "primary_category": result.intent.primary_category,
                "confidence": result.intent.confidence_score,
                "keywords": result.intent.keywords,
                "processing_time_ms": result.processing_time_ms,
                "error": result.error_message
            })
        
        successful_extractions = sum(1 for r in results if r["success"])
        
        logger.info(
            "Batch intent extraction test completed",
            admin_user_id=current_user.id,
            total_queries=len(queries),
            successful_extractions=successful_extractions
        )
        
        return {
            "total_queries": len(queries),
            "successful_extractions": successful_extractions,
            "success_rate": successful_extractions / len(queries),
            "results": results
        }
        
    except Exception as e:
        logger.error(
            "Batch intent extraction test failed",
            admin_user_id=current_user.id,
            queries_count=len(queries),
            error=str(e),
            exc_info=True
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch intent extraction failed: {str(e)}"
        )


class BusinessSearchRequest(BaseModel):
    """Request schema for business search."""
    
    query: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Search query (natural language or keywords)",
        example="quiet café with Wi-Fi near Connaught Place"
    )
    
    # Location context
    latitude: Optional[float] = Field(
        None,
        ge=-90,
        le=90,
        description="User latitude for location-based search"
    )
    longitude: Optional[float] = Field(
        None,
        ge=-180,
        le=180,
        description="User longitude for location-based search"
    )
    radius_km: Optional[float] = Field(
        None,
        ge=0.1,
        le=100,
        description="Search radius in kilometers"
    )
    
    # Filters
    categories: Optional[List[str]] = Field(
        None,
        description="Business categories to include",
        example=["restaurant", "cafe"]
    )
    min_rating: Optional[float] = Field(
        None,
        ge=1.0,
        le=5.0,
        description="Minimum rating filter"
    )
    price_range: Optional[List[str]] = Field(
        None,
        description="Price range filters",
        example=["budget", "moderate"]
    )
    amenities: Optional[List[str]] = Field(
        None,
        description="Required amenities",
        example=["Wi-Fi", "parking"]
    )
    open_now: Optional[bool] = Field(
        False,
        description="Only show businesses open now"
    )
    
    # Sorting and pagination
    sort_by: Optional[SortOrder] = Field(
        SortOrder.RELEVANCE,
        description="Sort order for results"
    )
    page: int = Field(
        1,
        ge=1,
        description="Page number"
    )
    page_size: int = Field(
        20,
        ge=1,
        le=100,
        description="Results per page"
    )


@router.post(
    "/businesses",
    response_model=SearchResult,
    summary="Search businesses",
    description="Search for businesses using natural language query with AI intent extraction.",
)
async def search_businesses(
    request: BusinessSearchRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: Optional[User] = Depends(get_optional_current_user)
) -> SearchResult:
    """Search for businesses using AI-powered intent extraction."""
    
    try:
        search_service = SearchService(session)
        
        # Prepare user location
        user_location = None
        if request.latitude and request.longitude:
            user_location = {
                "latitude": request.latitude,
                "longitude": request.longitude
            }
        
        # If explicit filters are provided, use filtered search
        if any([
            request.categories,
            request.min_rating,
            request.price_range,
            request.amenities,
            request.open_now
        ]):
            # Create explicit filters
            filters = SearchFilters(
                latitude=request.latitude,
                longitude=request.longitude,
                radius_km=request.radius_km,
                categories=request.categories,
                min_rating=request.min_rating,
                price_range=request.price_range,
                required_amenities=request.amenities,
                open_now=request.open_now or False
            )
            
            result = await search_service.search_with_filters(
                query_text=request.query,
                filters=filters,
                sort_by=request.sort_by,
                page=request.page,
                page_size=request.page_size,
                user_id=current_user.id if current_user else None
            )
        else:
            # Use AI intent extraction
            result = await search_service.search_with_intent(
                query_text=request.query,
                user_id=current_user.id if current_user else None,
                user_location=user_location,
                page=request.page,
                page_size=request.page_size,
                sort_by=request.sort_by
            )
        
        logger.info(
            "Business search completed",
            query=request.query,
            total_results=result.total_count,
            page=request.page,
            user_id=current_user.id if current_user else None,
            search_time_ms=result.search_time_ms
        )
        
        return result
        
    except Exception as e:
        logger.error(
            "Business search failed",
            query=request.query,
            user_id=current_user.id if current_user else None,
            error=str(e),
            exc_info=True
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )


@router.get(
    "/facets",
    summary="Get search facets",
    description="Get search facets and filters for advanced search UI.",
)
async def get_search_facets(
    q: str = Query(..., description="Base search query"),
    session: AsyncSession = Depends(get_db_session),
    current_user: Optional[User] = Depends(get_optional_current_user)
) -> Dict[str, Any]:
    """Get search facets for building filter UI."""
    
    try:
        search_service = SearchService(session)
        
        # Get search facets
        facets = await search_service.get_search_facets(q)
        
        logger.debug(
            "Search facets retrieved",
            query=q,
            user_id=current_user.id if current_user else None
        )
        
        return facets
        
    except Exception as e:
        logger.error(
            "Error retrieving search facets",
            query=q,
            user_id=current_user.id if current_user else None,
            error=str(e)
        )
        
        return {
            "categories": {},
            "price_ranges": {},
            "ratings": {},
            "amenities": {},
            "areas": {}
        }


@router.get(
    "/autocomplete",
    response_model=QuerySuggestionsResponse,
    summary="Search autocomplete",
    description="Get search query suggestions for autocomplete functionality.",
)
async def search_autocomplete(
    q: str = Query(
        ...,
        min_length=1,
        max_length=100,
        description="Partial search query"
    ),
    session: AsyncSession = Depends(get_db_session),
    current_user: Optional[User] = Depends(get_optional_current_user)
) -> QuerySuggestionsResponse:
    """Get search autocomplete suggestions."""
    
    try:
        search_service = SearchService(session)
        
        suggestions = await search_service.get_search_suggestions(q)
        
        logger.debug(
            "Search autocomplete generated",
            partial_query=q,
            suggestions_count=len(suggestions),
            user_id=current_user.id if current_user else None
        )
        
        return QuerySuggestionsResponse(
            suggestions=suggestions,
            partial_query=q
        )
        
    except Exception as e:
        logger.error(
            "Error generating autocomplete suggestions",
            partial_query=q,
            user_id=current_user.id if current_user else None,
            error=str(e)
        )
        
        return QuerySuggestionsResponse(
            suggestions=[],
            partial_query=q
        )