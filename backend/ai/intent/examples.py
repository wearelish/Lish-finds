"""
Example queries and expected intents for testing and training.

Used for validating intent extraction accuracy and training examples.
"""

from ai.intent.models import (
    SearchIntent, IntentCategory, PriceRange, TimeOfDay, Mood,
    LocationPreference, TimePreference, BudgetPreference
)

# Example queries with expected intents
INTENT_EXAMPLES = [
    {
        "query": "Find a quiet café with Wi-Fi under ₹300 that is open now",
        "expected_intent": SearchIntent(
            original_query="Find a quiet café with Wi-Fi under ₹300 that is open now",
            primary_category=IntentCategory.CAFE,
            keywords=["quiet", "café", "Wi-Fi", "₹300", "open now"],
            required_amenities=["Wi-Fi"],
            mood=Mood.QUIET,
            time=TimePreference(open_now=True),
            budget=BudgetPreference(max_budget=300, price_range=PriceRange.BUDGET),
            confidence_score=0.9
        )
    },
    {
        "query": "Best romantic restaurant for dinner date near Connaught Place",
        "expected_intent": SearchIntent(
            original_query="Best romantic restaurant for dinner date near Connaught Place",
            primary_category=IntentCategory.RESTAURANT,
            keywords=["best", "romantic", "restaurant", "dinner", "date", "Connaught Place"],
            mood=Mood.ROMANTIC,
            occasion="date",
            time=TimePreference(time_of_day=TimeOfDay.EVENING),
            location=LocationPreference(landmark="Connaught Place"),
            confidence_score=0.85
        )
    },
    {
        "query": "Family-friendly restaurant with parking for 6 people",
        "expected_intent": SearchIntent(
            original_query="Family-friendly restaurant with parking for 6 people",
            primary_category=IntentCategory.RESTAURANT,
            keywords=["family-friendly", "restaurant", "parking", "6 people"],
            required_amenities=["parking"],
            mood=Mood.FAMILY_FRIENDLY,
            group_size=6,
            confidence_score=0.8
        )
    },
    {
        "query": "Cheap food court open late night",
        "expected_intent": SearchIntent(
            original_query="Cheap food court open late night",
            primary_category=IntentCategory.RESTAURANT,
            secondary_categories=[IntentCategory.ENTERTAINMENT],
            keywords=["cheap", "food court", "late night"],
            time=TimePreference(time_of_day=TimeOfDay.LATE_NIGHT),
            budget=BudgetPreference(price_range=PriceRange.BUDGET),
            confidence_score=0.75
        )
    },
    {
        "query": "Shopping mall with branded stores and food court",
        "expected_intent": SearchIntent(
            original_query="Shopping mall with branded stores and food court",
            primary_category=IntentCategory.SHOPPING,
            secondary_categories=[IntentCategory.RESTAURANT],
            keywords=["shopping mall", "branded stores", "food court"],
            preferred_amenities=["food court", "brand stores"],
            confidence_score=0.7
        )
    },
    {
        "query": "Gym near me with good reviews under ₹2000 per month",
        "expected_intent": SearchIntent(
            original_query="Gym near me with good reviews under ₹2000 per month",
            primary_category=IntentCategory.FITNESS,
            keywords=["gym", "near me", "good reviews", "₹2000", "per month"],
            location=LocationPreference(max_distance_km=5.0),
            budget=BudgetPreference(max_budget=2000, price_range=PriceRange.MODERATE),
            min_rating=4.0,
            confidence_score=0.8
        )
    },
    {
        "query": "Vegetarian restaurant with outdoor seating for lunch",
        "expected_intent": SearchIntent(
            original_query="Vegetarian restaurant with outdoor seating for lunch",
            primary_category=IntentCategory.RESTAURANT,
            keywords=["vegetarian", "restaurant", "outdoor seating", "lunch"],
            dietary_preferences=["vegetarian"],
            preferred_amenities=["outdoor seating"],
            time=TimePreference(time_of_day=TimeOfDay.AFTERNOON),
            confidence_score=0.85
        )
    },
    {
        "query": "Bar with live music and good ambiance",
        "expected_intent": SearchIntent(
            original_query="Bar with live music and good ambiance",
            primary_category=IntentCategory.BAR,
            keywords=["bar", "live music", "good ambiance"],
            preferred_amenities=["live music"],
            mood=Mood.LIVELY,
            time=TimePreference(time_of_day=TimeOfDay.EVENING),
            confidence_score=0.8
        )
    },
    {
        "query": "Coworking space with Wi-Fi and coffee",
        "expected_intent": SearchIntent(
            original_query="Coworking space with Wi-Fi and coffee",
            primary_category=IntentCategory.SERVICES,
            keywords=["coworking space", "Wi-Fi", "coffee"],
            required_amenities=["Wi-Fi"],
            preferred_amenities=["coffee"],
            mood=Mood.WORK_FRIENDLY,
            confidence_score=0.8
        )
    },
    {
        "query": "Book a table for birthday party for 15 people",
        "expected_intent": SearchIntent(
            original_query="Book a table for birthday party for 15 people",
            primary_category=IntentCategory.RESTAURANT,
            keywords=["book", "table", "birthday party", "15 people"],
            occasion="birthday party",
            group_size=15,
            mood=Mood.PARTY,
            confidence_score=0.85
        )
    }
]

