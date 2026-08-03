"""
Location Service

Provides precise location detection and geographical services including:
- GPS coordinate detection
- IP-based geolocation
- Address validation and geocoding
- Distance calculations
- Area boundary detection
"""

import requests
import math
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import json

logger = logging.getLogger(__name__)


@dataclass
class Location:
    """Location data structure"""
    latitude: float
    longitude: float
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    accuracy: str = "unknown"  # high, medium, low, unknown
    source: str = "manual"  # gps, ip, manual, geocoded
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "address": self.address,
            "city": self.city,
            "state": self.state,
            "country": self.country,
            "postal_code": self.postal_code,
            "accuracy": self.accuracy,
            "source": self.source
        }


class LocationService:
    """Handles all location-related operations"""
    
    def __init__(self):
        self.geocoder = Nominatim(user_agent="lishfind_app")
        
        # Indian city coordinates for accurate local searches
        self.major_cities = {
            "mumbai": {"lat": 19.0760, "lng": 72.8777, "state": "Maharashtra"},
            "delhi": {"lat": 28.7041, "lng": 77.1025, "state": "Delhi"},
            "bangalore": {"lat": 12.9716, "lng": 77.5946, "state": "Karnataka"},
            "hyderabad": {"lat": 17.3850, "lng": 78.4867, "state": "Telangana"},
            "ahmedabad": {"lat": 23.0225, "lng": 72.5714, "state": "Gujarat"},
            "chennai": {"lat": 13.0827, "lng": 80.2707, "state": "Tamil Nadu"},
            "kolkata": {"lat": 22.5726, "lng": 88.3639, "state": "West Bengal"},
            "pune": {"lat": 18.5204, "lng": 73.8567, "state": "Maharashtra"},
            "jaipur": {"lat": 26.9124, "lng": 75.7873, "state": "Rajasthan"},
            "surat": {"lat": 21.1702, "lng": 72.8311, "state": "Gujarat"},
            "lucknow": {"lat": 26.8467, "lng": 80.9462, "state": "Uttar Pradesh"},
            "kanpur": {"lat": 26.4499, "lng": 80.3319, "state": "Uttar Pradesh"},
            "nagpur": {"lat": 21.1458, "lng": 79.0882, "state": "Maharashtra"},
            "indore": {"lat": 22.7196, "lng": 75.8577, "state": "Madhya Pradesh"},
            "thane": {"lat": 19.2183, "lng": 72.9781, "state": "Maharashtra"},
            "bhopal": {"lat": 23.2599, "lng": 77.4126, "state": "Madhya Pradesh"},
            "visakhapatnam": {"lat": 17.6868, "lng": 83.2185, "state": "Andhra Pradesh"},
            "pimpri": {"lat": 18.6298, "lng": 73.7997, "state": "Maharashtra"},
            "patna": {"lat": 25.5941, "lng": 85.1376, "state": "Bihar"},
            "vadodara": {"lat": 22.3072, "lng": 73.1812, "state": "Gujarat"},
            "ghaziabad": {"lat": 28.6692, "lng": 77.4538, "state": "Uttar Pradesh"},
            "ludhiana": {"lat": 30.9010, "lng": 75.8573, "state": "Punjab"},
            "agra": {"lat": 27.1767, "lng": 78.0081, "state": "Uttar Pradesh"},
            "nashik": {"lat": 19.9975, "lng": 73.7898, "state": "Maharashtra"},
            "faridabad": {"lat": 28.4089, "lng": 77.3178, "state": "Haryana"},
            "meerut": {"lat": 28.9845, "lng": 77.7064, "state": "Uttar Pradesh"},
            "rajkot": {"lat": 22.3039, "lng": 70.8022, "state": "Gujarat"},
            "kalyan": {"lat": 19.2437, "lng": 73.1355, "state": "Maharashtra"},
            "vasai": {"lat": 19.4912, "lng": 72.8054, "state": "Maharashtra"},
            "varanasi": {"lat": 25.3176, "lng": 82.9739, "state": "Uttar Pradesh"},
            "srinagar": {"lat": 34.0837, "lng": 74.7973, "state": "Jammu and Kashmir"},
            "aurangabad": {"lat": 19.8762, "lng": 75.3433, "state": "Maharashtra"},
            "dhanbad": {"lat": 23.7957, "lng": 86.4304, "state": "Jharkhand"},
            "amritsar": {"lat": 31.6340, "lng": 74.8723, "state": "Punjab"},
            "navi_mumbai": {"lat": 19.0330, "lng": 73.0297, "state": "Maharashtra"},
            "allahabad": {"lat": 25.4358, "lng": 81.8463, "state": "Uttar Pradesh"},
            "howrah": {"lat": 22.5958, "lng": 88.2636, "state": "West Bengal"},
            "ranchi": {"lat": 23.3441, "lng": 85.3096, "state": "Jharkhand"},
            "gwalior": {"lat": 26.2183, "lng": 78.1828, "state": "Madhya Pradesh"},
            "jabalpur": {"lat": 23.1815, "lng": 79.9864, "state": "Madhya Pradesh"},
            "coimbatore": {"lat": 11.0168, "lng": 76.9558, "state": "Tamil Nadu"},
            "vijayawada": {"lat": 16.5062, "lng": 80.6480, "state": "Andhra Pradesh"},
            "jodhpur": {"lat": 26.2389, "lng": 73.0243, "state": "Rajasthan"},
            "madurai": {"lat": 9.9252, "lng": 78.1198, "state": "Tamil Nadu"},
            "raipur": {"lat": 21.2514, "lng": 81.6296, "state": "Chhattisgarh"},
            "kota": {"lat": 25.2138, "lng": 75.8648, "state": "Rajasthan"},
            "chandigarh": {"lat": 30.7333, "lng": 76.7794, "state": "Chandigarh"},
            "guwahati": {"lat": 26.1445, "lng": 91.7362, "state": "Assam"},
            "solapur": {"lat": 17.6599, "lng": 75.9064, "state": "Maharashtra"},
            "hubli": {"lat": 15.3647, "lng": 75.1240, "state": "Karnataka"},
            "bareilly": {"lat": 28.3670, "lng": 79.4304, "state": "Uttar Pradesh"},
            "moradabad": {"lat": 28.8386, "lng": 78.7733, "state": "Uttar Pradesh"},
            "mysore": {"lat": 12.2958, "lng": 76.6394, "state": "Karnataka"},
            "tiruppur": {"lat": 11.1085, "lng": 77.3411, "state": "Tamil Nadu"},
            "gurgaon": {"lat": 28.4595, "lng": 77.0266, "state": "Haryana"},
            "aligarh": {"lat": 27.8974, "lng": 78.0880, "state": "Uttar Pradesh"},
            "jalandhar": {"lat": 31.3260, "lng": 75.5762, "state": "Punjab"},
            "tiruchirappalli": {"lat": 10.7905, "lng": 78.7047, "state": "Tamil Nadu"},
            "bhubaneswar": {"lat": 20.2961, "lng": 85.8245, "state": "Odisha"},
            "salem": {"lat": 11.6643, "lng": 78.1460, "state": "Tamil Nadu"},
            "warangal": {"lat": 17.9689, "lng": 79.5941, "state": "Telangana"},
            "mira": {"lat": 19.2952, "lng": 72.8544, "state": "Maharashtra"},
            "bhiwandi": {"lat": 19.2948, "lng": 73.0581, "state": "Maharashtra"},
            "saharanpur": {"lat": 29.9680, "lng": 77.5552, "state": "Uttar Pradesh"},
            "gorakhpur": {"lat": 26.7606, "lng": 83.3732, "state": "Uttar Pradesh"},
            "bikaner": {"lat": 28.0229, "lng": 73.3119, "state": "Rajasthan"},
            "amravati": {"lat": 20.9374, "lng": 77.7796, "state": "Maharashtra"},
            "noida": {"lat": 28.5355, "lng": 77.3910, "state": "Uttar Pradesh"},
            "jamshedpur": {"lat": 22.8046, "lng": 86.2029, "state": "Jharkhand"},
            "bhilai": {"lat": 21.1938, "lng": 81.3509, "state": "Chhattisgarh"},
            "cuttack": {"lat": 20.4625, "lng": 85.8828, "state": "Odisha"},
            "firozabad": {"lat": 27.1592, "lng": 78.3957, "state": "Uttar Pradesh"},
            "kochi": {"lat": 9.9312, "lng": 76.2673, "state": "Kerala"},
            "nellore": {"lat": 14.4426, "lng": 79.9865, "state": "Andhra Pradesh"},
            "bhavnagar": {"lat": 21.7645, "lng": 72.1519, "state": "Gujarat"},
            "dehradun": {"lat": 30.3165, "lng": 78.0322, "state": "Uttarakhand"},
            "durgapur": {"lat": 23.5204, "lng": 87.3119, "state": "West Bengal"},
            "asansol": {"lat": 23.6739, "lng": 86.9524, "state": "West Bengal"},
            "rourkela": {"lat": 22.2604, "lng": 84.8536, "state": "Odisha"},
            "nanded": {"lat": 19.1383, "lng": 77.3210, "state": "Maharashtra"},
            "kolhapur": {"lat": 16.7050, "lng": 74.2433, "state": "Maharashtra"},
            "ajmer": {"lat": 26.4499, "lng": 74.6399, "state": "Rajasthan"},
            "akola": {"lat": 20.7002, "lng": 77.0082, "state": "Maharashtra"},
            "gulbarga": {"lat": 17.3297, "lng": 76.8343, "state": "Karnataka"},
            "jamnagar": {"lat": 22.4707, "lng": 70.0577, "state": "Gujarat"},
            "ujjain": {"lat": 23.1793, "lng": 75.7849, "state": "Madhya Pradesh"},
            "loni": {"lat": 28.7333, "lng": 77.2833, "state": "Uttar Pradesh"},
            "siliguri": {"lat": 26.7271, "lng": 88.3953, "state": "West Bengal"},
            "jhansi": {"lat": 25.4484, "lng": 78.5685, "state": "Uttar Pradesh"},
            "ulhasnagar": {"lat": 19.2215, "lng": 73.1645, "state": "Maharashtra"},
            "jammu": {"lat": 32.7266, "lng": 74.8570, "state": "Jammu and Kashmir"},
            "sangli": {"lat": 16.8524, "lng": 74.5815, "state": "Maharashtra"},
            "mangalore": {"lat": 12.9141, "lng": 74.8560, "state": "Karnataka"},
            "erode": {"lat": 11.3410, "lng": 77.7172, "state": "Tamil Nadu"},
            "belgaum": {"lat": 15.8497, "lng": 74.4977, "state": "Karnataka"},
            "ambattur": {"lat": 13.1143, "lng": 80.1548, "state": "Tamil Nadu"},
            "tirunelveli": {"lat": 8.7139, "lng": 77.7567, "state": "Tamil Nadu"},
            "malegaon": {"lat": 20.5579, "lng": 74.5287, "state": "Maharashtra"},
            "gaya": {"lat": 24.7914, "lng": 85.0002, "state": "Bihar"}
        }
    
    def detect_location_from_ip(self, ip_address: str) -> Optional[Location]:
        """Detect location from IP address using free IP geolocation service"""
        try:
            # Using free ip-api.com service (no API key required)
            response = requests.get(f"http://ip-api.com/json/{ip_address}", timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('status') == 'success':
                    return Location(
                        latitude=float(data.get('lat', 0)),
                        longitude=float(data.get('lon', 0)),
                        city=data.get('city'),
                        state=data.get('regionName'),
                        country=data.get('country'),
                        postal_code=data.get('zip'),
                        accuracy="medium",
                        source="ip"
                    )
        except Exception as e:
            logger.warning(f"IP geolocation failed for {ip_address}: {e}")
        
        return None
    
    def geocode_address(self, address: str) -> Optional[Location]:
        """Convert address to coordinates"""
        try:
            location_data = self.geocoder.geocode(address, timeout=10)
            
            if location_data:
                # Extract address components
                address_parts = location_data.address.split(', ') if location_data.address else []
                
                return Location(
                    latitude=location_data.latitude,
                    longitude=location_data.longitude,
                    address=location_data.address,
                    city=self._extract_city(address_parts),
                    state=self._extract_state(address_parts),
                    country=self._extract_country(address_parts),
                    postal_code=self._extract_postal_code(address_parts),
                    accuracy="high",
                    source="geocoded"
                )
        except Exception as e:
            logger.warning(f"Geocoding failed for address {address}: {e}")
        
        return None
    
    def reverse_geocode(self, latitude: float, longitude: float) -> Optional[Location]:
        """Convert coordinates to address"""
        try:
            location_data = self.geocoder.reverse((latitude, longitude), timeout=10)
            
            if location_data:
                address_parts = location_data.address.split(', ') if location_data.address else []
                
                return Location(
                    latitude=latitude,
                    longitude=longitude,
                    address=location_data.address,
                    city=self._extract_city(address_parts),
                    state=self._extract_state(address_parts),
                    country=self._extract_country(address_parts),
                    postal_code=self._extract_postal_code(address_parts),
                    accuracy="high",
                    source="gps"
                )
        except Exception as e:
            logger.warning(f"Reverse geocoding failed for {latitude}, {longitude}: {e}")
        
        return None
    
    def get_city_location(self, city_name: str) -> Optional[Location]:
        """Get location for a known city"""
        city_key = city_name.lower().replace(" ", "_")
        
        if city_key in self.major_cities:
            city_data = self.major_cities[city_key]
            return Location(
                latitude=city_data["lat"],
                longitude=city_data["lng"],
                city=city_name.title(),
                state=city_data["state"],
                country="India",
                accuracy="high",
                source="database"
            )
        
        # Fallback to geocoding
        return self.geocode_address(f"{city_name}, India")
    
    def calculate_distance(self, location1: Location, location2: Location) -> float:
        """Calculate distance between two locations in kilometers"""
        try:
            point1 = (location1.latitude, location1.longitude)
            point2 = (location2.latitude, location2.longitude)
            
            distance = geodesic(point1, point2).kilometers
            return round(distance, 2)
        except Exception as e:
            logger.error(f"Distance calculation failed: {e}")
            return float('inf')
    
    def calculate_travel_time(self, location1: Location, location2: Location, 
                            mode: str = "driving") -> Dict[str, Any]:
        """Calculate travel time between locations"""
        distance_km = self.calculate_distance(location1, location2)
        
        # Estimated speeds (km/h) for different modes in Indian cities
        speed_estimates = {
            "walking": 4,
            "cycling": 12,
            "auto": 20,  # Auto-rickshaw in city traffic
            "driving": 25,  # Car in city traffic
            "metro": 35,  # Where available
            "bus": 18   # City bus in traffic
        }
        
        speed = speed_estimates.get(mode, 25)
        travel_time_hours = distance_km / speed
        travel_time_minutes = int(travel_time_hours * 60)
        
        # Add traffic and congestion factors for Indian cities
        congestion_factor = self._get_congestion_factor(location1.city, location2.city)
        adjusted_time = int(travel_time_minutes * congestion_factor)
        
        return {
            "distance_km": distance_km,
            "travel_time_minutes": adjusted_time,
            "mode": mode,
            "traffic_factor": congestion_factor
        }
    
    def is_location_in_city(self, location: Location, city_name: str, 
                           radius_km: float = 50) -> bool:
        """Check if location is within city boundaries"""
        city_location = self.get_city_location(city_name)
        
        if not city_location:
            return False
        
        distance = self.calculate_distance(location, city_location)
        return distance <= radius_km
    
    def find_nearby_locations(self, center: Location, 
                            radius_km: float = 10) -> List[str]:
        """Find major cities/areas within radius"""
        nearby_areas = []
        
        for city_name, city_data in self.major_cities.items():
            city_location = Location(
                latitude=city_data["lat"],
                longitude=city_data["lng"],
                city=city_name.title(),
                state=city_data["state"]
            )
            
            distance = self.calculate_distance(center, city_location)
            
            if distance <= radius_km:
                nearby_areas.append({
                    "name": city_name.replace("_", " ").title(),
                    "distance_km": distance,
                    "state": city_data["state"]
                })
        
        # Sort by distance
        nearby_areas.sort(key=lambda x: x["distance_km"])
        return nearby_areas
    
    def get_location_hierarchy(self, location: Location) -> Dict[str, str]:
        """Get location hierarchy (area -> city -> state -> country)"""
        hierarchy = {
            "coordinates": f"{location.latitude}, {location.longitude}",
            "address": location.address or "",
            "area": self._extract_area(location.address),
            "city": location.city or "",
            "state": location.state or "",
            "country": location.country or "India"
        }
        
        return hierarchy
    
    def validate_indian_location(self, location: Location) -> bool:
        """Validate if location is within Indian boundaries"""
        # Indian geographical boundaries (approximate)
        india_bounds = {
            "north": 37.6,
            "south": 6.4,
            "east": 97.25,
            "west": 68.7
        }
        
        return (india_bounds["south"] <= location.latitude <= india_bounds["north"] and
                india_bounds["west"] <= location.longitude <= india_bounds["east"])
    
    def _extract_city(self, address_parts: List[str]) -> Optional[str]:
        """Extract city from address parts"""
        # Common patterns in Indian addresses
        city_indicators = ['District', 'City', 'Municipal Corporation']
        
        for part in address_parts:
            part = part.strip()
            # Check if this part contains city indicators
            if any(indicator in part for indicator in city_indicators):
                return part.split(',')[0].strip()
            
            # Check if it's a known major city
            if part.lower().replace(" ", "_") in self.major_cities:
                return part.strip()
        
        # Fallback: assume the second-to-last part is the city
        if len(address_parts) >= 2:
            return address_parts[-2].strip()
        
        return None
    
    def _extract_state(self, address_parts: List[str]) -> Optional[str]:
        """Extract state from address parts"""
        indian_states = [
            'Andhra Pradesh', 'Arunachal Pradesh', 'Assam', 'Bihar', 'Chhattisgarh',
            'Goa', 'Gujarat', 'Haryana', 'Himachal Pradesh', 'Jharkhand', 'Karnataka',
            'Kerala', 'Madhya Pradesh', 'Maharashtra', 'Manipur', 'Meghalaya', 'Mizoram',
            'Nagaland', 'Odisha', 'Punjab', 'Rajasthan', 'Sikkim', 'Tamil Nadu', 'Telangana',
            'Tripura', 'Uttar Pradesh', 'Uttarakhand', 'West Bengal', 'Delhi', 'Chandigarh',
            'Jammu and Kashmir', 'Ladakh'
        ]
        
        for part in address_parts:
            for state in indian_states:
                if state.lower() in part.lower():
                    return state
        
        return None
    
    def _extract_country(self, address_parts: List[str]) -> str:
        """Extract country from address parts"""
        for part in address_parts:
            if 'india' in part.lower():
                return 'India'
        
        return 'India'  # Default for Indian locations
    
    def _extract_postal_code(self, address_parts: List[str]) -> Optional[str]:
        """Extract postal code from address parts"""
        import re
        
        postal_pattern = r'\b\d{6}\b'  # Indian postal codes are 6 digits
        
        for part in address_parts:
            match = re.search(postal_pattern, part)
            if match:
                return match.group()
        
        return None
    
    def _extract_area(self, address: Optional[str]) -> Optional[str]:
        """Extract local area/neighborhood from full address"""
        if not address:
            return None
        
        # Split address and take the first meaningful part
        parts = address.split(',')
        if len(parts) > 0:
            area = parts[0].strip()
            # Remove house/building numbers
            import re
            area = re.sub(r'^\d+[A-Z]?\s*[-/]?\s*', '', area)
            return area.strip() if area else None
        
        return None
    
    def _get_congestion_factor(self, city1: Optional[str], city2: Optional[str]) -> float:
        """Get traffic congestion factor for cities"""
        # Congestion factors for major Indian cities
        congestion_factors = {
            "mumbai": 1.8,
            "delhi": 1.7,
            "bangalore": 1.6,
            "pune": 1.5,
            "hyderabad": 1.4,
            "chennai": 1.5,
            "kolkata": 1.6,
            "ahmedabad": 1.3,
            "gurgaon": 1.7,
            "noida": 1.6
        }
        
        # Use the higher congestion factor if both cities are known
        factor1 = congestion_factors.get(city1.lower() if city1 else "", 1.2)
        factor2 = congestion_factors.get(city2.lower() if city2 else "", 1.2)
        
        return max(factor1, factor2)