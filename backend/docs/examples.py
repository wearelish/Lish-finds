"""
API usage examples and code samples for LishFind API.

Provides comprehensive examples for all major API endpoints and use cases.
"""

# Authentication Examples
AUTH_EXAMPLES = {
    "register": {
        "description": "Register a new user account",
        "request": {
            "email": "user@example.com",
            "password": "SecurePassword123!",
            "full_name": "John Doe",
            "role": "user"
        },
        "response": {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "email": "user@example.com",
            "full_name": "John Doe",
            "role": "user",
            "is_active": True,
            "is_verified": False,
            "created_at": "2024-01-15T10:30:00Z"
        },
        "curl": """
curl -X POST "https://api.lishfind.com/api/v1/auth/register" \\
  -H "Content-Type: application/json" \\
  -d '{
    "email": "user@example.com",
    "password": "SecurePassword123!",
    "full_name": "John Doe",
    "role": "user"
  }'
        """,
        "python": """
import requests

response = requests.post(
    "https://api.lishfind.com/api/v1/auth/register",
    json={
        "email": "user@example.com",
        "password": "SecurePassword123!",
        "full_name": "John Doe",
        "role": "user"
    }
)
user = response.json()
print(f"User registered: {user['id']}")
        """,
        "javascript": """
const response = await fetch('https://api.lishfind.com/api/v1/auth/register', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    email: 'user@example.com',
    password: 'SecurePassword123!',
    full_name: 'John Doe',
    role: 'user'
  })
});
const user = await response.json();
console.log(`User registered: ${user.id}`);
        """
    },
    "login": {
        "description": "Login with email and password to get JWT tokens",
        "request": {
            "email": "user@example.com",
            "password": "SecurePassword123!"
        },
        "response": {
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "token_type": "bearer",
            "expires_in": 3600,
            "user": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "email": "user@example.com",
                "full_name": "John Doe",
                "role": "user"
            }
        }
    }
}

# Search Examples
SEARCH_EXAMPLES = {
    "natural_language_search": {
        "description": "Search using natural language query with AI intent extraction",
        "request_params": {
            "query": "best pizza restaurants near me",
            "latitude": 28.6139,
            "longitude": 77.2090,
            "limit": 10
        },
        "response": {
            "businesses": [
                {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "name": "Mario's Pizza Palace",
                    "category": "restaurant",
                    "rating": 4.5,
                    "review_count": 127,
                    "distance_km": 0.8,
                    "address": "123 Main St, New Delhi",
                    "relevance_score": 0.95,
                    "price_range": "moderate"
                }
            ],
            "search_intent": {
                "categories": ["restaurant"],
                "location_intent": {
                    "type": "near_me",
                    "radius_km": 5.0
                },
                "quality_preferences": {
                    "min_rating": 4.0
                }
            },
            "total_count": 25,
            "facets": {
                "categories": {"restaurant": 15, "cafe": 8, "bakery": 2},
                "price_ranges": {"budget": 5, "moderate": 15, "expensive": 5}
            }
        },
        "curl": """
curl -X GET "https://api.lishfind.com/api/v1/search/businesses" \\
  -G \\
  -d "query=best pizza restaurants near me" \\
  -d "latitude=28.6139" \\
  -d "longitude=77.2090" \\
  -d "limit=10"
        """
    },
    "filtered_search": {
        "description": "Search with specific filters and criteria",
        "request_params": {
            "category": "restaurant",
            "latitude": 28.6139,
            "longitude": 77.2090,
            "radius_km": 5.0,
            "min_rating": 4.0,
            "price_range": "moderate",
            "amenities": ["wifi", "parking"],
            "open_now": True,
            "sort_by": "rating",
            "limit": 20
        }
    }
}

