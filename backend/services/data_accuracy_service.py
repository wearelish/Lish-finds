"""
Data Accuracy Service

Advanced data quality assessment and accuracy scoring system.
Provides comprehensive analysis of data quality across all business attributes.
"""

from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
import re
import logging
from statistics import mean, stdev

from ..models.business import Business

logger = logging.getLogger(__name__)

@dataclass
class DataQualityMetrics:
    """Comprehensive data quality metrics"""
    completeness_score: float  # 0-100, percentage of required fields filled
    consistency_score: float   # 0-100, internal data consistency
    validity_score: float      # 0-100, data format and range validity
    accuracy_score: float      # 0-100, estimated real-world accuracy
    freshness_score: float     # 0-100, data recency score
    overall_score: float       # 0-100, weighted overall quality

@dataclass
class FieldAnalysis:
    """Analysis of individual field quality"""
    field_name: str
    is_present: bool
    is_valid: bool
    quality_score: float
    issues: List[str]
    suggestions: List[str]

class DataAccuracyService:
    """
    Advanced data accuracy and quality assessment service
    """
    
    def __init__(self):
        self.required_fields = {
            'all': ['name', 'address', 'city', 'state', 'category'],
            'cinema': ['name', 'address', 'city', 'state', 'category', 'ticket_prices', 'screens'],
            'restaurant': ['name', 'address', 'city', 'state', 'category', 'cuisine_types', 'price_range'],
            'shopping': ['name', 'address', 'city', 'state', 'category', 'store_types'],
            'healthcare': ['name', 'address', 'city', 'state', 'category', 'specialties'],
        }
        
        self.validation_patterns = {
            'phone': re.compile(r'^(\+91|0)?[6789]\d{9}$'),
            'email': re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'),
            'pincode': re.compile(r'^\d{6}$'),
            'website': re.compile(r'^https?://[^\s/$.?#].[^\s]*$'),
        }
        
        self.min_movie_ticket_price = Decimal("70.00")
    
    async def assess_data_quality(self, business: Business) -> DataQualityMetrics:
        """
        Comprehensive data quality assessment
        """
        try:
            # Analyze different quality dimensions
            completeness = await self._assess_completeness(business)
            consistency = await self._assess_consistency(business)
            validity = await self._assess_validity(business)
            accuracy = await self._assess_accuracy(business)
            freshness = await self._assess_freshness(business)
            
            # Calculate weighted overall score
            weights = {
                'completeness': 0.25,
                'consistency': 0.20,
                'validity': 0.25,
                'accuracy': 0.20,
                'freshness': 0.10
            }
            
            overall_score = (
                completeness * weights['completeness'] +
                consistency * weights['consistency'] +
                validity * weights['validity'] +
                accuracy * weights['accuracy'] +
                freshness * weights['freshness']
            )
            
            return DataQualityMetrics(
                completeness_score=completeness,
                consistency_score=consistency,
                validity_score=validity,
                accuracy_score=accuracy,
                freshness_score=freshness,
                overall_score=overall_score
            )
            
        except Exception as e:
            logger.error(f"Data quality assessment failed for business {business.id}: {e}")
            return DataQualityMetrics(0, 0, 0, 0, 0, 0)
    async def _assess_completeness(self, business: Business) -> float:
        """
        Assess data completeness based on required and optional fields
        """
        try:
            category_requirements = self.required_fields.get(
                business.category, self.required_fields['all']
            )
            
            total_fields = len(category_requirements)
            filled_fields = 0
            
            for field in category_requirements:
                value = getattr(business, field, None)
                if value is not None and str(value).strip():
                    filled_fields += 1
            
            # Bonus points for optional but valuable fields
            optional_fields = ['phone', 'email', 'website', 'operating_hours', 'description']
            optional_filled = 0
            for field in optional_fields:
                value = getattr(business, field, None)
                if value is not None and str(value).strip():
                    optional_filled += 1
            
            # Calculate score with bonus
            base_score = (filled_fields / total_fields) * 80.0  # Max 80 for required
            bonus_score = (optional_filled / len(optional_fields)) * 20.0  # Max 20 for optional
            
            return min(base_score + bonus_score, 100.0)
            
        except Exception as e:
            logger.error(f"Completeness assessment failed: {e}")
            return 0.0
    
    async def _assess_consistency(self, business: Business) -> float:
        """
        Assess internal data consistency
        """
        try:
            score = 100.0
            issues = []
            
            # Name consistency
            if hasattr(business, 'name') and business.name:
                name_words = business.name.lower().split()
                
                # Check if category matches name context
                if business.category == "cinema" and not any(
                    word in name_words for word in ['cinema', 'theater', 'theatre', 'movies', 'film']
                ):
                    score -= 10.0
                    issues.append("Cinema name doesn't indicate movie theater")
                
                # Check name length reasonableness
                if len(business.name) < 3 or len(business.name) > 100:
                    score -= 15.0
                    issues.append("Business name length unreasonable")
            
            # Address-location consistency
            if (hasattr(business, 'address') and business.address and 
                hasattr(business, 'city') and business.city):
                if business.city.lower() not in business.address.lower():
                    score -= 20.0
                    issues.append("City name not found in address")
            
            # Pricing consistency
            if business.category == "cinema" and hasattr(business, 'ticket_prices'):
                if business.ticket_prices:
                    prices = [Decimal(str(p)) for p in business.ticket_prices.values() 
                             if isinstance(p, (int, float, Decimal))]
                    if prices:
                        # Check if all prices meet minimum
                        violating_prices = [p for p in prices if p < self.min_movie_ticket_price]
                        if violating_prices:
                            score -= 50.0  # Heavy penalty
                            issues.append(f"Movie ticket prices below ₹{self.min_movie_ticket_price} minimum")
                        
                        # Check price range reasonableness
                        if max(prices) > min(prices) * 10:  # More than 10x difference
                            score -= 10.0
                            issues.append("Unreasonable price range variation")
            
            # Operating hours consistency
            if hasattr(business, 'operating_hours') and business.operating_hours:
                for day, hours in business.operating_hours.items():
                    if isinstance(hours, dict) and 'open' in hours and 'close' in hours:
                        try:
                            open_time = datetime.strptime(hours['open'], '%H:%M').time()
                            close_time = datetime.strptime(hours['close'], '%H:%M').time()
                            
                            # Check for reasonable hours
                            if open_time >= close_time:
                                score -= 15.0
                                issues.append(f"Invalid operating hours for {day}")
                        except ValueError:
                            score -= 10.0
                            issues.append(f"Invalid time format for {day}")
            
            if issues:
                logger.info(f"Consistency issues for business {business.id}: {issues}")
            
            return max(score, 0.0)
            
        except Exception as e:
            logger.error(f"Consistency assessment failed: {e}")
            return 50.0  # Default medium score on error
    async def _assess_validity(self, business: Business) -> float:
        """
        Assess data format and value validity
        """
        try:
            score = 0.0
            total_checks = 0
            
            # Phone number validation
            if hasattr(business, 'phone') and business.phone:
                total_checks += 1
                if self.validation_patterns['phone'].match(business.phone.replace(' ', '').replace('-', '')):
                    score += 20.0
                else:
                    score += 5.0  # Present but invalid format
            
            # Email validation
            if hasattr(business, 'email') and business.email:
                total_checks += 1
                if self.validation_patterns['email'].match(business.email):
                    score += 20.0
                else:
                    score += 5.0
            
            # Coordinate validation
            if hasattr(business, 'latitude') and hasattr(business, 'longitude'):
                if business.latitude and business.longitude:
                    total_checks += 1
                    if (-90 <= business.latitude <= 90 and 
                        -180 <= business.longitude <= 180 and
                        8.0 <= business.latitude <= 37.0 and  # India latitude range
                        68.0 <= business.longitude <= 97.0):   # India longitude range
                        score += 25.0
                    else:
                        score += 5.0
            
            # Website validation
            if hasattr(business, 'website') and business.website:
                total_checks += 1
                if self.validation_patterns['website'].match(business.website):
                    score += 15.0
                else:
                    score += 5.0
            
            # Category validation
            if hasattr(business, 'category') and business.category:
                total_checks += 1
                valid_categories = {
                    'cinema', 'restaurant', 'shopping', 'healthcare', 'education',
                    'entertainment', 'automotive', 'beauty', 'fitness', 'finance'
                }
                if business.category.lower() in valid_categories:
                    score += 20.0
                else:
                    score += 10.0
            
            # If no validatable fields present, return neutral score
            if total_checks == 0:
                return 50.0
            
            return min(score, 100.0)
            
        except Exception as e:
            logger.error(f"Validity assessment failed: {e}")
            return 0.0
    
    async def _assess_accuracy(self, business: Business) -> float:
        """
        Assess estimated real-world accuracy based on patterns and heuristics
        """
        try:
            score = 70.0  # Start with moderate confidence
            
            # Check for signs of high accuracy
            accuracy_indicators = 0
            
            # Detailed address suggests accuracy
            if hasattr(business, 'address') and business.address:
                address_parts = business.address.split(',')
                if len(address_parts) >= 3:  # Multiple address components
                    accuracy_indicators += 1
                    score += 10.0
            
            # Multiple contact methods suggest verified business
            contact_methods = 0
            for field in ['phone', 'email', 'website']:
                if hasattr(business, field) and getattr(business, field):
                    contact_methods += 1
            
            if contact_methods >= 2:
                accuracy_indicators += 1
                score += 10.0
            
            # Detailed operating hours suggest active management
            if hasattr(business, 'operating_hours') and business.operating_hours:
                if len(business.operating_hours) >= 7:  # Full week specified
                    accuracy_indicators += 1
                    score += 10.0
            
            # Recent update timestamp (if available)
            if hasattr(business, 'updated_at') and business.updated_at:
                days_since_update = (datetime.now(timezone.utc) - business.updated_at).days
                if days_since_update <= 30:
                    accuracy_indicators += 1
                    score += 10.0
                elif days_since_update <= 90:
                    score += 5.0
            
            # Penalty for suspicious patterns
            suspicious_patterns = 0
            
            # Generic names are suspicious
            if hasattr(business, 'name') and business.name:
                generic_names = ['business', 'shop', 'store', 'restaurant', 'cinema']
                if any(generic in business.name.lower() for generic in generic_names):
                    suspicious_patterns += 1
                    score -= 15.0
            
            # Missing critical category-specific info
            if business.category == "cinema":
                if not (hasattr(business, 'ticket_prices') and business.ticket_prices):
                    suspicious_patterns += 1
                    score -= 20.0
            
            return max(min(score, 100.0), 0.0)
            
        except Exception as e:
            logger.error(f"Accuracy assessment failed: {e}")
            return 50.0
    async def _assess_freshness(self, business: Business) -> float:
        """
        Assess data freshness and recency
        """
        try:
            current_time = datetime.now(timezone.utc)
            
            # Check last updated timestamp
            if hasattr(business, 'updated_at') and business.updated_at:
                days_since_update = (current_time - business.updated_at).days
                
                if days_since_update <= 7:
                    return 100.0  # Very fresh
                elif days_since_update <= 30:
                    return 90.0   # Fresh
                elif days_since_update <= 90:
                    return 70.0   # Moderately fresh
                elif days_since_update <= 180:
                    return 50.0   # Aging
                elif days_since_update <= 365:
                    return 30.0   # Stale
                else:
                    return 10.0   # Very stale
            
            # Check created timestamp as fallback
            if hasattr(business, 'created_at') and business.created_at:
                days_since_creation = (current_time - business.created_at).days
                
                if days_since_creation <= 30:
                    return 80.0   # Recently added
                elif days_since_creation <= 90:
                    return 60.0   # Somewhat recent
                elif days_since_creation <= 365:
                    return 40.0   # Older data
                else:
                    return 20.0   # Old data
            
            # No timestamp information
            return 50.0  # Neutral score
            
        except Exception as e:
            logger.error(f"Freshness assessment failed: {e}")
            return 50.0
    
    async def analyze_field_quality(self, business: Business) -> List[FieldAnalysis]:
        """
        Detailed analysis of individual field quality
        """
        try:
            analyses = []
            
            # Analyze core fields
            core_fields = ['name', 'address', 'city', 'state', 'category']
            for field in core_fields:
                analysis = await self._analyze_single_field(business, field, required=True)
                analyses.append(analysis)
            
            # Analyze optional fields
            optional_fields = ['phone', 'email', 'website', 'description']
            for field in optional_fields:
                if hasattr(business, field):
                    analysis = await self._analyze_single_field(business, field, required=False)
                    analyses.append(analysis)
            
            # Analyze category-specific fields
            if business.category == "cinema":
                category_fields = ['ticket_prices', 'screens', 'sound_systems']
                for field in category_fields:
                    if hasattr(business, field):
                        analysis = await self._analyze_single_field(business, field, required=True)
                        analyses.append(analysis)
            
            return analyses
            
        except Exception as e:
            logger.error(f"Field analysis failed: {e}")
            return []
    
    async def _analyze_single_field(self, business: Business, field_name: str, required: bool) -> FieldAnalysis:
        """
        Analyze quality of a single field
        """
        try:
            value = getattr(business, field_name, None)
            is_present = value is not None and str(value).strip()
            issues = []
            suggestions = []
            quality_score = 0.0
            
            if not is_present:
                if required:
                    issues.append(f"Required field '{field_name}' is missing")
                    suggestions.append(f"Add {field_name} information")
                    quality_score = 0.0
                else:
                    quality_score = 50.0  # Neutral for optional missing fields
                is_valid = False
            else:
                is_valid = True
                quality_score = 70.0  # Base score for present fields
                
                # Field-specific validation
                if field_name == 'phone':
                    if self.validation_patterns['phone'].match(str(value).replace(' ', '').replace('-', '')):
                        quality_score = 100.0
                    else:
                        issues.append("Invalid phone number format")
                        suggestions.append("Use format: +91XXXXXXXXXX or 10-digit number")
                        quality_score = 30.0
                        is_valid = False
                
                elif field_name == 'email':
                    if self.validation_patterns['email'].match(str(value)):
                        quality_score = 100.0
                    else:
                        issues.append("Invalid email format")
                        suggestions.append("Use valid email format: example@domain.com")
                        quality_score = 30.0
                        is_valid = False
                
                elif field_name == 'ticket_prices' and business.category == "cinema":
                    if isinstance(value, dict):
                        violations = []
                        for show_type, price in value.items():
                            if isinstance(price, (int, float, Decimal)):
                                if Decimal(str(price)) < self.min_movie_ticket_price:
                                    violations.append(f"{show_type}: ₹{price}")
                        
                        if violations:
                            issues.append(f"Ticket prices below ₹{self.min_movie_ticket_price}: {', '.join(violations)}")
                            suggestions.append(f"Ensure all movie tickets are priced at least ₹{self.min_movie_ticket_price}")
                            quality_score = 10.0
                            is_valid = False
                        else:
                            quality_score = 100.0
                    else:
                        issues.append("Ticket prices should be a dictionary of show types and prices")
                        quality_score = 20.0
                        is_valid = False
                
                elif field_name in ['name', 'address']:
                    if len(str(value)) < 3:
                        issues.append(f"{field_name.title()} too short")
                        suggestions.append(f"Provide more detailed {field_name}")
                        quality_score = 40.0
                    elif len(str(value)) > 200:
                        issues.append(f"{field_name.title()} too long")
                        suggestions.append(f"Shorten {field_name} to reasonable length")
                        quality_score = 60.0
                    else:
                        quality_score = 90.0
            
            return FieldAnalysis(
                field_name=field_name,
                is_present=is_present,
                is_valid=is_valid,
                quality_score=quality_score,
                issues=issues,
                suggestions=suggestions
            )
            
        except Exception as e:
            logger.error(f"Single field analysis failed for {field_name}: {e}")
            return FieldAnalysis(
                field_name=field_name,
                is_present=False,
                is_valid=False,
                quality_score=0.0,
                issues=[f"Analysis error: {str(e)}"],
                suggestions=["Manual review required"]
            )