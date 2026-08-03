"""
Enhanced API documentation configuration and examples.

Provides comprehensive documentation with examples, usage patterns, and developer guides.
"""

from typing import Dict, Any, List
from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.openapi.utils import get_openapi

# API documentation metadata
API_METADATA = {
    "title": "LishFind API",
    "description": """
# LishFind API - AI-Powered Local Search Engine

Welcome to the LishFind API documentation. This comprehensive API provides AI-powered search capabilities 
for discovering local businesses and services.

## 🚀 Features

- **AI-Powered Search**: Natural language search with intent recognition
- **Smart Recommendations**: Personalized business recommendations using multiple AI strategies
- **Business Management**: Complete business listing management for owners
- **Advanced Ranking**: Configurable ranking algorithms for search results
- **Real-time Analytics**: Detailed analytics and insights for businesses
- **Caching Layer**: High-performance Redis caching for optimal response times

## 🔧 Getting Started

### Authentication

Most endpoints require authentication using JWT tokens. Include the token in the Authorization header:

```bash
Authorization: Bearer <your-jwt-token>
```

### Base URL

```
Production: https://api.lishfind.com/api/v1
Development: http://localhost:8000/api/v1
```

### Rate Limiting

API requests are rate-limited to ensure fair usage:
- **Authenticated users**: 1000 requests per hour
- **Anonymous users**: 100 requests per hour

## 📖 API Categories

### 🔐 Authentication
- User registration, login, and profile management
- JWT token generation and refresh
- Role-based access control

### 🔍 Search & Discovery
- Natural language search with AI intent extraction
- Advanced filtering and sorting options
- Geospatial search capabilities
- Search autocomplete and suggestions

### 🎯 Recommendations
- Personalized business recommendations
- Multiple recommendation strategies (collaborative, content-based, AI-powered)
- User preference learning and feedback

### 🏢 Business Management
- Business listing creation and management
- Analytics and insights dashboard
- Photo and media management
- Review management and responses

### 📊 Analytics & Ranking
- Business performance analytics
- Configurable ranking algorithms
- Competitive analysis and insights

### 💾 Cache Management
- Cache performance monitoring
- Selective cache invalidation
- Performance optimization tools

## 💡 Usage Examples

### Search for Businesses
```python
import requests

response = requests.get(
    "https://api.lishfind.com/api/v1/search/businesses",
    params={
        "query": "best pizza near me",
        "latitude": 28.6139,
        "longitude": 77.2090,
        "limit": 10
    }
)
businesses = response.json()
```

### Get Recommendations
```python
response = requests.get(
    "https://api.lishfind.com/api/v1/recommendations/",
    headers={"Authorization": f"Bearer {token}"},
    params={
        "recommendation_type": "recommended_for_you",
        "latitude": 28.6139,
        "longitude": 77.2090
    }
)
recommendations = response.json()
```

## 🛠️ SDKs and Libraries

- **Python SDK**: `pip install lishfind-python`
- **JavaScript SDK**: `npm install lishfind-js`
- **React Components**: `npm install lishfind-react`

## 📞 Support

- **Documentation**: https://docs.lishfind.com
- **Support Email**: api-support@lishfind.com
- **Developer Forum**: https://community.lishfind.com

## 📄 License

This API is licensed under the MIT License. See our [Terms of Service](https://lishfind.com/terms) for details.
    """,
    "version": "1.0.0",
    "terms_of_service": "https://lishfind.com/terms",
    "contact": {
        "name": "LishFind API Support",
        "url": "https://lishfind.com/support",
        "email": "api-support@lishfind.com",
    },
    "license_info": {
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
}

# Enhanced OpenAPI tags with detailed descriptions
API_TAGS_METADATA = [
    {
        "name": "Authentication",
        "description": """
## Authentication & Authorization

Manage user accounts, authentication, and access control.

### Key Features:
- JWT token-based authentication
- Role-based access control (User, Business Owner, Admin)
- Email verification and password reset
- Secure session management

### Authentication Flow:
1. Register a new account or login with existing credentials
2. Receive JWT access token and refresh token
3. Include access token in Authorization header for protected endpoints
4. Use refresh token to obtain new access tokens when expired

### User Roles:
- **User**: Regular users who can search and get recommendations
- **Business**: Business owners who can manage their listings
- **Admin**: System administrators with full access
        """,
        "externalDocs": {
            "description": "Authentication Guide",
            "url": "https://docs.lishfind.com/auth",
        },
    },
    {
        "name": "Search & Intent",
        "description": """
## Search & Intent Recognition

Intelligent search capabilities with AI-powered intent extraction.

### Search Types:
- **Natural Language Search**: "Find good sushi restaurants near me"
- **Filtered Search**: Search with specific filters and criteria
- **Geospatial Search**: Location-based search with distance filtering
- **Category Search**: Search within specific business categories

### Intent Recognition:
The AI system automatically extracts user intent from natural language queries:
- **Category Intent**: Restaurant, cafe, retail, etc.
- **Location Intent**: Near me, specific areas, distance preferences
- **Quality Intent**: Ratings, reviews, verification preferences
- **Time Intent**: Open now, specific hours, days of week
- **Budget Intent**: Price range preferences
- **Mood Intent**: Casual, formal, family-friendly, etc.

### Search Features:
- Real-time autocomplete suggestions
- Typo tolerance and spell correction
- Multi-language support
- Faceted search with aggregations
- Search result ranking and sorting
        """,
        "externalDocs": {
            "description": "Search API Guide",
            "url": "https://docs.lishfind.com/search",
        },
    },
    {
        "name": "AI Recommendations",
        "description": """
## AI-Powered Recommendations

Personalized business recommendations using advanced machine learning.

### Recommendation Strategies:
- **Collaborative Filtering**: Based on similar users' preferences
- **Content-Based**: Based on business characteristics and user history
- **Hybrid**: Combines multiple recommendation approaches
- **AI-Powered**: Uses advanced AI models for context-aware suggestions
- **Trending**: Popular and trending businesses
- **Location-Based**: Nearby popular businesses

### Recommendation Types:
- **Recommended for You**: Personalized recommendations based on user profile
- **Similar Businesses**: Businesses similar to one you're viewing
- **Trending Now**: Currently popular businesses in your area
- **Because You Liked**: Recommendations based on previous interactions

### Personalization Features:
- Learning from user interactions (views, clicks, reviews)
- Preference tracking and adjustment
- Context-aware recommendations (time, location, mood)
- Feedback integration for improved accuracy
        """,
        "externalDocs": {
            "description": "Recommendations Guide",
            "url": "https://docs.lishfind.com/recommendations",
        },
    },
    {
        "name": "Business Management",
        "description": """
## Business Listing Management

Complete business management tools for business owners.

### Business Profile Features:
- Complete business information management
- Photo and media upload
- Operating hours and contact information
- Amenities and services listing
- Social media integration

### Analytics & Insights:
- Performance metrics (views, clicks, engagement)
- Customer demographics and behavior
- Competitive analysis
- SEO optimization suggestions
- Growth recommendations

### Review Management:
- View and respond to customer reviews
- Review analytics and sentiment analysis
- Reputation management tools

### Verification & Quality:
- Business verification process
- Profile completeness scoring
- Quality improvement recommendations
        """,
        "externalDocs": {
            "description": "Business Management Guide",
            "url": "https://docs.lishfind.com/business",
        },
    },
    {
        "name": "Business Ranking",
        "description": """
## Intelligent Business Ranking

Advanced ranking algorithms for optimal search result ordering.

### Ranking Algorithms:
- **Balanced**: Equal weight to all ranking factors
- **Distance Priority**: Emphasizes proximity to user location
- **Quality Priority**: Focuses on ratings and reviews
- **Popularity Priority**: Emphasizes trending and popular businesses

### Ranking Factors:
- **Distance**: Proximity to user location
- **Rating**: Average customer rating
- **Reviews**: Number and quality of reviews
- **Completeness**: Business profile completeness
- **Popularity**: Engagement and trending metrics
- **Verification**: Business verification status

### Personalization:
- User preference integration
- Historical behavior analysis
- Context-aware adjustments
- Real-time optimization
        """,
        "externalDocs": {
            "description": "Ranking System Guide",
            "url": "https://docs.lishfind.com/ranking",
        },
    },
    {
        "name": "AI Service",
        "description": """
## AI Service & Providers

Core AI capabilities powering search and recommendations.

### AI Providers:
- **OpenAI**: GPT models for text generation and analysis
- **Google Gemini**: Advanced language understanding and generation
- **Multi-Provider Support**: Automatic fallback and load balancing

### AI Capabilities:
- Natural language understanding
- Intent extraction from search queries
- Personalized recommendation generation
- Business insight generation
- Content analysis and categorization

### AI Features:
- Real-time response generation
- Structured data extraction
- Multi-language support
- Context-aware processing
- Performance optimization
        """,
        "externalDocs": {
            "description": "AI Service Guide",
            "url": "https://docs.lishfind.com/ai",
        },
    },
    {
        "name": "Cache Management",
        "description": """
## Cache Management & Performance

Redis-based caching system for optimal API performance.

### Cache Features:
- **Multi-level Caching**: Different TTLs for different data types
- **Intelligent Invalidation**: Smart cache invalidation strategies
- **Compression**: Automatic compression for large cached values
- **Performance Monitoring**: Real-time cache performance metrics

### Cache Categories:
- **Search Results**: Search query results and facets
- **Business Data**: Business profiles and analytics
- **User Profiles**: User preferences and recommendation data
- **AI Responses**: AI-generated content and insights

### Management Tools:
- Cache statistics and health monitoring
- Selective cache invalidation
- Performance optimization
- Memory usage monitoring

*Note: Cache management endpoints are restricted to administrators.*
        """,
        "externalDocs": {
            "description": "Cache Management Guide",
            "url": "https://docs.lishfind.com/cache",
        },
    },
]

# Common response examples
COMMON_EXAMPLES = {
    "error_400": {
        "description": "Bad Request",
        "content": {
            "application/json": {
                "example": {
                    "detail": "Invalid request parameters",
                    "errors": [
                        {
                            "field": "latitude",
                            "message": "Latitude must be between -90 and 90"
                        }
                    ]
                }
            }
        }
    },
    "error_401": {
        "description": "Authentication Required",
        "content": {
            "application/json": {
                "example": {
                    "detail": "Authentication required",
                    "type": "authentication_required"
                }
            }
        }
    },
    "error_403": {
        "description": "Insufficient Permissions",
        "content": {
            "application/json": {
                "example": {
                    "detail": "Insufficient permissions for this action",
                    "required_role": "business",
                    "current_role": "user"
                }
            }
        }
    },
    "error_404": {
        "description": "Resource Not Found",
        "content": {
            "application/json": {
                "example": {
                    "detail": "Resource not found",
                    "resource_type": "business",
                    "resource_id": "123e4567-e89b-12d3-a456-426614174000"
                }
            }
        }
    },
    "error_429": {
        "description": "Rate Limit Exceeded",
        "content": {
            "application/json": {
                "example": {
                    "detail": "Rate limit exceeded",
                    "retry_after": 3600,
                    "limit_type": "hourly",
                    "remaining_requests": 0
                }
            }
        }
    },
    "error_500": {
        "description": "Internal Server Error",
        "content": {
            "application/json": {
                "example": {
                    "detail": "An unexpected error occurred",
                    "error_id": "err_123456789",
                    "support_contact": "api-support@lishfind.com"
                }
            }
        }
    }
}

def get_enhanced_openapi_schema(app: FastAPI) -> Dict[str, Any]:
    """Generate enhanced OpenAPI schema with comprehensive documentation."""
    
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=API_METADATA["title"],
        version=API_METADATA["version"],
        description=API_METADATA["description"],
        routes=app.routes,
        tags=API_TAGS_METADATA,
        servers=[
            {
                "url": "https://api.lishfind.com/api/v1",
                "description": "Production server"
            },
            {
                "url": "http://localhost:8000/api/v1",
                "description": "Development server"
            }
        ]
    )
    
    # Add additional metadata
    openapi_schema["info"].update({
        "termsOfService": API_METADATA["terms_of_service"],
        "contact": API_METADATA["contact"],
        "license": API_METADATA["license_info"],
        "x-logo": {
            "url": "https://lishfind.com/logo.png",
            "altText": "LishFind Logo"
        }
    })
    
    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "Bearer": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT token obtained from /auth/login endpoint"
        }
    }
    
    # Add common response schemas
    openapi_schema["components"]["responses"] = COMMON_EXAMPLES
    
    # Add example servers for different environments
    openapi_schema["servers"] = [
        {
            "url": "https://api.lishfind.com/api/v1",
            "description": "Production server"
        },
        {
            "url": "https://staging-api.lishfind.com/api/v1", 
            "description": "Staging server"
        },
        {
            "url": "http://localhost:8000/api/v1",
            "description": "Development server"
        }
    ]
    
    # Add API usage examples
    openapi_schema["x-code-samples"] = [
        {
            "lang": "Python",
            "source": """
import requests

# Search for businesses
response = requests.get(
    "https://api.lishfind.com/api/v1/search/businesses",
    params={
        "query": "best pizza near me",
        "latitude": 28.6139,
        "longitude": 77.2090
    }
)
businesses = response.json()
            """
        },
        {
            "lang": "JavaScript",
            "source": """
// Search for businesses
const response = await fetch(
    'https://api.lishfind.com/api/v1/search/businesses?' +
    new URLSearchParams({
        query: 'best pizza near me',
        latitude: 28.6139,
        longitude: 77.2090
    })
);
const businesses = await response.json();
            """
        },
        {
            "lang": "cURL",
            "source": """
# Search for businesses
curl -X GET "https://api.lishfind.com/api/v1/search/businesses" \\
  -G \\
  -d "query=best pizza near me" \\
  -d "latitude=28.6139" \\
  -d "longitude=77.2090"
            """
        }
    ]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


def setup_enhanced_docs(app: FastAPI) -> None:
    """Setup enhanced API documentation."""
    
    # Override the default OpenAPI schema
    app.openapi = lambda: get_enhanced_openapi_schema(app)
    
    # Custom docs endpoints with enhanced styling
    @app.get("/docs", include_in_schema=False)
    async def custom_swagger_ui_html():
        """Custom Swagger UI with enhanced styling."""
        return get_swagger_ui_html(
            openapi_url="/openapi.json",
            title=f"{API_METADATA['title']} - Interactive API Documentation",
            swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@3.52.5/swagger-ui-bundle.js",
            swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@3.52.5/swagger-ui.css",
            swagger_favicon_url="https://lishfind.com/favicon.ico",
        )
    
    @app.get("/redoc", include_in_schema=False)
    async def redoc_html():
        """Custom ReDoc documentation."""
        return get_redoc_html(
            openapi_url="/openapi.json",
            title=f"{API_METADATA['title']} - API Documentation",
            redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@2.0.0/bundles/redoc.standalone.js",
            redoc_favicon_url="https://lishfind.com/favicon.ico",
        )