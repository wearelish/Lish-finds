"""
Availability Service

Tracks and manages real-time availability including:
- Seat/table availability tracking
- Time-slot based bookings
- Capacity management
- Peak time availability prediction
- Waitlist management
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta, time
from dataclasses import dataclass
from enum import Enum
import logging

from .location_service import Location
from .business_rules_engine import BusinessRulesEngine

logger = logging.getLogger(__name__)


class AvailabilityStatus(Enum):
    """Availability status levels"""
    AVAILABLE = "available"
    LIMITED = "limited"
    VERY_LIMITED = "very_limited"
    FULL = "full"
    CLOSED = "closed"


@dataclass
class TimeSlot:
    """Time slot for booking/availability"""
    start_time: datetime
    end_time: datetime
    capacity: int
    booked: int
    waitlist: int
    
    @property
    def available(self) -> int:
        return max(0, self.capacity - self.booked)
    
    @property
    def occupancy_percent(self) -> float:
        return (self.booked / self.capacity * 100) if self.capacity > 0 else 0
    
    @property
    def status(self) -> AvailabilityStatus:
        occupancy = self.occupancy_percent
        
        if occupancy >= 100:
            return AvailabilityStatus.FULL
        elif occupancy >= 85:
            return AvailabilityStatus.VERY_LIMITED
        elif occupancy >= 60:
            return AvailabilityStatus.LIMITED
        else:
            return AvailabilityStatus.AVAILABLE


@dataclass
class BusinessAvailability:
    """Complete availability information for a business"""
    business_id: str
    business_type: str
    location: Location
    current_capacity: int
    current_booked: int
    time_slots: List[TimeSlot]
    operating_hours: Dict[str, str]
    last_updated: datetime
    
    @property
    def current_availability(self) -> int:
        return max(0, self.current_capacity - self.current_booked)
    
    @property
    def current_occupancy_percent(self) -> float:
        return (self.current_booked / self.current_capacity * 100) if self.current_capacity > 0 else 0
    
    @property
    def current_status(self) -> AvailabilityStatus:
        occupancy = self.current_occupancy_percent
        
        if not self._is_currently_open():
            return AvailabilityStatus.CLOSED
        elif occupancy >= 100:
            return AvailabilityStatus.FULL
        elif occupancy >= 85:
            return AvailabilityStatus.VERY_LIMITED
        elif occupancy >= 60:
            return AvailabilityStatus.LIMITED
        else:
            return AvailabilityStatus.AVAILABLE
    
    def _is_currently_open(self) -> bool:
        """Check if business is currently open"""
        now = datetime.now()
        current_day = now.strftime("%A").lower()
        
        if current_day in self.operating_hours:
            hours = self.operating_hours[current_day]
            if hours.lower() == "closed":
                return False
            
            try:
                open_time, close_time = hours.split("-")
                open_hour = int(open_time.split(":")[0])
                close_hour = int(close_time.split(":")[0])
                current_hour = now.hour
                
                if close_hour < open_hour:  # Crosses midnight
                    return current_hour >= open_hour or current_hour < close_hour
                else:
                    return open_hour <= current_hour < close_hour
            except:
                return True  # Default to open if parsing fails
        
        return True


class AvailabilityService:
    """Manages real-time availability tracking"""
    
    def __init__(self):
        self.business_rules = BusinessRulesEngine()
        
        # Mock availability data storage (in production, this would be a database)
        self.availability_cache: Dict[str, BusinessAvailability] = {}
        
    def get_business_availability(self, business_id: str, business_type: str,
                                location: Location, target_datetime: Optional[datetime] = None) -> BusinessAvailability:
        """Get current or future availability for a business"""
        
        if target_datetime is None:
            target_datetime = datetime.now()
        
        # Check cache first
        if business_id in self.availability_cache:
            cached_availability = self.availability_cache[business_id]
            # If cached data is recent (within 5 minutes), use it
            if datetime.now() - cached_availability.last_updated < timedelta(minutes=5):
                return cached_availability
        
        # Generate/update availability data
        availability = self._generate_availability_data(
            business_id, business_type, location, target_datetime
        )
        
        # Cache the result
        self.availability_cache[business_id] = availability
        
        return availability
    
    def _generate_availability_data(self, business_id: str, business_type: str,
                                  location: Location, target_datetime: datetime) -> BusinessAvailability:
        """Generate availability data based on business type and time"""
        
        if business_type == "movie_theater":
            return self._generate_theater_availability(business_id, location, target_datetime)
        elif business_type == "restaurant":
            return self._generate_restaurant_availability(business_id, location, target_datetime)
        elif business_type == "shopping_mall":
            return self._generate_mall_availability(business_id, location, target_datetime)
        else:
            return self._generate_generic_availability(business_id, business_type, location, target_datetime)
    
    def _generate_theater_availability(self, business_id: str, location: Location,
                                     target_datetime: datetime) -> BusinessAvailability:
        """Generate movie theater availability"""
        
        # Base capacity varies by location tier
        tier = self.business_rules._get_location_tier(location)
        base_capacities = {
            "premium_metro": 400,   # Large multiplexes
            "metro": 300,
            "tier1": 200,
            "tier2": 150,
            "tier3": 100
        }
        
        total_capacity = base_capacities.get(tier, 200)
        
        # Generate show time slots
        time_slots = []
        current_date = target_datetime.date()
        
        # Show times: 9 AM to 11:30 PM
        show_times = [
            time(9, 0), time(12, 0), time(15, 30), 
            time(18, 30), time(21, 30)
        ]
        
        for show_time in show_times:
            slot_datetime = datetime.combine(current_date, show_time)
            
            # Skip past shows
            if slot_datetime < datetime.now():
                continue
            
            # Calculate occupancy based on time and day
            occupancy_percent = self._calculate_theater_occupancy(slot_datetime, location)
            booked_seats = int(total_capacity * occupancy_percent / 100)
            
            time_slots.append(TimeSlot(
                start_time=slot_datetime,
                end_time=slot_datetime + timedelta(hours=3),  # Average movie length
                capacity=total_capacity,
                booked=booked_seats,
                waitlist=max(0, int(booked_seats * 0.1))  # 10% of bookings on waitlist
            ))
        
        # Current occupancy (if there's a current show)
        current_occupancy_percent = self._calculate_current_theater_occupancy(target_datetime, location)
        current_booked = int(total_capacity * current_occupancy_percent / 100)
        
        return BusinessAvailability(
            business_id=business_id,
            business_type="movie_theater",
            location=location,
            current_capacity=total_capacity,
            current_booked=current_booked,
            time_slots=time_slots,
            operating_hours={
                "monday": "09:00-23:30",
                "tuesday": "09:00-23:30",
                "wednesday": "09:00-23:30",
                "thursday": "09:00-23:30",
                "friday": "09:00-01:00",
                "saturday": "09:00-01:00",
                "sunday": "09:00-23:30"
            },
            last_updated=datetime.now()
        )
    
    def _generate_restaurant_availability(self, business_id: str, location: Location,
                                        target_datetime: datetime) -> BusinessAvailability:
        """Generate restaurant availability"""
        
        # Capacity based on location and type
        tier = self.business_rules._get_location_tier(location)
        base_capacities = {
            "premium_metro": 80,
            "metro": 60,
            "tier1": 45,
            "tier2": 35,
            "tier3": 25
        }
        
        seating_capacity = base_capacities.get(tier, 50)
        
        # Generate time slots for reservations
        time_slots = []
        current_date = target_datetime.date()
        
        # Reservation slots from 12 PM to 11 PM
        slot_times = []
        for hour in range(12, 23):
            slot_times.extend([
                time(hour, 0), time(hour, 30)
            ])
        
        for slot_time in slot_times:
            slot_datetime = datetime.combine(current_date, slot_time)
            
            # Skip past slots
            if slot_datetime < datetime.now():
                continue
            
            # Calculate occupancy based on meal times
            occupancy_percent = self._calculate_restaurant_occupancy(slot_datetime, location)
            booked_tables = int(seating_capacity * occupancy_percent / 100)
            
            time_slots.append(TimeSlot(
                start_time=slot_datetime,
                end_time=slot_datetime + timedelta(hours=1.5),  # Average dining duration
                capacity=seating_capacity,
                booked=booked_tables,
                waitlist=max(0, int(booked_tables * 0.15))  # 15% waitlist
            ))
        
        # Current occupancy
        current_occupancy_percent = self._calculate_current_restaurant_occupancy(target_datetime, location)
        current_booked = int(seating_capacity * current_occupancy_percent / 100)
        
        return BusinessAvailability(
            business_id=business_id,
            business_type="restaurant",
            location=location,
            current_capacity=seating_capacity,
            current_booked=current_booked,
            time_slots=time_slots,
            operating_hours={
                "monday": "12:00-23:00",
                "tuesday": "12:00-23:00",
                "wednesday": "12:00-23:00",
                "thursday": "12:00-23:00",
                "friday": "12:00-23:30",
                "saturday": "12:00-23:30",
                "sunday": "12:00-23:00"
            },
            last_updated=datetime.now()
        )
    
    def _generate_mall_availability(self, business_id: str, location: Location,
                                  target_datetime: datetime) -> BusinessAvailability:
        """Generate shopping mall availability (parking-based)"""
        
        # Parking capacity as proxy for mall capacity
        tier = self.business_rules._get_location_tier(location)
        parking_capacities = {
            "premium_metro": 2000,
            "metro": 1500,
            "tier1": 1000,
            "tier2": 600,
            "tier3": 300
        }
        
        parking_capacity = parking_capacities.get(tier, 800)
        
        # Current parking occupancy
        current_occupancy_percent = self._calculate_mall_occupancy(target_datetime, location)
        current_occupied = int(parking_capacity * current_occupancy_percent / 100)
        
        return BusinessAvailability(
            business_id=business_id,
            business_type="shopping_mall",
            location=location,
            current_capacity=parking_capacity,
            current_booked=current_occupied,
            time_slots=[],  # Malls don't use time slots
            operating_hours={
                "monday": "10:00-22:00",
                "tuesday": "10:00-22:00",
                "wednesday": "10:00-22:00",
                "thursday": "10:00-22:00",
                "friday": "10:00-22:30",
                "saturday": "10:00-23:00",
                "sunday": "10:00-23:00"
            },
            last_updated=datetime.now()
        )
    
    def _generate_generic_availability(self, business_id: str, business_type: str,
                                     location: Location, target_datetime: datetime) -> BusinessAvailability:
        """Generate generic availability for other business types"""
        
        return BusinessAvailability(
            business_id=business_id,
            business_type=business_type,
            location=location,
            current_capacity=100,
            current_booked=50,
            time_slots=[],
            operating_hours={
                "monday": "09:00-21:00",
                "tuesday": "09:00-21:00",
                "wednesday": "09:00-21:00",
                "thursday": "09:00-21:00",
                "friday": "09:00-21:00",
                "saturday": "09:00-21:00",
                "sunday": "10:00-20:00"
            },
            last_updated=datetime.now()
        )
    
    def _calculate_theater_occupancy(self, show_datetime: datetime, location: Location) -> float:
        """Calculate expected theater occupancy for a show time"""
        
        hour = show_datetime.hour
        weekday = show_datetime.weekday()
        
        # Base occupancy by show time
        if 9 <= hour < 12:
            base_occupancy = 25  # Morning shows
        elif 12 <= hour < 18:
            base_occupancy = 45  # Afternoon shows
        elif 18 <= hour < 22:
            base_occupancy = 75  # Prime time shows
        else:
            base_occupancy = 60  # Late shows
        
        # Weekend boost
        if weekday >= 5:  # Saturday, Sunday
            base_occupancy += 20
        
        # Location tier adjustment
        tier = self.business_rules._get_location_tier(location)
        tier_adjustments = {
            "premium_metro": 10,  # Higher occupancy in premium areas
            "metro": 5,
            "tier1": 0,
            "tier2": -5,
            "tier3": -10
        }
        
        base_occupancy += tier_adjustments.get(tier, 0)
        
        # Cap at reasonable limits
        return max(10, min(95, base_occupancy))
    
    def _calculate_current_theater_occupancy(self, current_datetime: datetime, location: Location) -> float:
        """Calculate current theater occupancy"""
        
        hour = current_datetime.hour
        
        # If there's likely a show running now
        if 9 <= hour <= 23:
            return self._calculate_theater_occupancy(current_datetime, location)
        else:
            return 0  # Closed
    
    def _calculate_restaurant_occupancy(self, slot_datetime: datetime, location: Location) -> float:
        """Calculate expected restaurant occupancy for a time slot"""
        
        hour = slot_datetime.hour
        weekday = slot_datetime.weekday()
        
        # Base occupancy by time
        if 12 <= hour < 15:  # Lunch time
            base_occupancy = 70
        elif 19 <= hour < 22:  # Dinner time
            base_occupancy = 85
        elif 15 <= hour < 19:  # Tea time
            base_occupancy = 40
        elif 22 <= hour < 23:  # Late dinner
            base_occupancy = 50
        else:
            base_occupancy = 20
        
        # Weekend adjustment
        if weekday >= 5:
            if 19 <= hour < 22:  # Weekend dinner peak
                base_occupancy = min(95, base_occupancy + 15)
            else:
                base_occupancy += 10
        
        # Location adjustment
        tier = self.business_rules._get_location_tier(location)
        tier_adjustments = {
            "premium_metro": 15,
            "metro": 8,
            "tier1": 0,
            "tier2": -5,
            "tier3": -10
        }
        
        base_occupancy += tier_adjustments.get(tier, 0)
        
        return max(5, min(95, base_occupancy))
    
    def _calculate_current_restaurant_occupancy(self, current_datetime: datetime, location: Location) -> float:
        """Calculate current restaurant occupancy"""
        
        hour = current_datetime.hour
        
        if 12 <= hour <= 23:
            return self._calculate_restaurant_occupancy(current_datetime, location)
        else:
            return 0  # Likely closed
    
    def _calculate_mall_occupancy(self, current_datetime: datetime, location: Location) -> float:
        """Calculate current mall (parking) occupancy"""
        
        hour = current_datetime.hour
        weekday = current_datetime.weekday()
        
        # Base occupancy by time of day
        if 10 <= hour < 12:  # Opening hours
            base_occupancy = 30
        elif 12 <= hour < 18:  # Afternoon
            base_occupancy = 60
        elif 18 <= hour < 21:  # Evening peak
            base_occupancy = 85
        elif 21 <= hour < 23:  # Late evening
            base_occupancy = 45
        else:
            base_occupancy = 10  # Closed or nearly closed
        
        # Weekend surge
        if weekday >= 5:
            if 12 <= hour <= 21:
                base_occupancy = min(95, base_occupancy + 20)
            else:
                base_occupancy += 10
        
        # Location tier effect
        tier = self.business_rules._get_location_tier(location)
        tier_adjustments = {
            "premium_metro": 10,  # Popular malls are busier
            "metro": 5,
            "tier1": 0,
            "tier2": -8,
            "tier3": -15
        }
        
        base_occupancy += tier_adjustments.get(tier, 0)
        
        return max(5, min(95, base_occupancy))
    
    def get_next_available_slots(self, business_id: str, business_type: str,
                               location: Location, count: int = 5) -> List[TimeSlot]:
        """Get next available time slots"""
        
        availability = self.get_business_availability(business_id, business_type, location)
        
        # Filter for available slots
        available_slots = [
            slot for slot in availability.time_slots 
            if slot.status in [AvailabilityStatus.AVAILABLE, AvailabilityStatus.LIMITED]
        ]
        
        # Sort by start time and return requested count
        available_slots.sort(key=lambda x: x.start_time)
        return available_slots[:count]
    
    def predict_future_availability(self, business_id: str, business_type: str,
                                  location: Location, hours_ahead: int = 24) -> List[Dict[str, Any]]:
        """Predict availability for the next N hours"""
        
        predictions = []
        current_time = datetime.now()
        
        for hour_offset in range(0, hours_ahead, 2):  # Every 2 hours
            future_time = current_time + timedelta(hours=hour_offset)
            availability = self.get_business_availability(
                business_id, business_type, location, future_time
            )
            
            predictions.append({
                "datetime": future_time.isoformat(),
                "occupancy_percent": availability.current_occupancy_percent,
                "status": availability.current_status.value,
                "available_capacity": availability.current_availability
            })
        
        return predictions
    
    def get_peak_hours_analysis(self, business_type: str, location: Location) -> Dict[str, Any]:
        """Analyze peak hours for a business type and location"""
        
        analysis = {
            "business_type": business_type,
            "location": location.to_dict(),
            "peak_hours": {},
            "recommendations": []
        }
        
        if business_type == "movie_theater":
            analysis["peak_hours"] = {
                "weekday": ["19:00-22:00"],
                "weekend": ["12:00-15:00", "18:00-22:00"],
                "highest_demand": "Saturday 20:00-22:00"
            }
            analysis["recommendations"] = [
                "Book tickets in advance for weekend evening shows",
                "Consider afternoon shows for better availability",
                "Avoid Friday and Saturday prime time for walk-ins"
            ]
        
        elif business_type == "restaurant":
            analysis["peak_hours"] = {
                "lunch": ["12:30-14:00"],
                "dinner": ["19:30-21:30"],
                "weekend_brunch": ["11:00-14:00"],
                "highest_demand": "Saturday 20:00-21:00"
            }
            analysis["recommendations"] = [
                "Make reservations for weekend dinners",
                "Consider early lunch (12:00) or late lunch (14:30)",
                "Off-peak hours (15:00-18:00) have better availability"
            ]
        
        elif business_type == "shopping_mall":
            analysis["peak_hours"] = {
                "weekday_evening": ["18:00-21:00"],
                "weekend_all_day": ["11:00-22:00"],
                "highest_demand": "Sunday 15:00-20:00"
            }
            analysis["recommendations"] = [
                "Visit on weekday mornings for less crowded experience",
                "Parking fills up quickly on weekends",
                "Best shopping experience on Tuesday-Thursday"
            ]
        
        return analysis
    
    def check_waitlist_status(self, business_id: str, time_slot: datetime) -> Dict[str, Any]:
        """Check waitlist status for a specific time slot"""
        
        # Mock waitlist implementation
        return {
            "business_id": business_id,
            "time_slot": time_slot.isoformat(),
            "waitlist_length": 12,
            "estimated_wait_time_minutes": 45,
            "probability_of_availability": 0.65,
            "alternative_suggestions": [
                {
                    "time": (time_slot + timedelta(hours=1)).isoformat(),
                    "availability": "high"
                },
                {
                    "time": (time_slot - timedelta(hours=1)).isoformat(), 
                    "availability": "medium"
                }
            ]
        }
    
    def get_availability_alerts(self, business_id: str, user_preferences: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get availability alerts based on user preferences"""
        
        alerts = []
        
        # Mock alert system
        preferred_times = user_preferences.get("preferred_times", [])
        max_price = user_preferences.get("max_price", 1000)
        
        for pref_time_str in preferred_times:
            try:
                pref_time = datetime.fromisoformat(pref_time_str)
                
                alerts.append({
                    "type": "availability_opened",
                    "business_id": business_id,
                    "time_slot": pref_time.isoformat(),
                    "message": f"Availability opened for {pref_time.strftime('%I:%M %p')}",
                    "action_required": "Book within 15 minutes",
                    "priority": "high"
                })
            except:
                continue
        
        return alerts
    
    def optimize_capacity_utilization(self, business_id: str, business_type: str,
                                    location: Location) -> Dict[str, Any]:
        """Suggest capacity optimization strategies"""
        
        availability = self.get_business_availability(business_id, business_type, location)
        
        optimization = {
            "current_utilization": availability.current_occupancy_percent,
            "target_utilization": 80.0,
            "strategies": [],
            "revenue_impact": {}
        }
        
        if availability.current_occupancy_percent < 60:
            optimization["strategies"].extend([
                "Implement dynamic pricing to attract more customers",
                "Offer promotional packages during low-demand hours",
                "Partner with aggregators for better visibility"
            ])
        elif availability.current_occupancy_percent > 90:
            optimization["strategies"].extend([
                "Increase pricing during peak hours", 
                "Implement premium tiers with higher prices",
                "Consider capacity expansion"
            ])
        
        return optimization