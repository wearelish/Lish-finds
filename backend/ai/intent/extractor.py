"""
AI-powered intent extractor for natural language search queries.

Converts user queries like "quiet café with Wi-Fi under ₹300" into structured SearchIntent objects.
"""

import json
import time
from typing import Dict, Any, List, Optional

import structlog

from ai.intent.models import (
    SearchIntent, IntentExtractionResult, IntentCategory, 
    PriceRange, TimeOfDay, Mood, LocationPreference, 
    TimePreference, BudgetPreference
)
from services.ai_service import AIService
from core.exceptions import ExternalServiceException

logger = structlog.get_logger(__name__)


class IntentExtractor:
    """Extracts structured intent from natural language queries using AI."""
    
    def __init__(self):
        self.ai_service = AIService()
        
        # Define the JSON schema for intent extraction
        self.intent_schema = {
            "type": "object",
            "properties": {
                "primary_category": {
                    "type": "string",
                    "enum": [cat.value for cat in IntentCategory],
                    "description": "Main business category being searched for"
                },
                "secondary_categories": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [cat.value for cat in IntentCategory]
                    },
                    "description": "Additional relevant categories"
                },
                "keywords": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Important keywords and search terms"
                },
                "required_amenities": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Must-have amenities (Wi-Fi, parking, etc.)"
                },
                "preferred_amenities": {
                    "type": "array", 
                    "items": {"type": "string"},
                    "description": "Nice-to-have amenities"
                },
                "location": {
                    "type": "object",
                    "properties": {
                        "city": {"type": "string"},
                        "area": {"type": "string"}, 
                        "landmark": {"type": "string"},
                        "max_distance_km": {"type": "number"}
                    },
                    "description": "Location preferences"
                },
                "time": {
                    "type": "object",
                    "properties": {
                        "open_now": {"type": "boolean"},
                        "time_of_day": {
                            "type": "string",
                            "enum": [t.value for t in TimeOfDay]
                        },
                        "specific_time": {"type": "string"},
                        "day_of_week": {"type": "string"}
                    },
                    "description": "Time-related preferences"
                },
                "budget": {
                    "type": "object", 
                    "properties": {
                        "price_range": {
                            "type": "string",
                            "enum": [p.value for p in PriceRange]
                        },
                        "max_budget": {"type": "integer"},
                        "min_budget": {"type": "integer"},
                        "budget_per_person": {"type": "integer"}
                    },
                    "description": "Budget constraints"
                },
                "mood": {
                    "type": "string",
                    "enum": [m.value for m in Mood],
                    "description": "Desired ambiance or mood"
                },
                "group_size": {
                    "type": "integer",
                    "description": "Number of people"
                },
                "occasion": {
                    "type": "string",
                    "description": "Special occasion like birthday, date, business meeting"
                },
                "dietary_preferences": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Dietary restrictions like vegetarian, vegan, halal"
                },
                "accessibility_needs": {
                    "type": "array",
                    "items": {"type": "string"}, 
                    "description": "Accessibility requirements"
                },
                "min_rating": {
                    "type": "number",
                    "minimum": 1.0,
                    "maximum": 5.0,
                    "description": "Minimum required rating"
                },
                "verified_only": {
                    "type": "boolean",
                    "description": "Only show verified businesses"
                },
                "confidence_score": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "description": "AI confidence in this extraction"
                }
            },
            "required": ["primary_category"],
            "additionalProperties": False
        }
        
        # System prompt for intent extraction
        self.system_prompt = """
        You are LishFind's intent extraction AI. Your job is to analyze natural language search queries 
        and extract structured intent data for local business searches.
        
        Key guidelines:
        1. Always identify the primary business category being searched for
        2. Extract specific requirements (amenities, budget, location, time)
        3. Understand context clues for mood and occasion
        4. Parse budget amounts in Indian Rupees (₹)
        5. Recognize location references (cities, areas, landmarks)
        6. Identify time preferences (open now, specific times, time of day)
        7. Extract dietary preferences and accessibility needs
        8. Assign a confidence score based on query clarity
        
        Category mappings:
        - Food places: restaurant, cafe, bar
        - Shopping: shopping (malls, stores, markets)
        - Health: healthcare, fitness, beauty
        - Fun: entertainment (movies, games, events)
        - Stay: accommodation (hotels, PGs)
        - Learn: education (schools, courses, training)
        
        Budget ranges in Indian Rupees:
        - budget: Under ₹500
        - moderate: ₹500 - ₹1500  
        - expensive: ₹1500 - ₹3000
        - luxury: Above ₹3000
        
        Common amenities: Wi-Fi, parking, AC, outdoor seating, home delivery, 
        takeaway, wheelchair accessible, pet friendly, live music, etc.
        
        Be precise and only extract information that's clearly stated or strongly implied.
        """
    
    async def extract_intent(self, query: str, user_context: Optional[Dict[str, Any]] = None) -> IntentExtractionResult:
        """
        Extract structured intent from a natural language query.
        
        Args:
            query: The user's search query
            user_context: Optional context (location, preferences, history)
            
        Returns:
            IntentExtractionResult with extracted intent
        """
        
        start_time = time.time()
        
        try:
            # Prepare the extraction prompt
            extraction_prompt = self._build_extraction_prompt(query, user_context)
            
            logger.debug(
                "Starting intent extraction",
                query=query,
                query_length=len(query),
                has_context=user_context is not None
            )
            
            # Extract intent using AI
            extracted_data = await self.ai_service.generate_structured_response(
                prompt=extraction_prompt,
                schema=self.intent_schema,
                system_prompt=self.system_prompt,
                temperature=0.2  # Low temperature for consistent extraction
            )
            
            # Convert to SearchIntent object
            intent = self._convert_to_search_intent(query, extracted_data)
            
            processing_time = int((time.time() - start_time) * 1000)
            
            logger.info(
                "Intent extraction successful",
                query=query,
                primary_category=intent.primary_category,
                keywords_count=len(intent.keywords),
                confidence_score=intent.confidence_score,
                processing_time_ms=processing_time
            )
            
            return IntentExtractionResult(
                intent=intent,
                success=True,
                processing_time_ms=processing_time,
                entities=extracted_data
            )
            
        except ExternalServiceException as e:
            processing_time = int((time.time() - start_time) * 1000)
            
            logger.error(
                "Intent extraction failed - AI service error",
                query=query,
                error=str(e),
                processing_time_ms=processing_time
            )
            
            # Return fallback intent
            fallback_intent = self._create_fallback_intent(query)
            
            return IntentExtractionResult(
                intent=fallback_intent,
                success=False,
                error_message=f"AI service error: {str(e)}",
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            processing_time = int((time.time() - start_time) * 1000)
            
            logger.error(
                "Intent extraction failed - unexpected error",
                query=query,
                error=str(e),
                exc_info=True,
                processing_time_ms=processing_time
            )
            
            # Return fallback intent
            fallback_intent = self._create_fallback_intent(query)
            
            return IntentExtractionResult(
                intent=fallback_intent,
                success=False,
                error_message=f"Extraction error: {str(e)}",
                processing_time_ms=processing_time
            )
    
    def _build_extraction_prompt(self, query: str, user_context: Optional[Dict[str, Any]] = None) -> str:
        """Build the prompt for intent extraction."""
        
        prompt = f"""
        Extract structured intent from this search query:
        
        Query: "{query}"
        """
        
        if user_context:
            prompt += f"\n\nUser Context:\n{json.dumps(user_context, indent=2)}"
        
        prompt += """
        
        Analyze the query and extract all relevant information into the specified JSON structure.
        Consider the user's intent, requirements, preferences, and constraints.
        
        Pay special attention to:
        - Business category (restaurant, cafe, bar, shopping, etc.)
        - Specific requirements (Wi-Fi, parking, outdoor seating, etc.)
        - Budget mentions (under ₹500, around ₹1000, etc.)
        - Location references (near me, in Delhi, Connaught Place, etc.)
        - Time preferences (open now, for dinner, late night, etc.) 
        - Mood indicators (quiet, romantic, family-friendly, etc.)
        - Group size (for 2 people, family dinner, etc.)
        - Special occasions (birthday, date, business meeting, etc.)
        
        Provide a confidence score based on how clearly the intent is expressed.
        """
        
        return prompt
    
    def _convert_to_search_intent(self, original_query: str, extracted_data: Dict[str, Any]) -> SearchIntent:
        """Convert extracted data to SearchIntent object."""
        
        # Handle location data
        location_data = extracted_data.get("location", {})
        location = None
        if location_data:
            location = LocationPreference(**location_data)
        
        # Handle time data
        time_data = extracted_data.get("time", {})
        time_pref = None
        if time_data:
            time_pref = TimePreference(**time_data)
        
        # Handle budget data
        budget_data = extracted_data.get("budget", {})
        budget = None
        if budget_data:
            budget = BudgetPreference(**budget_data)
        
        # Create SearchIntent
        intent = SearchIntent(
            original_query=original_query,
            primary_category=extracted_data.get("primary_category"),
            secondary_categories=extracted_data.get("secondary_categories", []),
            keywords=extracted_data.get("keywords", []),
            required_amenities=extracted_data.get("required_amenities", []),
            preferred_amenities=extracted_data.get("preferred_amenities", []),
            location=location,
            time=time_pref,
            budget=budget,
            mood=extracted_data.get("mood"),
            group_size=extracted_data.get("group_size"),
            occasion=extracted_data.get("occasion"),
            dietary_preferences=extracted_data.get("dietary_preferences", []),
            accessibility_needs=extracted_data.get("accessibility_needs", []),
            min_rating=extracted_data.get("min_rating"),
            verified_only=extracted_data.get("verified_only", False),
            confidence_score=extracted_data.get("confidence_score", 0.5)
        )
        
        return intent
    
    def _create_fallback_intent(self, query: str) -> SearchIntent:
        """Create a basic fallback intent when AI extraction fails."""
        
        # Simple keyword-based fallback
        query_lower = query.lower()
        
        # Try to detect category from keywords
        primary_category = None
        
        food_keywords = ["restaurant", "food", "eat", "dining", "meal", "lunch", "dinner", "breakfast"]
        cafe_keywords = ["cafe", "coffee", "tea", "bakery", "pastry"]
        bar_keywords = ["bar", "pub", "drink", "beer", "wine", "alcohol"]
        shopping_keywords = ["shop", "store", "mall", "market", "buy", "purchase"]
        
        if any(keyword in query_lower for keyword in cafe_keywords):
            primary_category = IntentCategory.CAFE
        elif any(keyword in query_lower for keyword in food_keywords):
            primary_category = IntentCategory.RESTAURANT
        elif any(keyword in query_lower for keyword in bar_keywords):
            primary_category = IntentCategory.BAR
        elif any(keyword in query_lower for keyword in shopping_keywords):
            primary_category = IntentCategory.SHOPPING
        else:
            primary_category = IntentCategory.OTHER
        
        # Extract basic keywords
        keywords = [word.strip() for word in query.split() if len(word.strip()) > 2]
        
        # Check for "open now"
        open_now = "open now" in query_lower or "open right now" in query_lower
        
        time_pref = None
        if open_now:
            time_pref = TimePreference(open_now=True)
        
        return SearchIntent(
            original_query=query,
            primary_category=primary_category,
            keywords=keywords[:10],  # Limit to first 10 words
            time=time_pref,
            confidence_score=0.3  # Low confidence for fallback
        )
    
    async def extract_batch_intents(self, queries: List[str]) -> List[IntentExtractionResult]:
        """Extract intents for multiple queries in batch."""
        
        results = []
        
        for query in queries:
            result = await self.extract_intent(query)
            results.append(result)
        
        logger.info(
            "Batch intent extraction completed",
            total_queries=len(queries),
            successful_extractions=sum(1 for r in results if r.success)
        )
        
        return results