"""
Area Mapping Service

Provides comprehensive area mapping and boundary detection including:
- City boundaries and districts
- Neighborhood mapping
- Commercial vs residential area detection
- Metro/transport accessibility
- Distance-based search with multiple transport modes
"""

import math
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import logging

from .location_service import Location, LocationService

logger = logging.getLogger(__name__)


@dataclass
class SearchRadius:
    """Search radius configuration for different modes"""
    walking: float = 1.0  # 1 km walking radius
    cycling: float = 3.0  # 3 km cycling radius
    auto: float = 5.0     # 5 km auto-rickshaw radius
    driving: float = 10.0 # 10 km driving radius
    metro: float = 15.0   # 15 km if metro connectivity exists
    
    def get_radius(self, transport_mode: str) -> float:
        return getattr(self, transport_mode, self.driving)


@dataclass
class AreaInfo:
    """Area information and characteristics"""
    name: str
    area_type: str  # commercial, residential, industrial, mixed
    safety_rating: float  # 1-5 scale
    traffic_level: str  # low, medium, high, very_high
    parking_availability: str  # abundant, moderate, limited, none
    public_transport: List[str]  # metro, bus, auto, taxi
    landmarks: List[str]
    average_rent_per_sqft: float
    commercial_density: str  # low, medium, high
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "area_type": self.area_type,
            "safety_rating": self.safety_rating,
            "traffic_level": self.traffic_level,
            "parking_availability": self.parking_availability,
            "public_transport": self.public_transport,
            "landmarks": self.landmarks,
            "average_rent_per_sqft": self.average_rent_per_sqft,
            "commercial_density": self.commercial_density
        }