# Common query patterns for training
QUERY_PATTERNS = [
    # Restaurant patterns
    {
        "pattern": "{adjective} restaurant for {occasion}",
        "examples": [
            "romantic restaurant for date",
            "family restaurant for dinner", 
            "casual restaurant for lunch"
        ],
        "category": IntentCategory.RESTAURANT
    },
    
    # Café patterns
    {
        "pattern": "{adjective} café with {amenity}",
        "examples": [
            "quiet café with Wi-Fi",
            "cozy café with outdoor seating",
            "modern café with good coffee"
        ],
        "category": IntentCategory.CAFE
    },
    
    # Budget patterns
    {
        "pattern": "{business_type} under ₹{amount}",
        "examples": [
            "restaurant under ₹500",
            "café under ₹300",
            "shopping under ₹1000"
        ],
        "budget_related": True
    },
    
    # Location patterns
    {
        "pattern": "{business_type} near {location}",
        "examples": [
            "restaurant near me",
            "café near Connaught Place",
            "mall near metro station"
        ],
        "location_related": True
    },
    
    # Time patterns
    {
        "pattern": "{business_type} open {time}",
        "examples": [
            "restaurant open now",
            "café open late",
            "shop open 24 hours"
        ],
        "time_related": True
    }
]

# Common amenities by category
CATEGORY_AMENITIES = {
    IntentCategory.RESTAURANT: [
        "parking", "outdoor seating", "home delivery", "takeaway",
        "air conditioning", "live music", "bar", "private dining",
        "wheelchair accessible", "kid-friendly", "pet friendly"
    ],
    IntentCategory.CAFE: [
        "Wi-Fi", "outdoor seating", "laptop friendly", "power outlets",
        "quiet atmosphere", "good coffee", "pastries", "meeting rooms",
        "parking", "air conditioning"
    ],
    IntentCategory.SHOPPING: [
        "parking", "food court", "brand stores", "escalator", "elevator",
        "wheelchair accessible", "ATM", "restroom", "air conditioning",
        "entertainment zone", "kids play area"
    ],
    IntentCategory.FITNESS: [
        "parking", "locker room", "shower", "trainer", "equipment variety",
        "air conditioning", "group classes", "swimming pool", "steam room",
        "nutritionist", "flexible timings"
    ],
    IntentCategory.BAR: [
        "live music", "DJ", "dance floor", "outdoor seating", "parking",
        "happy hour", "food menu", "cocktails", "beer", "wine selection",
        "sports screening", "private booths"
    ]
}

# Common dietary preferences
DIETARY_PREFERENCES = [
    "vegetarian", "vegan", "jain", "halal", "kosher", 
    "gluten-free", "sugar-free", "keto", "diabetic-friendly"
]

# Common accessibility needs
ACCESSIBILITY_NEEDS = [
    "wheelchair accessible", "ramp access", "elevator", "braille menu",
    "hearing aid compatible", "wide doorways", "accessible parking",
    "accessible restroom"
]