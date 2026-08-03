"""
Enhanced Search Service

Provides location-aware search with accurate distance calculation and filtering including:
- Multi-modal distance calculation (walking, driving, metro, etc.)
- Real-time travel time estimation
- Location-based result ranking
- Transport accessibility analysis
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import math
import logging

from .location_service import Location, LocationService
from .area_mapping_service import AreaMappingService, SearchRadius
from .business_rules_engine import BusinessRulesEngine
from .dynamic_pricing_service import DynamicPricingService, DemandLevel, WeatherCondition
from .availability_service import AvailabilityService
from .location_verification_service import LocationVerificationService
from .data_accuracy_service import DataAccuracyService

logger = logging.getLogger(__name__)


@dataclass
class SearchFilters:
    """Search filter configuration"""
    max_distance_km: float = 10.0
    max_travel_time_minutes: int = 30
    transport_modes: List[str] = None
    price_range: Optional[Tuple[float, float]] = None
    business_types: Optional[List[str]] = None
    open_now: bool = False
    min_rating: float = 0.0
    accessibility_required: bool = False
    
    def __post_init__(self):
        if self.transport_modes is None:
            self.transport_modes = ["driving"]


@dataclass 
class SearchResult:
    """Enhanced search result with location intelligence"""
    business_id: str
    name: str
    business_type: str
    location: Location
    
    # Distance and travel information
    distance_km: float
    travel_times: Dict[str, int]  # Transport mode -> time in minutes
    accessibility_score: float
    
    # Business information
    rating: float
    price_range: str
    is_open: bool
    operating_hours: Dict[str, Any]
    
    # Location context
    area_info: Dict[str, Any]
    landmarks_nearby: List[str]
    transport_options: List[str]
    
    # Accuracy and relevance
    location_accuracy: str
    relevance_score: float
    verification_score: float
    data_quality_score: float
    is_verified: bool
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "business_id": self.business_id,
            "name": self.name,
            "business_type": self.business_type,
            "location": self.location.to_dict(),
            "distance_km": self.distance_km,
            "travel_times": self.travel_times,
            "accessibility_score": self.accessibility_score,
            "rating": self.rating,
            "price_range": self.price_range,
            "is_open": self.is_open,
            "operating_hours": self.operating_hours,
            "area_info": self.area_info,
            "landmarks_nearby": self.landmarks_nearby,
            "transport_options": self.transport_options,
            "location_accuracy": self.location_accuracy,
            "relevance_score": self.relevance_score,
            "verification_score": self.verification_score,
            "data_quality_score": self.data_quality_score,
            "is_verified": self.is_verified
        }
        
        # Add enhanced data if available
        if hasattr(self, '_enhanced_data'):
            result.update(self._enhanced_data)
        
        return result


class EnhancedSearchService:
    """Enhanced location-aware search service"""
    
    def __init__(self):
        self.location_service = LocationService()
        self.area_mapping = AreaMappingService()
        self.business_rules = BusinessRulesEngine()
        self.dynamic_pricing = DynamicPricingService()
        self.availability_service = AvailabilityService()
        self.location_verification = LocationVerificationService(
            self.location_service, self.business_rules
        )
        self.data_accuracy = DataAccuracyService()
        self.search_radius = SearchRadius()
    
    def search_businesses(self, user_location: Location, query: str = "",
                         filters: SearchFilters = None) -> List[SearchResult]:
        """Search for businesses with enhanced location intelligence"""
        
        if filters is None:
            filters = SearchFilters()
        
        # Get mock business data (in production, this would query the database)
        mock_businesses = self._get_mock_businesses(user_location, filters)
        
        results = []
        
        for business in mock_businesses:
            # Calculate distance and travel times
            business_location = Location(
                latitude=business["latitude"],
                longitude=business["longitude"],
                address=business.get("address"),
                city=business.get("city"),
                area=business.get("area")
            )
            
            distance = self.location_service.calculate_distance(
                user_location, business_location
            )
            
            # Skip if beyond maximum distance
            if distance > filters.max_distance_km:
                continue
            
            # Calculate travel times for different modes
            travel_times = {}
            accessible_modes = []
            
            for mode in filters.transport_modes:
                travel_info = self.location_service.calculate_travel_time(
                    user_location, business_location, mode
                )
                
                travel_time = travel_info["travel_time_minutes"]
                travel_times[mode] = travel_time
                
                # Check if within time limit
                if travel_time <= filters.max_travel_time_minutes:
                    accessible_modes.append(mode)
            
            # Skip if not accessible by any preferred transport mode
            if not accessible_modes:
                continue
            
            # Get area information
            area_info = self.area_mapping.get_area_info(business_location)
            area_dict = area_info.to_dict() if area_info else {}
            
            # Calculate accessibility score
            accessibility_score = self.area_mapping.get_accessibility_score(
                business_location
            )["overall_score"]
            
            # Get real-time availability and pricing
            availability = self.availability_service.get_business_availability(
                business["id"], business["type"], business_location
            )
            
            is_open = availability.current_status.value != "closed"
            
            # Skip if open_now filter is set and business is closed
            if filters.open_now and not is_open:
                continue
            
            # Calculate dynamic pricing
            base_price = business.get("base_ticket_price", business.get("avg_cost_per_person", 0))
            if base_price > 0:
                pricing_info = self.dynamic_pricing.calculate_real_time_pricing(
                    business["id"], base_price, business["type"], business_location
                )
                dynamic_price = pricing_info["final_price"]
                price_factors = pricing_info.get("factors_applied", [])
            else:
                dynamic_price = 0
                price_factors = []
            
            # Calculate relevance score
            relevance_score = self._calculate_relevance_score(
                business, user_location, distance, query, filters
            )
            
            # VERIFICATION AND DATA ACCURACY ASSESSMENT
            verification_score = 75.0  # Default score
            data_quality_score = 75.0  # Default score
            is_verified = True  # Default assumption
            
            try:
                # Convert business dict to mock business object for verification
                from ..models.business import Business as BusinessModel
                business_obj = BusinessModel(
                    id=business["id"],
                    name=business["name"],
                    category=business["type"],
                    latitude=business["latitude"],
                    longitude=business["longitude"],
                    address=business.get("address"),
                    city=business.get("city"),
                    state=business.get("state"),
                    phone=business.get("phone"),
                    email=business.get("email"),
                    operating_hours=business.get("hours", {}),
                    price_range=business.get("price_range"),
                    ticket_prices=business.get("ticket_prices", {}) if business["type"] == "cinema" else None
                )
                
                # Perform synchronous verification assessment using async wrapper
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                verification_result = loop.run_until_complete(
                    self.location_verification.verify_business_location(business_obj)
                )
                verification_score = verification_result.score
                is_verified = verification_result.is_verified
                
                # Perform data quality assessment
                quality_metrics = loop.run_until_complete(
                    self.data_accuracy.assess_data_quality(business_obj)
                )
                data_quality_score = quality_metrics.overall_score
                
                loop.close()
                
            except Exception as e:
                logger.warning(f"Verification assessment failed for business {business['id']}: {e}")
                # Use default scores if verification fails
            
            # Apply verification score multiplier to relevance
            if verification_score < 50:
                relevance_score *= 0.7  # Reduce relevance for low-quality data
            elif verification_score >= 90:
                relevance_score *= 1.1  # Boost high-quality verified businesses
            
            # Create search result
            result = SearchResult(
                business_id=business["id"],
                name=business["name"],
                business_type=business["type"],
                location=business_location,
                distance_km=distance,
                travel_times=travel_times,
                accessibility_score=accessibility_score,
                rating=business.get("rating", 0.0),
                price_range=business.get("price_range", "₹₹"),
                is_open=is_open,
                operating_hours=business.get("hours", {}),
                area_info=area_dict,
                landmarks_nearby=business.get("landmarks", []),
                transport_options=accessible_modes,
                location_accuracy="high",
                relevance_score=relevance_score,
                verification_score=verification_score,
                data_quality_score=data_quality_score,
                is_verified=is_verified
            )
            
            # Add dynamic pricing and availability info
            result_dict = result.to_dict()
            result_dict.update({
                "availability": {
                    "status": availability.current_status.value,
                    "occupancy_percent": availability.current_occupancy_percent,
                    "available_capacity": availability.current_availability,
                    "next_available_slots": [
                        {
                            "time": slot.start_time.isoformat(),
                            "duration_minutes": int((slot.end_time - slot.start_time).total_seconds() / 60),
                            "available_spots": slot.available
                        }
                        for slot in availability.time_slots[:3]  # Show next 3 slots
                        if slot.available > 0
                    ]
                },
                "pricing": {
                    "base_price": base_price,
                    "current_price": dynamic_price,
                    "price_change_percent": ((dynamic_price - base_price) / base_price * 100) if base_price > 0 else 0,
                    "price_factors": price_factors[:3],  # Show top 3 factors
                    "next_price_update": (datetime.now() + timedelta(minutes=15)).isoformat()
                }
            })
            
            # Convert back to SearchResult with enhanced data
            enhanced_result = SearchResult(**{
                k: v for k, v in result_dict.items() 
                if k in SearchResult.__dataclass_fields__
            })
            enhanced_result._enhanced_data = {
                "availability": result_dict["availability"],
                "pricing": result_dict["pricing"]
            }
            
            results.append(enhanced_result)
        
        # Sort by relevance score
        results.sort(key=lambda x: x.relevance_score, reverse=True)
        
        return results
    
    def find_businesses_by_type(self, user_location: Location, business_type: str,
                               max_distance_km: float = 5.0,
                               transport_mode: str = "driving") -> List[SearchResult]:
        """Find businesses of specific type with location intelligence"""
        
        filters = SearchFilters(
            max_distance_km=max_distance_km,
            transport_modes=[transport_mode],
            business_types=[business_type]
        )
        
        return self.search_businesses(user_location, "", filters)
    
    def get_business_recommendations(self, user_location: Location,
                                   user_preferences: Dict[str, Any]) -> List[SearchResult]:
        """Get personalized business recommendations based on location and preferences"""
        
        # Extract preferences
        preferred_types = user_preferences.get("business_types", ["restaurant", "movie_theater"])
        max_budget = user_preferences.get("max_budget", 1000)
        transport_mode = user_preferences.get("transport_mode", "driving")
        max_distance = user_preferences.get("max_distance_km", 10.0)
        
        all_results = []
        
        # Search for each preferred business type
        for business_type in preferred_types:
            filters = SearchFilters(
                max_distance_km=max_distance,
                transport_modes=[transport_mode],
                business_types=[business_type],
                price_range=(0, max_budget)
            )
            
            type_results = self.search_businesses(user_location, "", filters)
            
            # Boost relevance for preferred types
            for result in type_results:
                result.relevance_score *= 1.2
            
            all_results.extend(type_results[:3])  # Top 3 per type
        
        # Remove duplicates and sort
        unique_results = {r.business_id: r for r in all_results}.values()
        sorted_results = sorted(unique_results, key=lambda x: x.relevance_score, reverse=True)
        
        return sorted_results[:10]
    
    def analyze_location_viability(self, location: Location, 
                                 business_type: str) -> Dict[str, Any]:
        """Analyze location viability for a business type"""
        
        # Get area characteristics
        area_info = self.area_mapping.get_area_info(location)
        accessibility = self.area_mapping.get_accessibility_score(location)
        
        # Calculate catchment area
        catchment = self.area_mapping.calculate_catchment_area(
            location, ["walking", "driving", "metro"]
        )
        
        # Get business constraints
        constraints = self.business_rules.get_location_specific_constraints(
            business_type, location
        )
        
        # Analyze competition (mock data)
        competition_analysis = self._analyze_competition(location, business_type)
        
        # Calculate viability score
        viability_score = self._calculate_viability_score(
            area_info, accessibility, catchment, constraints, competition_analysis
        )
        
        return {
            "location": location.to_dict(),
            "business_type": business_type,
            "viability_score": viability_score,
            "area_characteristics": area_info.to_dict() if area_info else {},
            "accessibility_analysis": accessibility,
            "catchment_analysis": catchment,
            "business_constraints": constraints,
            "competition_analysis": competition_analysis,
            "recommendations": self._generate_location_recommendations(
                viability_score, area_info, constraints
            )
        }
    
    def _get_mock_businesses(self, user_location: Location, 
                           filters: SearchFilters) -> List[Dict[str, Any]]:
        """Generate realistic mock business data based on location"""
        
        # Import here to avoid circular imports
        from ..data.realistic_business_data import RealisticBusinessDataGenerator
        from ..data.city_specific_data import CitySpecificDataProvider
        
        city = user_location.city or "Mumbai"
        
        # Try to get real city data first
        city_data_provider = CitySpecificDataProvider()
        city_data = city_data_provider.get_city_data(city)
        
        businesses = []
        
        # Get real movie theaters if available
        if city_data.get("movie_theaters"):
            for i, theater_data in enumerate(city_data["movie_theaters"]):
                theater = {
                    "id": f"theater_{i+1}",
                    "name": theater_data["name"],
                    "type": "movie_theater",
                    "latitude": theater_data["location"]["lat"],
                    "longitude": theater_data["location"]["lng"],
                    "address": f"{theater_data['area']}, {city}",
                    "city": city,
                    "area": theater_data["area"],
                    "rating": theater_data.get("rating", 4.2),
                    "price_range": self._convert_to_price_range(theater_data["pricing"]["regular_2d"]),
                    "base_ticket_price": theater_data["pricing"]["regular_2d"],  # Always ≥ ₹70
                    "premium_price": theater_data["pricing"].get("premium_2d", theater_data["pricing"]["regular_2d"] * 1.5),
                    "imax_price": theater_data["pricing"].get("imax", theater_data["pricing"]["regular_2d"] * 2.5),
                    "screens": theater_data.get("screens", 6),
                    "amenities": theater_data.get("amenities", []),
                    "hours": {"monday": "09:00-23:30", "tuesday": "09:00-23:30"},
                    "landmarks": [theater_data["area"]]
                }
                businesses.append(theater)
        
        # Get real restaurants if available
        if city_data.get("restaurants"):
            for i, restaurant_data in enumerate(city_data["restaurants"]):
                restaurant = {
                    "id": f"restaurant_{i+1}",
                    "name": restaurant_data["name"],
                    "type": "restaurant",
                    "latitude": restaurant_data["location"]["lat"],
                    "longitude": restaurant_data["location"]["lng"],
                    "address": f"{restaurant_data['area']}, {city}",
                    "city": city,
                    "area": restaurant_data["area"],
                    "rating": restaurant_data.get("rating", 4.0),
                    "price_range": self._convert_to_price_range(restaurant_data["avg_cost_per_person"]),
                    "avg_cost_per_person": restaurant_data["avg_cost_per_person"],
                    "cuisine": restaurant_data.get("cuisine", ["Multi-cuisine"]),
                    "restaurant_type": restaurant_data.get("type", "casual_dining"),
                    "hours": {"monday": "12:00-23:00", "tuesday": "12:00-23:00"},
                    "landmarks": [restaurant_data["area"]]
                }
                businesses.append(restaurant)
        
        # Get real shopping malls if available
        if city_data.get("shopping_malls"):
            for i, mall_data in enumerate(city_data["shopping_malls"]):
                mall = {
                    "id": f"mall_{i+1}",
                    "name": mall_data["name"],
                    "type": "shopping_mall",
                    "latitude": mall_data["location"]["lat"],
                    "longitude": mall_data["location"]["lng"],
                    "address": f"{mall_data['area']}, {city}",
                    "city": city,
                    "area": mall_data["area"],
                    "rating": mall_data.get("rating", 4.0),
                    "price_range": "₹₹₹" if mall_data.get("luxury_brands") else "₹₹",
                    "floors": mall_data.get("floors", 4),
                    "stores": mall_data.get("stores", 150),
                    "anchor_stores": mall_data.get("anchor_stores", []),
                    "hours": {"monday": "10:00-22:00", "tuesday": "10:00-22:00"},
                    "landmarks": [mall_data["area"], "Shopping District"]
                }
                businesses.append(mall)
        
        # If no real data available, generate realistic mock data
        if not businesses:
            data_generator = RealisticBusinessDataGenerator()
            
            # Generate realistic data based on location
            mock_theaters = data_generator.generate_movie_theaters(user_location, 2)
            mock_restaurants = data_generator.generate_restaurants(user_location, 4)
            mock_malls = data_generator.generate_shopping_malls(user_location, 1)
            
            # Convert to expected format
            for theater in mock_theaters:
                businesses.append({
                    "id": theater["id"],
                    "name": theater["name"],
                    "type": "movie_theater",
                    "latitude": theater["location"]["latitude"],
                    "longitude": theater["location"]["longitude"],
                    "address": theater["location"].get("address", f"{city}"),
                    "city": city,
                    "area": theater["location"].get("area", "City Center"),
                    "rating": theater["rating"],
                    "price_range": self._convert_to_price_range(theater["pricing"]["regular_2d"]),
                    "base_ticket_price": theater["pricing"]["regular_2d"],
                    "hours": theater["operating_hours"],
                    "landmarks": [theater["location"].get("area", "")]
                })
            
            for restaurant in mock_restaurants:
                businesses.append({
                    "id": restaurant["id"],
                    "name": restaurant["name"],
                    "type": "restaurant",
                    "latitude": restaurant["location"]["latitude"],
                    "longitude": restaurant["location"]["longitude"],
                    "address": restaurant["location"].get("address", f"{city}"),
                    "city": city,
                    "area": restaurant["location"].get("area", "Restaurant District"),
                    "rating": restaurant["rating"],
                    "price_range": restaurant["pricing"]["price_range"],
                    "avg_cost_per_person": restaurant["pricing"]["average_cost_per_person"],
                    "cuisine": restaurant.get("cuisine", ["Multi-cuisine"]),
                    "hours": restaurant["operating_hours"],
                    "landmarks": [restaurant["location"].get("area", "")]
                })
        
        # Filter by business type if specified
        if filters.business_types:
            businesses = [
                b for b in businesses 
                if b["type"] in filters.business_types
            ]
        
        return businesses
    
    def _convert_to_price_range(self, avg_cost: float) -> str:
        """Convert average cost to price range symbols"""
        
        if avg_cost < 300:
            return "₹"
        elif avg_cost < 800:
            return "₹₹"
        elif avg_cost < 1500:
            return "₹₹₹"
        else:
            return "₹₹₹₹"
    
    def _check_if_open(self, business: Dict[str, Any], current_time: datetime) -> bool:
        """Check if business is currently open (mock implementation)"""
        
        # For movie theaters, typically open 9 AM to 11:30 PM
        if business["type"] == "movie_theater":
            current_hour = current_time.hour
            return 9 <= current_hour <= 23
        
        # For restaurants, typically open 12 PM to 11 PM
        elif business["type"] == "restaurant":
            current_hour = current_time.hour
            return 12 <= current_hour <= 23
        
        # For malls, typically open 10 AM to 10 PM
        elif business["type"] == "shopping_mall":
            current_hour = current_time.hour
            return 10 <= current_hour <= 22
        
        # Default: assume open
        return True
    
    def _calculate_relevance_score(self, business: Dict[str, Any], 
                                 user_location: Location, distance: float,
                                 query: str, filters: SearchFilters) -> float:
        """Calculate relevance score for search result"""
        
        score = 0.0
        
        # Distance factor (closer is better)
        if distance <= 1.0:
            score += 10.0
        elif distance <= 3.0:
            score += 8.0
        elif distance <= 5.0:
            score += 6.0
        elif distance <= 10.0:
            score += 4.0
        else:
            score += 2.0
        
        # Rating factor
        score += business.get("rating", 0.0) * 2.0
        
        # Price range matching (if specified)
        if filters.price_range:
            business_price = business.get("avg_cost_per_person", business.get("base_ticket_price", 0))
            min_price, max_price = filters.price_range
            
            if min_price <= business_price <= max_price:
                score += 5.0
            elif business_price < min_price:
                score += 2.0  # Cheaper than expected
            else:
                score -= 2.0  # More expensive
        
        # Query matching (simple keyword matching)
        if query:
            query_words = query.lower().split()
            business_text = f"{business['name']} {business.get('cuisine', '')} {business['type']}".lower()
            
            for word in query_words:
                if word in business_text:
                    score += 3.0
        
        # Area type bonus
        area_type = business.get("area", "").lower()
        if "commercial" in area_type or "entertainment" in area_type:
            score += 2.0
        
        # Landmark proximity bonus
        landmarks = business.get("landmarks", [])
        if "metro" in str(landmarks).lower():
            score += 1.5
        if "mall" in str(landmarks).lower():
            score += 1.0
        
        return max(0.0, score)
    
    def _analyze_competition(self, location: Location, 
                           business_type: str) -> Dict[str, Any]:
        """Analyze competition in the area (mock analysis)"""
        
        # Mock competition data based on location tier
        tier = self.business_rules._get_location_tier(location)
        
        competition_levels = {
            "premium_metro": {"density": "very_high", "count": 15, "quality": "high"},
            "metro": {"density": "high", "count": 10, "quality": "medium"},
            "tier1": {"density": "medium", "count": 6, "quality": "medium"},
            "tier2": {"density": "low", "count": 3, "quality": "low"},
            "tier3": {"density": "very_low", "count": 1, "quality": "low"}
        }
        
        competition = competition_levels.get(tier, competition_levels["tier2"])
        
        return {
            "competitor_density": competition["density"],
            "estimated_competitors_5km": competition["count"],
            "average_competitor_quality": competition["quality"],
            "market_saturation": "high" if competition["count"] > 8 else "medium" if competition["count"] > 4 else "low"
        }
    
    def _calculate_viability_score(self, area_info, accessibility, catchment, 
                                 constraints, competition) -> float:
        """Calculate business location viability score"""
        
        score = 5.0  # Base score
        
        # Area characteristics
        if area_info:
            if area_info.area_type in ["commercial", "mixed"]:
                score += 2.0
            score += area_info.safety_rating * 0.5
            if area_info.commercial_density == "high":
                score += 1.0
        
        # Accessibility
        score += accessibility["overall_score"] * 0.3
        
        # Population reach
        population = catchment.get("estimated_population_reach", 0)
        if population > 100000:
            score += 2.0
        elif population > 50000:
            score += 1.0
        
        # Competition factor
        if competition["market_saturation"] == "low":
            score += 2.0
        elif competition["market_saturation"] == "high":
            score -= 1.0
        
        return min(10.0, max(0.0, score))
    
    def _generate_location_recommendations(self, viability_score: float, 
                                         area_info, constraints) -> List[str]:
        """Generate recommendations for location improvement"""
        
        recommendations = []
        
        if viability_score < 6.0:
            recommendations.append("Consider locations with better accessibility")
            recommendations.append("Look for areas with higher footfall")
        
        if area_info and area_info.parking_availability == "limited":
            recommendations.append("Negotiate parking arrangements with nearby facilities")
        
        if area_info and area_info.safety_rating < 3.5:
            recommendations.append("Consider security arrangements for evening operations")
        
        recommendations.append("Validate pricing against local competition")
        recommendations.append("Ensure compliance with local regulations")
        
        return recommendations
    async def get_verification_report(self, business_ids: List[str]) -> Dict[str, Any]:
        """
        Generate comprehensive verification report for businesses
        """
        try:
            # Get business data for verification
            mock_businesses = self._get_all_businesses()
            businesses_to_verify = [b for b in mock_businesses if b["id"] in business_ids]
            
            # Convert to business objects
            business_objects = []
            for business in businesses_to_verify:
                from ..models.business import Business as BusinessModel
                business_obj = BusinessModel(
                    id=business["id"],
                    name=business["name"],
                    category=business["type"],
                    latitude=business["latitude"],
                    longitude=business["longitude"],
                    address=business.get("address"),
                    city=business.get("city"),
                    state=business.get("state"),
                    phone=business.get("phone"),
                    email=business.get("email"),
                    operating_hours=business.get("hours", {}),
                    price_range=business.get("price_range"),
                    ticket_prices=business.get("ticket_prices", {}) if business["type"] == "cinema" else None
                )
                business_objects.append(business_obj)
            
            # Batch verification
            verification_results = await self.location_verification.batch_verify_businesses(business_objects)
            
            # Batch data quality assessment
            quality_results = {}
            for business_obj in business_objects:
                quality_metrics = await self.data_accuracy.assess_data_quality(business_obj)
                field_analyses = await self.data_accuracy.analyze_field_quality(business_obj)
                quality_results[business_obj.id] = {
                    "metrics": quality_metrics,
                    "field_analyses": field_analyses
                }
            
            # Compile comprehensive report
            report = {
                "report_timestamp": datetime.now().isoformat(),
                "total_businesses": len(business_ids),
                "verification_summary": {
                    "verified": sum(1 for result in verification_results.values() if result.is_verified),
                    "high_confidence": sum(1 for result in verification_results.values() if result.confidence_level == "high"),
                    "medium_confidence": sum(1 for result in verification_results.values() if result.confidence_level == "medium"),
                    "low_confidence": sum(1 for result in verification_results.values() if result.confidence_level == "low"),
                    "avg_verification_score": sum(result.score for result in verification_results.values()) / len(verification_results) if verification_results else 0
                },
                "data_quality_summary": {
                    "high_quality": sum(1 for result in quality_results.values() if result["metrics"].overall_score >= 80),
                    "medium_quality": sum(1 for result in quality_results.values() if 60 <= result["metrics"].overall_score < 80),
                    "low_quality": sum(1 for result in quality_results.values() if result["metrics"].overall_score < 60),
                    "avg_completeness": sum(result["metrics"].completeness_score for result in quality_results.values()) / len(quality_results) if quality_results else 0,
                    "avg_consistency": sum(result["metrics"].consistency_score for result in quality_results.values()) / len(quality_results) if quality_results else 0,
                    "avg_validity": sum(result["metrics"].validity_score for result in quality_results.values()) / len(quality_results) if quality_results else 0
                },
                "critical_issues": [],
                "business_details": {}
            }
            
            # Collect critical issues and detailed business info
            for business_id in business_ids:
                verification = verification_results.get(business_id)
                quality = quality_results.get(business_id)
                
                if verification and quality:
                    # Check for critical issues
                    if verification.score < 50:
                        report["critical_issues"].append({
                            "business_id": business_id,
                            "type": "low_verification_score",
                            "details": f"Verification score: {verification.score:.1f}",
                            "issues": verification.issues
                        })
                    
                    if quality["metrics"].overall_score < 50:
                        report["critical_issues"].append({
                            "business_id": business_id,
                            "type": "low_data_quality",
                            "details": f"Data quality score: {quality['metrics'].overall_score:.1f}",
                            "issues": [f.issues for f in quality["field_analyses"] if not f.is_valid]
                        })
                    
                    # Movie ticket price violations
                    business_obj = next((b for b in business_objects if b.id == business_id), None)
                    if business_obj and business_obj.category == "cinema":
                        if hasattr(business_obj, 'ticket_prices') and business_obj.ticket_prices:
                            violations = []
                            for show_type, price in business_obj.ticket_prices.items():
                                if isinstance(price, (int, float)) and price < 70:
                                    violations.append(f"{show_type}: ₹{price}")
                            
                            if violations:
                                report["critical_issues"].append({
                                    "business_id": business_id,
                                    "type": "movie_ticket_price_violation",
                                    "details": f"Prices below ₹70 minimum: {', '.join(violations)}",
                                    "severity": "CRITICAL"
                                })
                    
                    # Detailed business info
                    report["business_details"][business_id] = {
                        "verification": {
                            "score": verification.score,
                            "is_verified": verification.is_verified,
                            "confidence": verification.confidence_level,
                            "issues": verification.issues,
                            "recommendations": verification.recommendations
                        },
                        "data_quality": {
                            "overall_score": quality["metrics"].overall_score,
                            "completeness": quality["metrics"].completeness_score,
                            "consistency": quality["metrics"].consistency_score,
                            "validity": quality["metrics"].validity_score,
                            "accuracy": quality["metrics"].accuracy_score,
                            "freshness": quality["metrics"].freshness_score,
                            "field_issues": [
                                {
                                    "field": f.field_name,
                                    "score": f.quality_score,
                                    "issues": f.issues,
                                    "suggestions": f.suggestions
                                }
                                for f in quality["field_analyses"] if f.issues
                            ]
                        }
                    }
            
            return report
            
        except Exception as e:
            logger.error(f"Verification report generation failed: {e}")
            return {
                "error": f"Report generation failed: {str(e)}",
                "report_timestamp": datetime.now().isoformat()
            }
    
    def _get_all_businesses(self) -> List[Dict[str, Any]]:
        """
        Get all businesses for verification (mock implementation)
        """
        # This would typically query the database
        # For now, return a subset of mock data with known movie theaters
        return [
            {
                "id": "cinema_001",
                "name": "PVR Cinemas Phoenix",
                "type": "cinema",
                "latitude": 19.0896,
                "longitude": 72.8656,
                "address": "Phoenix Marketcity, Kurla West, Mumbai",
                "city": "Mumbai",
                "state": "Maharashtra",
                "phone": "+91-9876543210",
                "email": "info@pvrcinemas.com",
                "hours": {
                    "monday": {"open": "09:00", "close": "23:00"},
                    "tuesday": {"open": "09:00", "close": "23:00"},
                    "wednesday": {"open": "09:00", "close": "23:00"},
                    "thursday": {"open": "09:00", "close": "23:00"},
                    "friday": {"open": "09:00", "close": "23:00"},
                    "saturday": {"open": "09:00", "close": "23:00"},
                    "sunday": {"open": "09:00", "close": "23:00"}
                },
                "ticket_prices": {
                    "regular": 150,
                    "gold": 250,
                    "recliner": 350,
                    "imax": 400
                },
                "screens": 8,
                "price_range": "₹₹₹"
            },
            {
                "id": "cinema_002",
                "name": "INOX Leisure City",
                "type": "cinema",
                "latitude": 28.5355,
                "longitude": 77.3910,
                "address": "Leisure Valley, Sector 29, Gurgaon",
                "city": "Gurgaon", 
                "state": "Haryana",
                "phone": "+91-9876543211",
                "email": "info@inoxmovies.com",
                "ticket_prices": {
                    "regular": 180,
                    "premium": 280,
                    "4dx": 450
                },
                "screens": 6
            }
        ]