class AreaMappingService:
    """Handles area mapping and location-based searches"""
    
    def __init__(self):
        self.location_service = LocationService()
        self.search_radius = SearchRadius()
        
        # Define major area boundaries and characteristics
        self.area_boundaries = self._load_area_boundaries()
        self.metro_stations = self._load_metro_stations()
        self.transport_hubs = self._load_transport_hubs()
        
    def _load_area_boundaries(self) -> Dict[str, Dict[str, Any]]:
        """Load area boundaries for major cities"""
        return {
            # Mumbai areas
            "mumbai": {
                "bandra_kurla_complex": {
                    "bounds": {"north": 19.0700, "south": 19.0500, "east": 72.8800, "west": 72.8600},
                    "area_info": AreaInfo(
                        name="Bandra Kurla Complex",
                        area_type="commercial",
                        safety_rating=4.5,
                        traffic_level="very_high",
                        parking_availability="limited",
                        public_transport=["metro", "bus", "taxi"],
                        landmarks=["NSE Building", "Consulate General"],
                        average_rent_per_sqft=250.0,
                        commercial_density="high"
                    )
                },
                "powai": {
                    "bounds": {"north": 19.1300, "south": 19.1000, "east": 72.9200, "west": 72.8800},
                    "area_info": AreaInfo(
                        name="Powai",
                        area_type="mixed",
                        safety_rating=4.2,
                        traffic_level="high",
                        parking_availability="moderate",
                        public_transport=["bus", "auto", "taxi"],
                        landmarks=["Powai Lake", "Hiranandani Gardens", "IIT Bombay"],
                        average_rent_per_sqft=180.0,
                        commercial_density="medium"
                    )
                },
                "andheri_east": {
                    "bounds": {"north": 19.1400, "south": 19.1000, "east": 72.8700, "west": 72.8300},
                    "area_info": AreaInfo(
                        name="Andheri East",
                        area_type="mixed",
                        safety_rating=3.8,
                        traffic_level="very_high",
                        parking_availability="limited",
                        public_transport=["metro", "bus", "auto", "taxi"],
                        landmarks=["Saki Naka", "MIDC", "WEH Metro"],
                        average_rent_per_sqft=150.0,
                        commercial_density="high"
                    )
                },
                "lower_parel": {
                    "bounds": {"north": 19.0150, "south": 18.9950, "east": 72.8350, "west": 72.8150},
                    "area_info": AreaInfo(
                        name="Lower Parel",
                        area_type="commercial",
                        safety_rating=4.3,
                        traffic_level="very_high",
                        parking_availability="limited",
                        public_transport=["metro", "bus", "taxi"],
                        landmarks=["Phoenix Mills", "High Street Phoenix", "Palladium Mall"],
                        average_rent_per_sqft=280.0,
                        commercial_density="high"
                    )
                }
            },
            
            # Delhi areas
            "delhi": {
                "connaught_place": {
                    "bounds": {"north": 28.6350, "south": 28.6250, "east": 77.2250, "west": 77.2150},
                    "area_info": AreaInfo(
                        name="Connaught Place",
                        area_type="commercial",
                        safety_rating=4.0,
                        traffic_level="very_high",
                        parking_availability="limited",
                        public_transport=["metro", "bus", "auto", "taxi"],
                        landmarks=["Central Park", "Palika Bazaar", "Rajiv Chowk Metro"],
                        average_rent_per_sqft=300.0,
                        commercial_density="high"
                    )
                },
                "cyber_city_gurgaon": {
                    "bounds": {"north": 28.4950, "south": 28.4750, "east": 77.0950, "west": 77.0750},
                    "area_info": AreaInfo(
                        name="Cyber City, Gurgaon",
                        area_type="commercial",
                        safety_rating=4.5,
                        traffic_level="very_high",
                        parking_availability="moderate",
                        public_transport=["metro", "bus", "taxi"],
                        landmarks=["DLF Cyber Hub", "Ambience Mall", "Cyber City Metro"],
                        average_rent_per_sqft=200.0,
                        commercial_density="high"
                    )
                }
            },
            
            # Bangalore areas
            "bangalore": {
                "koramangala": {
                    "bounds": {"north": 12.9400, "south": 12.9200, "east": 77.6400, "west": 77.6200},
                    "area_info": AreaInfo(
                        name="Koramangala",
                        area_type="mixed",
                        safety_rating=4.2,
                        traffic_level="very_high",
                        parking_availability="limited",
                        public_transport=["bus", "auto", "taxi"],
                        landmarks=["Forum Mall", "Sony World Junction", "Jyoti Nivas College"],
                        average_rent_per_sqft=120.0,
                        commercial_density="high"
                    )
                },
                "indiranagar": {
                    "bounds": {"north": 12.9800, "south": 12.9600, "east": 77.6500, "west": 77.6300},
                    "area_info": AreaInfo(
                        name="Indiranagar",
                        area_type="mixed",
                        safety_rating=4.3,
                        traffic_level="high",
                        parking_availability="moderate",
                        public_transport=["metro", "bus", "auto", "taxi"],
                        landmarks=["100 Feet Road", "CMH Road", "Indiranagar Metro"],
                        average_rent_per_sqft=110.0,
                        commercial_density="high"
                    )
                },
                "electronic_city": {
                    "bounds": {"north": 12.8500, "south": 12.8300, "east": 77.6800, "west": 77.6600},
                    "area_info": AreaInfo(
                        name="Electronic City",
                        area_type="commercial",
                        safety_rating=4.0,
                        traffic_level="high",
                        parking_availability="abundant",
                        public_transport=["bus", "taxi"],
                        landmarks=["Infosys Campus", "Electronic City Metro", "Forum Nexus Mall"],
                        average_rent_per_sqft=80.0,
                        commercial_density="medium"
                    )
                }
            }
        }
    
    def _load_metro_stations(self) -> Dict[str, List[Dict[str, Any]]]:
        """Load metro station locations for accurate transport mapping"""
        return {
            "mumbai": [
                {"name": "Andheri", "lat": 19.1197, "lng": 72.8461, "lines": ["Blue"]},
                {"name": "Bandra", "lat": 19.0544, "lng": 72.8406, "lines": ["Blue"]},
                {"name": "Lower Parel", "lat": 19.0142, "lng": 72.8302, "lines": ["Blue"]},
                {"name": "Ghatkopar", "lat": 19.0864, "lng": 72.9081, "lines": ["Blue", "Red"]},
                {"name": "Powai", "lat": 19.1176, "lng": 72.9060, "lines": ["Blue"]},
            ],
            "delhi": [
                {"name": "Rajiv Chowk", "lat": 28.6328, "lng": 77.2197, "lines": ["Blue", "Yellow"]},
                {"name": "Kashmere Gate", "lat": 28.6676, "lng": 77.2273, "lines": ["Red", "Yellow"]},
                {"name": "Cyber City", "lat": 28.4953, "lng": 77.0890, "lines": ["Yellow"]},
                {"name": "Huda City Centre", "lat": 28.4594, "lng": 77.0688, "lines": ["Yellow"]},
            ],
            "bangalore": [
                {"name": "MG Road", "lat": 12.9759, "lng": 77.6046, "lines": ["Purple"]},
                {"name": "Indiranagar", "lat": 12.9718, "lng": 77.6410, "lines": ["Purple"]},
                {"name": "Whitefield", "lat": 12.9698, "lng": 77.7500, "lines": ["Purple"]},
            ]
        }
    
    def _load_transport_hubs(self) -> Dict[str, List[Dict[str, Any]]]:
        """Load major transport hubs (airports, railway stations, bus terminals)"""
        return {
            "mumbai": [
                {"name": "Chhatrapati Shivaji Airport", "lat": 19.0896, "lng": 72.8656, "type": "airport"},
                {"name": "Mumbai Central", "lat": 18.9690, "lng": 72.8205, "type": "railway"},
                {"name": "Bandra Terminus", "lat": 19.0634, "lng": 72.8404, "type": "railway"},
                {"name": "Dadar", "lat": 19.0178, "lng": 72.8478, "type": "railway"},
            ],
            "delhi": [
                {"name": "Indira Gandhi International Airport", "lat": 28.5562, "lng": 77.1000, "type": "airport"},
                {"name": "New Delhi Railway Station", "lat": 28.6428, "lng": 77.2197, "type": "railway"},
                {"name": "ISBT Kashmere Gate", "lat": 28.6676, "lng": 77.2273, "type": "bus_terminal"},
            ],
            "bangalore": [
                {"name": "Kempegowda International Airport", "lat": 13.1986, "lng": 77.7066, "type": "airport"},
                {"name": "Bangalore City Railway Station", "lat": 12.9767, "lng": 77.5993, "type": "railway"},
                {"name": "Majestic Bus Terminal", "lat": 12.9767, "lng": 77.5750, "type": "bus_terminal"},
            ]
        }
    
    def find_businesses_in_radius(self, center: Location, radius_km: float, 
                                business_type: Optional[str] = None,
                                transport_mode: str = "driving") -> List[Dict[str, Any]]:
        """Find businesses within specified radius with transport considerations"""
        
        # Adjust radius based on transport mode
        effective_radius = min(radius_km, self.search_radius.get_radius(transport_mode))
        
        # Get area information for the center location
        area_info = self.get_area_info(center)
        
        # Find nearby areas within radius
        nearby_areas = []
        city_key = center.city.lower().replace(" ", "_") if center.city else ""
        
        if city_key in self.area_boundaries:
            city_areas = self.area_boundaries[city_key]
            
            for area_name, area_data in city_areas.items():
                area_center = self._get_area_center(area_data["bounds"])
                area_location = Location(
                    latitude=area_center["lat"],
                    longitude=area_center["lng"],
                    city=center.city,
                    area=area_data["area_info"].name
                )
                
                distance = self.location_service.calculate_distance(center, area_location)
                
                if distance <= effective_radius:
                    travel_info = self.location_service.calculate_travel_time(
                        center, area_location, transport_mode
                    )
                    
                    nearby_areas.append({
                        "area_name": area_data["area_info"].name,
                        "distance_km": distance,
                        "travel_time_minutes": travel_info["travel_time_minutes"],
                        "area_info": area_data["area_info"].to_dict(),
                        "suitability_score": self._calculate_area_suitability(
                            area_data["area_info"], business_type
                        )
                    })
        
        # Sort by suitability score and distance
        nearby_areas.sort(key=lambda x: (-x["suitability_score"], x["distance_km"]))
        
        return nearby_areas
    
    def get_area_info(self, location: Location) -> Optional[AreaInfo]:
        """Get detailed area information for a location"""
        
        city_key = location.city.lower().replace(" ", "_") if location.city else ""
        
        if city_key not in self.area_boundaries:
            return self._get_default_area_info(location)
        
        city_areas = self.area_boundaries[city_key]
        
        # Find which area the location falls into
        for area_name, area_data in city_areas.items():
            if self._point_in_bounds(location, area_data["bounds"]):
                return area_data["area_info"]
        
        # If not in any defined area, return default info
        return self._get_default_area_info(location)
    
    def find_nearest_metro_station(self, location: Location) -> Optional[Dict[str, Any]]:
        """Find the nearest metro station to a location"""
        
        city_key = location.city.lower().replace(" ", "_") if location.city else ""
        
        if city_key not in self.metro_stations:
            return None
        
        stations = self.metro_stations[city_key]
        nearest_station = None
        min_distance = float('inf')
        
        for station in stations:
            station_location = Location(
                latitude=station["lat"],
                longitude=station["lng"],
                city=location.city
            )
            
            distance = self.location_service.calculate_distance(location, station_location)
            
            if distance < min_distance:
                min_distance = distance
                nearest_station = {
                    **station,
                    "distance_km": distance,
                    "walking_time_minutes": int(distance / 4 * 60)  # 4 km/h walking speed
                }
        
        return nearest_station
    
    def find_nearest_transport_hub(self, location: Location, 
                                 hub_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Find nearest transport hub (airport, railway, bus terminal)"""
        
        city_key = location.city.lower().replace(" ", "_") if location.city else ""
        
        if city_key not in self.transport_hubs:
            return None
        
        hubs = self.transport_hubs[city_key]
        
        if hub_type:
            hubs = [hub for hub in hubs if hub["type"] == hub_type]
        
        nearest_hub = None
        min_distance = float('inf')
        
        for hub in hubs:
            hub_location = Location(
                latitude=hub["lat"],
                longitude=hub["lng"],
                city=location.city
            )
            
            distance = self.location_service.calculate_distance(location, hub_location)
            
            if distance < min_distance:
                min_distance = distance
                travel_info = self.location_service.calculate_travel_time(
                    location, hub_location, "driving"
                )
                
                nearest_hub = {
                    **hub,
                    "distance_km": distance,
                    "travel_time_minutes": travel_info["travel_time_minutes"]
                }
        
        return nearest_hub
    
    def get_accessibility_score(self, location: Location) -> Dict[str, Any]:
        """Calculate accessibility score based on transport options"""
        
        score_breakdown = {
            "metro_access": 0,
            "transport_hub_access": 0,
            "road_connectivity": 0,
            "overall_score": 0
        }
        
        # Metro accessibility (40% weight)
        nearest_metro = self.find_nearest_metro_station(location)
        if nearest_metro:
            if nearest_metro["distance_km"] <= 0.5:
                score_breakdown["metro_access"] = 10
            elif nearest_metro["distance_km"] <= 1.0:
                score_breakdown["metro_access"] = 8
            elif nearest_metro["distance_km"] <= 2.0:
                score_breakdown["metro_access"] = 6
            elif nearest_metro["distance_km"] <= 3.0:
                score_breakdown["metro_access"] = 4
            else:
                score_breakdown["metro_access"] = 2
        
        # Transport hub accessibility (30% weight)
        nearest_airport = self.find_nearest_transport_hub(location, "airport")
        nearest_railway = self.find_nearest_transport_hub(location, "railway")
        
        airport_score = 0
        if nearest_airport and nearest_airport["distance_km"] <= 30:
            airport_score = max(0, 5 - nearest_airport["distance_km"] / 6)
        
        railway_score = 0
        if nearest_railway and nearest_railway["distance_km"] <= 10:
            railway_score = max(0, 5 - nearest_railway["distance_km"] / 2)
        
        score_breakdown["transport_hub_access"] = min(10, airport_score + railway_score)
        
        # Road connectivity (30% weight) - based on area type and traffic
        area_info = self.get_area_info(location)
        if area_info:
            if area_info.area_type == "commercial":
                score_breakdown["road_connectivity"] = 9
            elif area_info.area_type == "mixed":
                score_breakdown["road_connectivity"] = 7
            else:
                score_breakdown["road_connectivity"] = 5
        else:
            score_breakdown["road_connectivity"] = 5
        
        # Calculate overall score (weighted average)
        score_breakdown["overall_score"] = (
            score_breakdown["metro_access"] * 0.4 +
            score_breakdown["transport_hub_access"] * 0.3 +
            score_breakdown["road_connectivity"] * 0.3
        )
        
        return score_breakdown
    
    def calculate_catchment_area(self, location: Location, 
                               transport_modes: List[str]) -> Dict[str, Any]:
        """Calculate catchment area coverage for different transport modes"""
        
        catchment_data = {
            "center": location.to_dict(),
            "coverage_by_mode": {},
            "total_coverage_area_km2": 0,
            "estimated_population_reach": 0
        }
        
        for mode in transport_modes:
            radius = self.search_radius.get_radius(mode)
            area_km2 = math.pi * radius * radius
            
            # Estimate population density based on location type
            area_info = self.get_area_info(location)
            population_density = self._estimate_population_density(area_info)
            
            estimated_population = int(area_km2 * population_density)
            
            catchment_data["coverage_by_mode"][mode] = {
                "radius_km": radius,
                "coverage_area_km2": round(area_km2, 2),
                "estimated_population": estimated_population,
                "travel_time_range": f"5-{int(radius/self._get_average_speed(mode)*60)} minutes"
            }
        
        # Calculate total coverage (union of all modes)
        max_radius = max(self.search_radius.get_radius(mode) for mode in transport_modes)
        total_area = math.pi * max_radius * max_radius
        area_info = self.get_area_info(location)
        population_density = self._estimate_population_density(area_info)
        
        catchment_data["total_coverage_area_km2"] = round(total_area, 2)
        catchment_data["estimated_population_reach"] = int(total_area * population_density)
        
        return catchment_data
    
    def _get_area_center(self, bounds: Dict[str, float]) -> Dict[str, float]:
        """Calculate center point of area bounds"""
        return {
            "lat": (bounds["north"] + bounds["south"]) / 2,
            "lng": (bounds["east"] + bounds["west"]) / 2
        }
    
    def _point_in_bounds(self, location: Location, bounds: Dict[str, float]) -> bool:
        """Check if point is within area bounds"""
        return (bounds["south"] <= location.latitude <= bounds["north"] and
                bounds["west"] <= location.longitude <= bounds["east"])
    
    def _get_default_area_info(self, location: Location) -> AreaInfo:
        """Get default area information when specific data not available"""
        return AreaInfo(
            name=location.city or "Unknown Area",
            area_type="mixed",
            safety_rating=3.5,
            traffic_level="medium",
            parking_availability="moderate",
            public_transport=["bus", "auto", "taxi"],
            landmarks=[],
            average_rent_per_sqft=100.0,
            commercial_density="medium"
        )
    
    def _calculate_area_suitability(self, area_info: AreaInfo, 
                                  business_type: Optional[str]) -> float:
        """Calculate how suitable an area is for a specific business type"""
        
        base_score = 5.0  # Base suitability score
        
        # Business type specific adjustments
        if business_type == "movie_theater":
            if area_info.area_type in ["commercial", "mixed"]:
                base_score += 2.0
            if area_info.commercial_density == "high":
                base_score += 1.0
            if "metro" in area_info.public_transport:
                base_score += 1.0
                
        elif business_type == "restaurant":
            if area_info.area_type in ["commercial", "mixed"]:
                base_score += 1.5
            if area_info.commercial_density in ["medium", "high"]:
                base_score += 1.0
            if area_info.parking_availability in ["moderate", "abundant"]:
                base_score += 0.5
                
        elif business_type == "shopping_mall":
            if area_info.area_type == "commercial":
                base_score += 2.5
            if area_info.parking_availability in ["abundant", "moderate"]:
                base_score += 1.5
            if "metro" in area_info.public_transport:
                base_score += 1.0
        
        # General factors
        base_score += area_info.safety_rating * 0.3
        
        if area_info.traffic_level == "low":
            base_score += 0.5
        elif area_info.traffic_level == "very_high":
            base_score -= 0.5
        
        return min(10.0, max(0.0, base_score))
    
    def _estimate_population_density(self, area_info: Optional[AreaInfo]) -> float:
        """Estimate population density per km² based on area characteristics"""
        
        if not area_info:
            return 5000  # Default density
        
        # Base density by area type (people per km²)
        density_by_type = {
            "commercial": 8000,
            "mixed": 12000,
            "residential": 15000,
            "industrial": 3000
        }
        
        base_density = density_by_type.get(area_info.area_type, 8000)
        
        # Adjust by commercial density
        if area_info.commercial_density == "high":
            base_density *= 1.3
        elif area_info.commercial_density == "low":
            base_density *= 0.8
        
        return base_density
    
    def _get_average_speed(self, transport_mode: str) -> float:
        """Get average speed for transport mode in km/h"""
        speeds = {
            "walking": 4,
            "cycling": 12,
            "auto": 20,
            "driving": 25,
            "metro": 35,
            "bus": 18
        }
        
        return speeds.get(transport_mode, 25)