# Recommendation Examples
RECOMMENDATION_EXAMPLES = {
    "personalized_recommendations": {
        "description": "Get personalized recommendations based on user preferences",
        "request_headers": {
            "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
        },
        "request_params": {
            "recommendation_type": "recommended_for_you",
            "latitude": 28.6139,
            "longitude": 77.2090,
            "limit": 10
        },
        "response": {
            "recommendations": [
                {
                    "business_id": "123e4567-e89b-12d3-a456-426614174000",
                    "business_name": "The Coffee Bean",
                    "category": "cafe",
                    "recommendation_score": 0.89,
                    "confidence_score": 0.92,
                    "strategy_used": "hybrid",
                    "reason": "Based on your love for cozy cafes with great coffee",
                    "explanation_factors": [
                        "Matches your preference for cafes",
                        "High rating (4.6★)",
                        "Similar to places you've visited"
                    ],
                    "rating": 4.6,
                    "distance_km": 1.2
                }
            ],
            "strategy_explanation": "Combines multiple recommendation approaches for best results",
            "personalization_applied": True,
            "diversity_score": 0.75
        },
        "python": """
import requests

headers = {"Authorization": "Bearer your-jwt-token"}
params = {
    "recommendation_type": "recommended_for_you",
    "latitude": 28.6139,
    "longitude": 77.2090,
    "limit": 10
}

response = requests.get(
    "https://api.lishfind.com/api/v1/recommendations/",
    headers=headers,
    params=params
)
recommendations = response.json()

for rec in recommendations["recommendations"]:
    print(f"{rec['business_name']}: {rec['reason']}")
        """
    },
    "similar_businesses": {
        "description": "Get businesses similar to a specific business",
        "request_params": {
            "business_id": "123e4567-e89b-12d3-a456-426614174000",
            "limit": 5
        }
    }
}

# Business Management Examples
BUSINESS_EXAMPLES = {
    "create_business": {
        "description": "Create a new business listing",
        "request_headers": {
            "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
        },
        "request": {
            "name": "Mario's Pizza Palace",
            "description": "Authentic Italian pizza made with fresh ingredients",
            "category": "restaurant",
            "phone": "+91-11-12345678",
            "email": "info@mariospizza.com",
            "website": "https://mariospizza.com",
            "address": "123 Main Street",
            "city": "New Delhi",
            "state": "Delhi",
            "postal_code": "110001",
            "latitude": 28.6139,
            "longitude": 77.2090,
            "price_range": "moderate",
            "amenities": ["wifi", "parking", "outdoor_seating"],
            "services": ["dine_in", "takeout", "delivery"],
            "opening_hours": {
                "monday": {"open": "11:00", "close": "22:00"},
                "tuesday": {"open": "11:00", "close": "22:00"},
                "wednesday": {"open": "11:00", "close": "22:00"},
                "thursday": {"open": "11:00", "close": "22:00"},
                "friday": {"open": "11:00", "close": "23:00"},
                "saturday": {"open": "11:00", "close": "23:00"},
                "sunday": {"open": "12:00", "close": "21:00"}
            }
        },
        "response": {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "name": "Mario's Pizza Palace",
            "status": "pending",
            "message": "Business created successfully. It will be reviewed before going live."
        }
    },
    "business_analytics": {
        "description": "Get comprehensive business analytics",
        "response": {
            "total_views": 1250,
            "total_clicks": 340,
            "total_reviews": 45,
            "average_rating": 4.5,
            "views_last_30_days": 450,
            "clicks_last_30_days": 120,
            "reviews_last_30_days": 8,
            "click_through_rate": 27.2,
            "search_rankings": {
                "restaurant": 5,
                "pizza restaurant new delhi": 3
            },
            "visitor_locations": {
                "New Delhi": 60,
                "Gurgaon": 25,
                "Noida": 15
            },
            "peak_hours": [12, 13, 17, 18, 19, 20]
        }
    }
}

# AI Service Examples
AI_EXAMPLES = {
    "extract_intent": {
        "description": "Extract structured intent from natural language query",
        "request": {
            "query": "I'm looking for a romantic dinner place with good wine, not too expensive, somewhere in South Delhi"
        },
        "response": {
            "intent": {
                "categories": ["restaurant"],
                "location_intent": {
                    "area": "South Delhi",
                    "type": "area_specific"
                },
                "budget_preferences": {
                    "price_range": "moderate",
                    "budget_conscious": True
                },
                "occasion_preferences": {
                    "mood": "romantic",
                    "dining_style": "fine_dining"
                },
                "feature_preferences": {
                    "amenities": ["wine_selection"],
                    "atmosphere": "romantic"
                }
            },
            "confidence_score": 0.92,
            "extracted_keywords": ["romantic", "dinner", "wine", "South Delhi"]
        }
    }
}

