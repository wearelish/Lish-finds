"""
Location Verification Service

Comprehensive location and business data verification system with accuracy scoring.
Ensures all location data and business information meets strict accuracy requirements.
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime, timezone
from geopy.distance import geodesic
import asyncio
import logging
from decimal import Decimal

from ..models.business import Business
from ..services.location_service import LocationService
from ..services.business_rules_engine import BusinessRulesEngine

logger = logging.getLogger(__name__)

@dataclass
class VerificationResult:
    """Result of location/business verification"""
    score: float  # 0-100 accuracy score
    is_verified: bool
    confidence_level: str  # "high", "medium", "low"
    issues: List[str]
    recommendations: List[str]
    verification_timestamp: datetime

@dataclass
class LocationAccuracy:
    """Location accuracy assessment"""
    coordinate_precision: float  # GPS precision score
    address_match: float  # Address vs coordinates match
    landmark_verification: float  # Nearby landmark validation
    accessibility_data: float  # Accessibility info accuracy

@dataclass
class BusinessDataAccuracy:
    """Business data accuracy assessment"""
    pricing_compliance: float  # Pricing rule compliance
    hours_validation: float  # Operating hours accuracy
    contact_verification: float  # Contact info validation
    service_accuracy: float  # Service/menu accuracy
class LocationVerificationService:
    """
    Comprehensive location and business data verification service
    """
    
    def __init__(self, location_service: LocationService, rules_engine: BusinessRulesEngine):
        self.location_service = location_service
        self.rules_engine = rules_engine
        self.min_movie_ticket_price = Decimal("70.00")  # Hard constraint
        
    async def verify_business_location(self, business: Business) -> VerificationResult:
        """
        Comprehensive verification of business location and data accuracy
        """
        try:
            # Parallel verification tasks
            tasks = [
                self._verify_location_accuracy(business),
                self._verify_business_data(business),
                self._verify_pricing_constraints(business),
                self._verify_temporal_accuracy(business)
            ]
            
            location_acc, business_acc, pricing_acc, temporal_acc = await asyncio.gather(*tasks)
            
            # Calculate overall score with weighted components
            overall_score = self._calculate_weighted_score(
                location_acc, business_acc, pricing_acc, temporal_acc
            )
            
            # Determine verification status
            is_verified = overall_score >= 75.0 and pricing_acc >= 95.0
            confidence_level = self._determine_confidence_level(overall_score)
            
            # Collect issues and recommendations
            issues = []
            recommendations = []
            
            if location_acc < 70:
                issues.append("Location accuracy below acceptable threshold")
                recommendations.append("Verify GPS coordinates and address details")
            
            if business_acc < 70:
                issues.append("Business data accuracy concerns")
                recommendations.append("Update business information and validate services")
            
            if pricing_acc < 95:
                issues.append("Pricing constraint violations detected")
                recommendations.append("Review and correct pricing to meet minimum requirements")
            
            return VerificationResult(
                score=overall_score,
                is_verified=is_verified,
                confidence_level=confidence_level,
                issues=issues,
                recommendations=recommendations,
                verification_timestamp=datetime.now(timezone.utc)
            )
            
        except Exception as e:
            logger.error(f"Verification failed for business {business.id}: {e}")
            return VerificationResult(
                score=0.0,
                is_verified=False,
                confidence_level="low",
                issues=[f"Verification failed: {str(e)}"],
                recommendations=["Manual verification required"],
                verification_timestamp=datetime.now(timezone.utc)
            )
    async def _verify_location_accuracy(self, business: Business) -> float:
        """
        Verify location data accuracy with multiple validation checks
        """
        try:
            score = 0.0
            max_score = 100.0
            
            # GPS coordinate precision (25 points)
            if business.latitude and business.longitude:
                # Check coordinate precision (decimal places)
                lat_precision = len(str(business.latitude).split('.')[-1])
                lng_precision = len(str(business.longitude).split('.')[-1])
                
                if lat_precision >= 6 and lng_precision >= 6:
                    score += 25.0  # High precision
                elif lat_precision >= 4 and lng_precision >= 4:
                    score += 20.0  # Medium precision
                else:
                    score += 10.0  # Low precision
            
            # Address-coordinate consistency (25 points)
            if business.address and business.latitude and business.longitude:
                # Simulate geocoding verification
                geocoded_location = await self.location_service.geocode_address(business.address)
                if geocoded_location:
                    distance = geodesic(
                        (business.latitude, business.longitude),
                        (geocoded_location.latitude, geocoded_location.longitude)
                    ).meters
                    
                    if distance <= 100:  # Within 100m
                        score += 25.0
                    elif distance <= 500:  # Within 500m
                        score += 20.0
                    elif distance <= 1000:  # Within 1km
                        score += 15.0
                    else:
                        score += 5.0
            
            # Area and locality validation (25 points)
            if business.area and business.city:
                area_info = await self.location_service.get_area_info(business.area, business.city)
                if area_info and area_info.get('is_valid'):
                    score += 25.0
                else:
                    score += 10.0
            
            # Accessibility and transport connectivity (25 points)
            if business.latitude and business.longitude:
                connectivity = await self.location_service.get_transport_connectivity(
                    business.latitude, business.longitude
                )
                if connectivity:
                    # Score based on connectivity quality
                    metro_score = min(connectivity.get('metro_stations', 0) * 5, 10)
                    bus_score = min(connectivity.get('bus_stops', 0) * 2, 10)
                    accessibility_score = 5 if connectivity.get('wheelchair_accessible') else 0
                    
                    score += metro_score + bus_score + accessibility_score
            
            return min(score, max_score)
            
        except Exception as e:
            logger.error(f"Location accuracy verification failed: {e}")
            return 0.0
    async def _verify_business_data(self, business: Business) -> float:
        """
        Verify business data accuracy and completeness
        """
        try:
            score = 0.0
            
            # Contact information validation (25 points)
            contact_score = 0.0
            if business.phone and len(business.phone) >= 10:
                contact_score += 15.0
            if business.email and '@' in business.email:
                contact_score += 10.0
            score += contact_score
            
            # Operating hours validation (25 points)
            if business.operating_hours:
                hours_validation = self.rules_engine.validate_operating_hours(
                    business.operating_hours, business.city, business.state
                )
                if hours_validation.is_valid:
                    score += 25.0
                else:
                    score += 10.0
            
            # Services/amenities completeness (25 points)
            if hasattr(business, 'services') and business.services:
                service_count = len(business.services)
                if service_count >= 5:
                    score += 25.0
                elif service_count >= 3:
                    score += 20.0
                elif service_count >= 1:
                    score += 15.0
            
            # Category-specific validation (25 points)
            category_score = 0.0
            if business.category:
                if business.category == "cinema":
                    # Movie theaters must have screen count, sound system info
                    if hasattr(business, 'screens') and business.screens > 0:
                        category_score += 15.0
                    if hasattr(business, 'sound_systems') and business.sound_systems:
                        category_score += 10.0
                elif business.category == "restaurant":
                    # Restaurants must have cuisine type, capacity info
                    if hasattr(business, 'cuisine_types') and business.cuisine_types:
                        category_score += 15.0
                    if hasattr(business, 'seating_capacity') and business.seating_capacity > 0:
                        category_score += 10.0
                else:
                    category_score += 20.0  # Basic category validation
            
            score += category_score
            return min(score, 100.0)
            
        except Exception as e:
            logger.error(f"Business data verification failed: {e}")
            return 0.0
    async def _verify_pricing_constraints(self, business: Business) -> float:
        """
        Strict verification of pricing constraints, especially movie ticket minimum
        """
        try:
            score = 100.0  # Start with perfect score, deduct for violations
            violations = []
            
            # Movie ticket price validation (CRITICAL)
            if business.category == "cinema":
                if hasattr(business, 'ticket_prices') and business.ticket_prices:
                    for show_type, price in business.ticket_prices.items():
                        if isinstance(price, (int, float, Decimal)):
                            price = Decimal(str(price))
                            if price < self.min_movie_ticket_price:
                                violations.append(
                                    f"Movie ticket price ₹{price} below minimum ₹{self.min_movie_ticket_price} for {show_type}"
                                )
                                score -= 50.0  # Heavy penalty for movie ticket violations
                else:
                    violations.append("Cinema missing ticket price information")
                    score -= 30.0
            
            # General pricing validation
            if hasattr(business, 'price_range') and business.price_range:
                price_validation = self.rules_engine.validate_pricing(
                    business.price_range, business.category, business.city, business.state
                )
                if not price_validation.is_valid:
                    violations.extend(price_validation.errors)
                    score -= len(price_validation.errors) * 10.0
            
            # Dynamic pricing compliance
            if hasattr(business, 'surge_pricing_enabled') and business.surge_pricing_enabled:
                # Ensure surge pricing doesn't violate minimum constraints
                if business.category == "cinema":
                    base_price = min(business.ticket_prices.values()) if business.ticket_prices else 0
                    if base_price > 0 and base_price < self.min_movie_ticket_price:
                        violations.append("Base price before surge violates minimum movie ticket price")
                        score -= 40.0
            
            # Log violations for monitoring
            if violations:
                logger.warning(f"Pricing violations for business {business.id}: {violations}")
            
            return max(score, 0.0)
            
        except Exception as e:
            logger.error(f"Pricing constraint verification failed: {e}")
            return 0.0
    
    async def _verify_temporal_accuracy(self, business: Business) -> float:
        """
        Verify temporal aspects like operating hours, seasonal availability
        """
        try:
            score = 0.0
            
            # Current time validation (30 points)
            current_time = datetime.now()
            if business.operating_hours:
                is_open = self._is_currently_open(business.operating_hours, current_time)
                # Score based on whether the business should be open
                score += 30.0 if is_open is not None else 15.0
            
            # Seasonal availability (35 points)
            if hasattr(business, 'seasonal_availability'):
                # Check if current season is handled
                current_month = current_time.month
                if current_month in business.seasonal_availability:
                    score += 35.0
                else:
                    score += 20.0
            else:
                score += 25.0  # Default score if no seasonal data
            
            # Special hours validation (35 points)
            if hasattr(business, 'special_hours') and business.special_hours:
                # Check for upcoming holidays/events
                score += 35.0
            else:
                score += 25.0
            
            return min(score, 100.0)
            
        except Exception as e:
            logger.error(f"Temporal accuracy verification failed: {e}")
            return 0.0
    def _calculate_weighted_score(
        self, location_acc: float, business_acc: float, 
        pricing_acc: float, temporal_acc: float
    ) -> float:
        """
        Calculate weighted overall accuracy score
        """
        weights = {
            'location': 0.25,      # 25% - Location accuracy
            'business': 0.20,      # 20% - Business data quality
            'pricing': 0.35,       # 35% - Pricing compliance (highest weight)
            'temporal': 0.20       # 20% - Temporal accuracy
        }
        
        weighted_score = (
            location_acc * weights['location'] +
            business_acc * weights['business'] +
            pricing_acc * weights['pricing'] +
            temporal_acc * weights['temporal']
        )
        
        return min(weighted_score, 100.0)
    
    def _determine_confidence_level(self, score: float) -> str:
        """
        Determine confidence level based on overall score
        """
        if score >= 90:
            return "high"
        elif score >= 70:
            return "medium"
        else:
            return "low"
    
    def _is_currently_open(self, operating_hours: Dict, current_time: datetime) -> Optional[bool]:
        """
        Check if business is currently open based on operating hours
        """
        try:
            current_day = current_time.strftime("%A").lower()
            if current_day in operating_hours:
                hours = operating_hours[current_day]
                if hours and isinstance(hours, dict):
                    open_time = hours.get('open')
                    close_time = hours.get('close')
                    if open_time and close_time:
                        current_time_str = current_time.strftime("%H:%M")
                        return open_time <= current_time_str <= close_time
            return None
        except Exception:
            return None
    
    async def batch_verify_businesses(self, businesses: List[Business]) -> Dict[str, VerificationResult]:
        """
        Batch verification of multiple businesses
        """
        tasks = [self.verify_business_location(business) for business in businesses]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        verification_results = {}
        for i, result in enumerate(results):
            business_id = businesses[i].id
            if isinstance(result, Exception):
                verification_results[business_id] = VerificationResult(
                    score=0.0,
                    is_verified=False,
                    confidence_level="low",
                    issues=[f"Verification error: {str(result)}"],
                    recommendations=["Manual review required"],
                    verification_timestamp=datetime.now(timezone.utc)
                )
            else:
                verification_results[business_id] = result
        
        return verification_results