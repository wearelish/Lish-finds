"""
Realistic Business Data Generator

Creates location-specific mock data that reflects real-world accuracy including:
- Movie theaters with ₹70+ minimum pricing
- Restaurants with location-appropriate pricing
- Shopping malls with realistic brand presence
- Operating hours based on local regulations
- Area-specific business characteristics
"""

from typing import Dict, Any, List, Optional
import json
import random
from datetime import datetime, time
from ..services.location_service import Location
from ..services.business_rules_engine import BusinessRulesEngine


class RealisticBusinessDataGenerator:
    """Generates realistic business data based on location constraints"""
    
    def __init__(self):
        self.business_rules = BusinessRulesEngine()
        
        # Real movie theater chains in India
        self.movie_theater_chains = {
            "premium": ["PVR Cinemas", "INOX", "Cinepolis", "Carnival Cinemas"],
            "standard": ["Miraj Cinemas", "Wave Cinemas", "Fun Cinemas", "Delite Cinemas"],
            "budget": ["Shree Cinemas", "Roopbani Cinema", "Mukta Cinemas"]
        }
        
        # Real restaurant chains and types
        self.restaurant_chains = {
            "fine_dining": ["Taj Hotels", "ITC Hotels", "Mainland China", "Barbeque Nation"],
            "casual_dining": ["Cafe Coffee Day", "Pizza Hut", "Domino's", "KFC"],
            "fast_food": ["McDonald's", "Subway", "Burger King", "Taco Bell"],
            "local": ["Saravana Bhavan", "Udupi Krishna", "Haldiram's", "Bikanervala"]
        }
        
        # Shopping mall chains
        self.mall_chains = ["Phoenix Mills", "DLF Malls", "Nexus Malls", "Forum Malls", "Inorbit Malls"]
        
    def generate_movie_theaters(self, location: Location, count: int = 5) -> List[Dict[str, Any]]:
        """Generate realistic movie theater data with ₹70+ constraint"""
        
        theaters = []
        tier = self.business_rules._get_location_tier(location)
        pricing_rules = self.business_rules.movie_pricing_rules["tier_pricing"][tier]
        
        for i in range(count):
            # Select theater type based on location tier
            if tier in ["premium_metro", "metro"]:
                chain_type = random.choice(["premium", "standard"])
            else:
                chain_type = random.choice(["standard", "budget"])
            
            chain_name = random.choice(self.movie_theater_chains[chain_type])
            
            # Generate location coordinates near the center
            lat_offset = random.uniform(-0.02, 0.02)
            lng_offset = random.uniform(-0.02, 0.02)
            
            theater_location = Location(
                latitude=location.latitude + lat_offset,
                longitude=location.longitude + lng_offset,
                city=location.city,
                area=f"{location.city} Area {i+1}"
            )
            
            # Generate pricing - ALWAYS ₹70 or above
            base_price = max(70, pricing_rules["base_range"][0] + random.randint(-10, 20))
            premium_price = base_price * random.uniform(1.5, 2.0)
            
            theater = {
                "id": f"theater_{location.city}_{i+1}",
                "name": f"{chain_name} {location.city}",
                "type": "movie_theater",
                "chain": chain_name,
                "location": theater_location.to_dict(),
                "pricing": {
                    "regular_2d": max(70, int(base_price)),  # NEVER below ₹70
                    "regular_3d": max(90, int(base_price * 1.3)),
                    "premium_2d": max(120, int(premium_price)),
                    "premium_3d": max(150, int(premium_price * 1.3)),
                    "imax": max(200, int(base_price * 2.5)),
                    "4dx": max(250, int(base_price * 3.0))
                },
                "screens": random.randint(4, 12),
                "seating_capacity": random.randint(200, 400) * random.randint(4, 12),
                "amenities": self._get_theater_amenities(chain_type, tier),
                "operating_hours": {
                    "monday": "09:00-23:30",
                    "tuesday": "09:00-23:30", 
                    "wednesday": "09:00-23:30",
                    "thursday": "09:00-23:30",
                    "friday": "09:00-01:00",
                    "saturday": "09:00-01:00",
                    "sunday": "09:00-23:30"
                },
                "food_pricing": {
                    "popcorn_small": random.randint(150, 250),
                    "popcorn_large": random.randint(250, 400),
                    "cold_drink": random.randint(100, 180),
                    "nachos": random.randint(200, 350)
                },
                "booking_fees": {
                    "convenience_fee": random.randint(15, 25),
                    "processing_fee": random.randint(10, 20)
                },
                "rating": round(random.uniform(3.5, 4.8), 1),
                "reviews_count": random.randint(500, 5000),
                "parking": tier in ["premium_metro", "metro"],
                "wheelchair_accessible": chain_type == "premium"
            }
            
            theaters.append(theater)
        
        return theaters
    
    def generate_restaurants(self, location: Location, count: int = 10) -> List[Dict[str, Any]]:
        """Generate realistic restaurant data with location-appropriate pricing"""
        
        restaurants = []
        tier = self.business_rules._get_location_tier(location)
        pricing_rules = self.business_rules.restaurant_pricing_rules
        
        # Distribution of restaurant types based on location tier
        if tier in ["premium_metro", "metro"]:
            type_distribution = {"fine_dining": 0.3, "casual_dining": 0.4, "fast_food": 0.2, "local": 0.1}
        else:
            type_distribution = {"fine_dining": 0.1, "casual_dining": 0.3, "fast_food": 0.3, "local": 0.3}
        
        for i in range(count):
            # Select restaurant type
            restaurant_type = random.choices(
                list(type_distribution.keys()),
                weights=list(type_distribution.values())
            )[0]
            
            chain_name = random.choice(self.restaurant_chains[restaurant_type])
            
            # Generate location
            lat_offset = random.uniform(-0.03, 0.03)
            lng_offset = random.uniform(-0.03, 0.03)
            
            restaurant_location = Location(
                latitude=location.latitude + lat_offset,
                longitude=location.longitude + lng_offset,
                city=location.city,
                area=f"{location.city} Restaurant District {i+1}"
            )
            
            # Get realistic pricing for this type and tier
            price_range = pricing_rules[restaurant_type][tier]
            avg_cost = random.randint(price_range[0], price_range[1])
            
            restaurant = {
                "id": f"restaurant_{location.city}_{i+1}",
                "name": f"{chain_name} {location.city}",
                "type": "restaurant",
                "restaurant_type": restaurant_type,
                "chain": chain_name,
                "location": restaurant_location.to_dict(),
                "cuisine": self._get_cuisine_type(restaurant_type, chain_name),
                "pricing": {
                    "average_cost_per_person": avg_cost,
                    "price_range": self._get_price_range_symbol(avg_cost),
                    "minimum_order": max(50, int(avg_cost * 0.3)) if restaurant_type == "fast_food" else 0,
                    "service_charge_percent": 10 if restaurant_type == "fine_dining" else 0,
                    "taxes": {
                        "cgst_percent": 2.5,
                        "sgst_percent": 2.5
                    }
                },
                "operating_hours": self._get_restaurant_hours(restaurant_type, location.state),
                "amenities": self._get_restaurant_amenities(restaurant_type, tier),
                "seating_capacity": self._get_seating_capacity(restaurant_type),
                "rating": round(random.uniform(3.2, 4.7), 1),
                "reviews_count": random.randint(200, 3000),
                "delivery_available": restaurant_type in ["fast_food", "casual_dining"],
                "alcohol_served": self._can_serve_alcohol(location.state, restaurant_type),
                "dietary_options": self._get_dietary_options(restaurant_type, location.state)
            }
            
            restaurants.append(restaurant)
        
        return restaurants
    
    def generate_shopping_malls(self, location: Location, count: int = 3) -> List[Dict[str, Any]]:
        """Generate realistic shopping mall data"""
        
        malls = []
        tier = self.business_rules._get_location_tier(location)
        
        for i in range(count):
            mall_name = random.choice(self.mall_chains)
            
            # Generate location
            lat_offset = random.uniform(-0.05, 0.05)
            lng_offset = random.uniform(-0.05, 0.05)
            
            mall_location = Location(
                latitude=location.latitude + lat_offset,
                longitude=location.longitude + lng_offset,
                city=location.city,
                area=f"{location.city} Shopping District {i+1}"
            )
            
            # Mall size and brand count based on tier
            if tier == "premium_metro":
                floors = random.randint(4, 8)
                brands = random.randint(150, 300)
                anchor_stores = ["Lifestyle", "Westside", "Pantaloons", "Central", "Max"]
            elif tier == "metro":
                floors = random.randint(3, 6)
                brands = random.randint(100, 200)
                anchor_stores = ["Big Bazaar", "Reliance Trends", "Shoppers Stop"]
            else:
                floors = random.randint(2, 4)
                brands = random.randint(50, 120)
                anchor_stores = ["V-Mart", "Brand Factory", "Lifestyle"]
            
            mall = {
                "id": f"mall_{location.city}_{i+1}",
                "name": f"{mall_name} {location.city}",
                "type": "shopping_mall",
                "chain": mall_name,
                "location": mall_location.to_dict(),
                "details": {
                    "floors": floors,
                    "total_stores": brands,
                    "anchor_stores": random.sample(anchor_stores, min(3, len(anchor_stores))),
                    "food_court": True,
                    "multiplex": random.choice([True, False]),
                    "parking_capacity": random.randint(500, 2000)
                },
                "operating_hours": {
                    "weekday": "10:00-22:00",
                    "weekend": "10:00-23:00"
                },
                "amenities": self._get_mall_amenities(tier),
                "rating": round(random.uniform(3.8, 4.6), 1),
                "reviews_count": random.randint(1000, 8000),
                "categories": ["Fashion", "Electronics", "Food & Dining", "Entertainment"],
                "price_segments": self._get_mall_price_segments(tier)
            }
            
            malls.append(mall)
        
        return malls
    
    def _get_theater_amenities(self, chain_type: str, tier: str) -> List[str]:
        """Get realistic theater amenities based on type and location"""
        
        base_amenities = ["Air Conditioning", "Online Booking", "Snacks Counter"]
        
        if chain_type == "premium":
            base_amenities.extend([
                "Recliner Seats", "Dolby Atmos", "4K Projection", 
                "Premium Food Menu", "Valet Parking", "Wheelchair Access"
            ])
            if tier == "premium_metro":
                base_amenities.extend(["IMAX", "4DX", "Gold Class Lounge"])
        
        elif chain_type == "standard":
            base_amenities.extend([
                "Digital Projection", "Comfortable Seating", "Multiple Screens"
            ])
            if tier in ["premium_metro", "metro"]:
                base_amenities.extend(["3D Capable", "Surround Sound"])
        
        return base_amenities
    
    def _get_cuisine_type(self, restaurant_type: str, chain_name: str) -> List[str]:
        """Get cuisine types based on restaurant"""
        
        cuisine_map = {
            "Taj Hotels": ["Indian", "Continental", "Chinese"],
            "Mainland China": ["Chinese", "Thai", "Pan Asian"],
            "Pizza Hut": ["Italian", "American"],
            "McDonald's": ["American", "Fast Food"],
            "Saravana Bhavan": ["South Indian", "Vegetarian"],
            "Haldiram's": ["North Indian", "Chaat", "Sweets"]
        }
        
        if chain_name in cuisine_map:
            return cuisine_map[chain_name]
        
        # Default based on type
        if restaurant_type == "fine_dining":
            return ["Multi-cuisine", "Continental", "Indian"]
        elif restaurant_type == "fast_food":
            return ["Fast Food", "American"]
        else:
            return ["Indian", "Chinese"]
    
    def _get_price_range_symbol(self, avg_cost: int) -> str:
        """Convert average cost to price range symbols"""
        
        if avg_cost < 300:
            return "₹"
        elif avg_cost < 800:
            return "₹₹"
        elif avg_cost < 1500:
            return "₹₹₹"
        else:
            return "₹₹₹₹"
    
    def _get_restaurant_hours(self, restaurant_type: str, state: Optional[str]) -> Dict[str, str]:
        """Get realistic operating hours based on type and location"""
        
        if restaurant_type == "fine_dining":
            return {
                "monday": "19:00-23:30",
                "tuesday": "19:00-23:30",
                "wednesday": "19:00-23:30", 
                "thursday": "19:00-23:30",
                "friday": "19:00-00:30",
                "saturday": "19:00-00:30",
                "sunday": "19:00-23:30"
            }
        
        elif restaurant_type == "fast_food":
            return {
                "monday": "08:00-23:00",
                "tuesday": "08:00-23:00",
                "wednesday": "08:00-23:00",
                "thursday": "08:00-23:00", 
                "friday": "08:00-24:00",
                "saturday": "08:00-24:00",
                "sunday": "08:00-23:00"
            }
        
        else:  # casual_dining, local
            return {
                "monday": "11:00-23:00",
                "tuesday": "11:00-23:00",
                "wednesday": "11:00-23:00",
                "thursday": "11:00-23:00",
                "friday": "11:00-23:30",
                "saturday": "11:00-23:30", 
                "sunday": "11:00-23:00"
            }
    
    def _get_restaurant_amenities(self, restaurant_type: str, tier: str) -> List[str]:
        """Get restaurant amenities based on type and tier"""
        
        base_amenities = ["Air Conditioning", "Credit Card Accepted"]
        
        if restaurant_type == "fine_dining":
            base_amenities.extend([
                "Table Reservation", "Valet Parking", "Live Music",
                "Private Dining", "Wine List", "Wheelchair Accessible"
            ])
        
        elif restaurant_type == "casual_dining":
            base_amenities.extend([
                "Family Friendly", "Takeaway Available", "Home Delivery"
            ])
            if tier in ["premium_metro", "metro"]:
                base_amenities.extend(["WiFi", "Outdoor Seating"])
        
        elif restaurant_type == "fast_food":
            base_amenities.extend([
                "Quick Service", "Online Ordering", "Drive Through"
            ])
        
        return base_amenities
    
    def _get_seating_capacity(self, restaurant_type: str) -> int:
        """Get realistic seating capacity"""
        
        capacity_ranges = {
            "fine_dining": (40, 120),
            "casual_dining": (60, 200),
            "fast_food": (30, 80),
            "local": (20, 60)
        }
        
        min_cap, max_cap = capacity_ranges.get(restaurant_type, (40, 100))
        return random.randint(min_cap, max_cap)
    
    def _can_serve_alcohol(self, state: Optional[str], restaurant_type: str) -> bool:
        """Check if restaurant can serve alcohol based on state laws"""
        
        # Dry states where alcohol is banned
        dry_states = ["Gujarat", "Bihar", "Nagaland", "Mizoram"]
        
        if state in dry_states:
            return False
        
        # Only fine dining and some casual dining serve alcohol
        if restaurant_type in ["fine_dining"]:
            return True
        elif restaurant_type == "casual_dining":
            return random.choice([True, False])  # Some do, some don't
        
        return False
    
    def _get_dietary_options(self, restaurant_type: str, state: Optional[str]) -> List[str]:
        """Get dietary options based on restaurant type and location"""
        
        options = ["Vegetarian Options"]
        
        # States with high vegetarian population
        high_veg_states = ["Gujarat", "Rajasthan", "Madhya Pradesh", "Haryana"]
        
        if state in high_veg_states:
            options.extend(["Pure Vegetarian", "Jain Food Available"])
        
        if restaurant_type != "local":  # International chains
            options.extend(["Vegan Options Available"])
        
        # Muslim-majority areas or general inclusivity
        if restaurant_type in ["fine_dining", "casual_dining"]:
            options.append("Halal Available")
        
        return options
    
    def _get_mall_amenities(self, tier: str) -> List[str]:
        """Get mall amenities based on location tier"""
        
        base_amenities = [
            "Air Conditioning", "Escalators", "Food Court", 
            "ATM", "Restrooms", "Security"
        ]
        
        if tier == "premium_metro":
            base_amenities.extend([
                "Valet Parking", "Personal Shopping Assistant", 
                "VIP Lounge", "Currency Exchange", "Concierge Service",
                "Electric Car Charging", "Premium Brands"
            ])
        
        elif tier == "metro":
            base_amenities.extend([
                "Multi-level Parking", "WiFi", "Kids Play Area",
                "Gaming Zone", "Wheelchair Access"
            ])
        
        else:
            base_amenities.extend([
                "Parking Available", "Family Entertainment"
            ])
        
        return base_amenities
    
    def _get_mall_price_segments(self, tier: str) -> List[str]:
        """Get price segments available in mall"""
        
        if tier == "premium_metro":
            return ["Luxury", "Premium", "Mid-range", "Budget"]
        elif tier == "metro":
            return ["Premium", "Mid-range", "Budget"]
        else:
            return ["Mid-range", "Budget", "Value"]
    
    def generate_comprehensive_location_data(self, location: Location) -> Dict[str, Any]:
        """Generate complete business ecosystem for a location"""
        
        # Generate different business types
        movie_theaters = self.generate_movie_theaters(location, 3)
        restaurants = self.generate_restaurants(location, 8)
        shopping_malls = self.generate_shopping_malls(location, 2)
        
        # Add other business types
        other_businesses = self._generate_other_businesses(location)
        
        return {
            "location": location.to_dict(),
            "location_tier": self.business_rules._get_location_tier(location),
            "businesses": {
                "movie_theaters": movie_theaters,
                "restaurants": restaurants,
                "shopping_malls": shopping_malls,
                "others": other_businesses
            },
            "location_statistics": {
                "total_businesses": len(movie_theaters) + len(restaurants) + len(shopping_malls) + len(other_businesses),
                "average_rating": self._calculate_average_rating(movie_theaters + restaurants + shopping_malls),
                "price_range_distribution": self._get_price_distribution(restaurants),
                "business_density": self._calculate_business_density(location)
            },
            "accessibility": {
                "metro_stations": self._get_nearby_metro_stations(location),
                "transport_hubs": self._get_nearby_transport_hubs(location),
                "parking_availability": self._assess_parking_availability(location)
            }
        }
    
    def _generate_other_businesses(self, location: Location) -> List[Dict[str, Any]]:
        """Generate other types of businesses"""
        
        other_businesses = []
        tier = self.business_rules._get_location_tier(location)
        
        # Banks
        banks = ["SBI", "HDFC Bank", "ICICI Bank", "Axis Bank", "Kotak Bank"]
        for i, bank in enumerate(banks[:3]):
            other_businesses.append({
                "id": f"bank_{location.city}_{i+1}",
                "name": f"{bank} {location.city} Branch",
                "type": "bank",
                "location": {
                    "latitude": location.latitude + random.uniform(-0.01, 0.01),
                    "longitude": location.longitude + random.uniform(-0.01, 0.01)
                },
                "operating_hours": {"weekday": "10:00-16:00", "saturday": "10:00-14:00", "sunday": "Closed"},
                "services": ["ATM", "Locker Facility", "Internet Banking", "Mobile Banking"],
                "rating": round(random.uniform(3.5, 4.2), 1)
            })
        
        # Pharmacies
        pharmacies = ["Apollo Pharmacy", "MedPlus", "Netmeds", "1mg"]
        for i, pharmacy in enumerate(pharmacies[:2]):
            other_businesses.append({
                "id": f"pharmacy_{location.city}_{i+1}",
                "name": f"{pharmacy} {location.city}",
                "type": "pharmacy",
                "location": {
                    "latitude": location.latitude + random.uniform(-0.01, 0.01),
                    "longitude": location.longitude + random.uniform(-0.01, 0.01)
                },
                "operating_hours": {"daily": "08:00-22:00"},
                "services": ["Prescription Medicines", "OTC Drugs", "Health Products", "Home Delivery"],
                "rating": round(random.uniform(4.0, 4.5), 1)
            })
        
        return other_businesses
    
    def _calculate_average_rating(self, businesses: List[Dict[str, Any]]) -> float:
        """Calculate average rating across businesses"""
        
        if not businesses:
            return 0.0
        
        total_rating = sum(business.get("rating", 0.0) for business in businesses)
        return round(total_rating / len(businesses), 2)
    
    def _get_price_distribution(self, restaurants: List[Dict[str, Any]]) -> Dict[str, int]:
        """Get price range distribution"""
        
        distribution = {"₹": 0, "₹₹": 0, "₹₹₹": 0, "₹₹₹₹": 0}
        
        for restaurant in restaurants:
            price_range = restaurant.get("pricing", {}).get("price_range", "₹₹")
            if price_range in distribution:
                distribution[price_range] += 1
        
        return distribution
    
    def _calculate_business_density(self, location: Location) -> str:
        """Calculate business density for the area"""
        
        tier = self.business_rules._get_location_tier(location)
        
        density_map = {
            "premium_metro": "very_high",
            "metro": "high", 
            "tier1": "medium",
            "tier2": "low",
            "tier3": "very_low"
        }
        
        return density_map.get(tier, "medium")
    
    def _get_nearby_metro_stations(self, location: Location) -> List[Dict[str, Any]]:
        """Get nearby metro stations (mock data)"""
        
        # This would integrate with the AreaMappingService in real implementation
        city_key = location.city.lower().replace(" ", "_") if location.city else ""
        
        metro_cities = ["mumbai", "delhi", "bangalore", "kolkata", "chennai", "hyderabad"]
        
        if city_key in metro_cities:
            return [
                {
                    "name": f"{location.city} Central Metro",
                    "distance_km": round(random.uniform(0.5, 3.0), 1),
                    "lines": ["Line 1"]
                },
                {
                    "name": f"{location.city} Junction Metro", 
                    "distance_km": round(random.uniform(1.0, 5.0), 1),
                    "lines": ["Line 2"]
                }
            ]
        
        return []
    
    def _get_nearby_transport_hubs(self, location: Location) -> Dict[str, Any]:
        """Get nearby transport hubs"""
        
        return {
            "airport": {
                "name": f"{location.city} Airport",
                "distance_km": random.randint(15, 45),
                "travel_time_minutes": random.randint(30, 90)
            },
            "railway_station": {
                "name": f"{location.city} Railway Station",
                "distance_km": random.randint(3, 15),
                "travel_time_minutes": random.randint(15, 45)
            },
            "bus_terminal": {
                "name": f"{location.city} Bus Terminal",
                "distance_km": random.randint(2, 10),
                "travel_time_minutes": random.randint(10, 30)
            }
        }
    
    def _assess_parking_availability(self, location: Location) -> str:
        """Assess parking availability in the area"""
        
        tier = self.business_rules._get_location_tier(location)
        
        if tier == "premium_metro":
            return random.choice(["limited", "moderate"])  # High-end areas have parking challenges
        elif tier == "metro":
            return random.choice(["moderate", "limited"])
        else:
            return random.choice(["abundant", "moderate"])
    
    def get_location_specific_constraints_data(self, location: Location) -> Dict[str, Any]:
        """Get all location-specific constraints and rules"""
        
        tier = self.business_rules._get_location_tier(location)
        state_restrictions = self.business_rules._get_state_restrictions(location.state)
        
        return {
            "location": location.to_dict(),
            "tier": tier,
            "constraints": {
                "movie_theater": {
                    "minimum_ticket_price": 70.0,  # ABSOLUTE MINIMUM
                    "typical_price_ranges": self.business_rules.movie_pricing_rules["tier_pricing"][tier],
                    "operating_hours": {
                        "earliest_show": "09:00",
                        "latest_show": "23:30", 
                        "friday_saturday_extended": "01:00"
                    }
                },
                "restaurant": {
                    "price_ranges_per_person": {
                        restaurant_type: self.business_rules.restaurant_pricing_rules[restaurant_type][tier]
                        for restaurant_type in ["street_food", "fast_food", "casual_dining", "fine_dining"]
                    },
                    "alcohol_restrictions": state_restrictions,
                    "gst_rates": {
                        "food_under_1000": 5,
                        "food_over_1000": 18,
                        "alcohol": 28
                    }
                },
                "general": {
                    "state_restrictions": state_restrictions,
                    "dry_days": self._get_dry_days_calendar(location.state),
                    "festival_closures": self._get_festival_calendar(location.state)
                }
            }
        }
    
    def _get_dry_days_calendar(self, state: Optional[str]) -> List[str]:
        """Get dry days calendar for the state"""
        
        national_dry_days = [
            "2024-01-26",  # Republic Day
            "2024-08-15",  # Independence Day
            "2024-10-02"   # Gandhi Jayanti
        ]
        
        # Add state-specific dry days
        if state == "Maharashtra":
            national_dry_days.extend([
                "2024-05-01",  # Maharashtra Day
                "First Saturday of every month",
                "Third Saturday of every month"
            ])
        
        return national_dry_days
    
    def _get_festival_calendar(self, state: Optional[str]) -> List[Dict[str, str]]:
        """Get festival closure calendar"""
        
        return [
            {"date": "2024-03-08", "festival": "Holi", "impact": "Most businesses closed"},
            {"date": "2024-04-17", "festival": "Ram Navami", "impact": "Partial closures"},
            {"date": "2024-10-31", "festival": "Diwali", "impact": "Most businesses closed"},
            {"date": "2024-12-25", "festival": "Christmas", "impact": "Many businesses closed"}
        ]


# Example usage and data validation
def validate_generated_data():
    """Validate that generated data meets all constraints"""
    
    generator = RealisticBusinessDataGenerator()
    
    # Test Mumbai (premium metro)
    mumbai_location = Location(
        latitude=19.0760, longitude=72.8777, 
        city="Mumbai", state="Maharashtra"
    )
    
    mumbai_data = generator.generate_comprehensive_location_data(mumbai_location)
    
    # Validate movie theater pricing constraint
    for theater in mumbai_data["businesses"]["movie_theaters"]:
        for screen_type, price in theater["pricing"].items():
            assert price >= 70, f"Movie ticket price {price} for {screen_type} is below ₹70 minimum!"
    
    print("✅ All movie theater prices are ≥ ₹70")
    print(f"Generated {len(mumbai_data['businesses']['movie_theaters'])} theaters")
    print(f"Generated {len(mumbai_data['businesses']['restaurants'])} restaurants") 
    print(f"Generated {len(mumbai_data['businesses']['shopping_malls'])} malls")
    
    return mumbai_data


if __name__ == "__main__":
    # Validate data generation
    sample_data = validate_generated_data()
    print(json.dumps(sample_data, indent=2, default=str))