# Error Examples
ERROR_EXAMPLES = {
    "validation_error": {
        "status_code": 400,
        "response": {
            "detail": "Validation error in request data",
            "errors": [
                {
                    "field": "latitude",
                    "message": "Latitude must be between -90 and 90",
                    "invalid_value": 91.5
                },
                {
                    "field": "email",
                    "message": "Invalid email format",
                    "invalid_value": "not-an-email"
                }
            ]
        }
    },
    "authentication_error": {
        "status_code": 401,
        "response": {
            "detail": "Invalid or expired authentication token",
            "error_code": "INVALID_TOKEN",
            "suggestion": "Please login again to get a new token"
        }
    },
    "rate_limit_error": {
        "status_code": 429,
        "response": {
            "detail": "Rate limit exceeded",
            "retry_after": 3600,
            "limit": 1000,
            "window": "hour",
            "remaining": 0
        }
    }
}

# Complete workflow examples
WORKFLOW_EXAMPLES = {
    "user_search_workflow": {
        "description": "Complete user search and recommendation workflow",
        "steps": [
            {
                "step": 1,
                "action": "Search for businesses",
                "endpoint": "GET /search/businesses",
                "description": "User searches for 'best sushi restaurants'"
            },
            {
                "step": 2,
                "action": "Get recommendations based on search",
                "endpoint": "GET /recommendations/",
                "description": "Get personalized recommendations"
            },
            {
                "step": 3,
                "action": "Record user interaction",
                "endpoint": "POST /recommendations/interaction",
                "description": "Track when user clicks on a business"
            },
            {
                "step": 4,
                "action": "Get similar businesses",
                "endpoint": "GET /recommendations/similar/{business_id}",
                "description": "Show similar options to the selected business"
            }
        ]
    },
    "business_owner_workflow": {
        "description": "Business owner registration and management workflow",
        "steps": [
            {
                "step": 1,
                "action": "Register business account",
                "endpoint": "POST /auth/register",
                "description": "Create business owner account"
            },
            {
                "step": 2,
                "action": "Create business listing",
                "endpoint": "POST /business/create",
                "description": "Add business information"
            },
            {
                "step": 3,
                "action": "Upload business photos",
                "endpoint": "POST /business/photos/upload",
                "description": "Add photos to the listing"
            },
            {
                "step": 4,
                "action": "Monitor analytics",
                "endpoint": "GET /business/analytics",
                "description": "Track business performance"
            },
            {
                "step": 5,
                "action": "Respond to reviews",
                "endpoint": "POST /business/reviews/{review_id}/respond",
                "description": "Engage with customers"
            }
        ]
    }
}

def get_example_for_endpoint(endpoint_path: str, method: str) -> dict:
    """Get example data for a specific endpoint."""
    
    # Map endpoints to example data
    endpoint_examples = {
        ("POST", "/auth/register"): AUTH_EXAMPLES["register"],
        ("POST", "/auth/login"): AUTH_EXAMPLES["login"],
        ("GET", "/search/businesses"): SEARCH_EXAMPLES["natural_language_search"],
        ("GET", "/recommendations/"): RECOMMENDATION_EXAMPLES["personalized_recommendations"],
        ("POST", "/business/create"): BUSINESS_EXAMPLES["create_business"],
        ("GET", "/business/analytics"): BUSINESS_EXAMPLES["business_analytics"],
        ("POST", "/ai/extract-intent"): AI_EXAMPLES["extract_intent"],
    }
    
    return endpoint_examples.get((method, endpoint_path), {})


def get_code_samples_for_endpoint(endpoint_path: str, method: str, example_data: dict) -> list:
    """Generate code samples for an endpoint."""
    
    samples = []
    
    # Python example
    if "python" in example_data:
        samples.append({
            "lang": "Python",
            "source": example_data["python"]
        })
    
    # JavaScript example
    if "javascript" in example_data:
        samples.append({
            "lang": "JavaScript",
            "source": example_data["javascript"]
        })
    
    # cURL example
    if "curl" in example_data:
        samples.append({
            "lang": "Shell",
            "source": example_data["curl"]
        })
    
    return samples