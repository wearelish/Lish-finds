# LishFind API Developer Guide

## 📚 Table of Contents
- [Getting Started](#getting-started)
- [Authentication](#authentication)
- [API Endpoints](#api-endpoints)
- [Error Handling](#error-handling)
- [Rate Limiting](#rate-limiting)
- [Best Practices](#best-practices)
- [SDK Usage](#sdk-usage)
- [Examples](#examples)

## 🚀 Getting Started

### Base URLs
- **Production**: `https://api.lishfind.com/api/v1`
- **Staging**: `https://staging-api.lishfind.com/api/v1`
- **Development**: `http://localhost:8000/api/v1`

### Content Types
- **Request**: `application/json`
- **Response**: `application/json`

### Required Headers
```http
Content-Type: application/json
Authorization: Bearer <your-jwt-token>  # For protected endpoints
User-Agent: YourApp/1.0.0
```

## 🔐 Authentication

### JWT Token Authentication
LishFind API uses JWT (JSON Web Tokens) for authentication. Tokens are obtained through the login endpoint and must be included in the `Authorization` header for protected endpoints.

#### Getting a Token
```bash
curl -X POST "https://api.lishfind.com/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "your@email.com",
    "password": "your-password"
  }'
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "email": "your@email.com",
    "role": "user"
  }
}
```

#### Using the Token
```bash
curl -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  "https://api.lishfind.com/api/v1/recommendations/"
```

#### Token Refresh
```bash
curl -X POST "https://api.lishfind.com/api/v1/auth/refresh" \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "your-refresh-token"
  }'
```

### User Roles
- **`user`**: Regular users (search, recommendations)
- **`business`**: Business owners (manage listings, analytics)
- **`admin`**: System administrators (full access)

## 🎯 API Endpoints

### Search & Discovery

#### Search Businesses
```http
GET /search/businesses
```

**Parameters:**
- `query` (string): Natural language search query
- `latitude` (float): User latitude for location-based search
- `longitude` (float): User longitude for location-based search
- `category` (string): Filter by business category
- `min_rating` (float): Minimum rating filter (1.0-5.0)
- `max_distance_km` (float): Maximum distance in kilometers
- `price_range` (string): Price range filter (budget/moderate/expensive)
- `amenities` (array): Required amenities
- `open_now` (boolean): Only show businesses open now
- `sort_by` (string): Sort order (relevance/distance/rating/popularity)
- `limit` (int): Number of results (1-100, default: 10)
- `offset` (int): Pagination offset (default: 0)

**Example:**
```bash
curl "https://api.lishfind.com/api/v1/search/businesses" \
  -G \
  -d "query=best pizza restaurants" \
  -d "latitude=28.6139" \
  -d "longitude=77.2090" \
  -d "limit=10"
```

#### Extract Search Intent
```http
POST /ai/extract-intent
```

**Body:**
```json
{
  "query": "Looking for a cozy cafe with wifi near Central Park",
  "context": {
    "location": "New York",
    "time_of_day": "morning"
  }
}
```

### Recommendations

#### Get Personalized Recommendations
```http
GET /recommendations/
```

**Parameters:**
- `recommendation_type` (string): Type of recommendations
  - `recommended_for_you`
  - `trending_now`
  - `nearby_popular`
- `strategy` (string): Recommendation strategy
  - `hybrid` (default)
  - `collaborative_filtering`
  - `content_based`
  - `ai_powered`
- `latitude` (float): User latitude
- `longitude` (float): User longitude
- `limit` (int): Number of recommendations (1-50, default: 10)

**Headers:** `Authorization: Bearer <token>` (required)

#### Get Similar Businesses
```http
GET /recommendations/similar/{business_id}
```

**Parameters:**
- `business_id` (UUID): ID of the reference business
- `limit` (int): Number of similar businesses

### Business Management

#### Create Business Listing
```http
POST /business/create
```

**Headers:** `Authorization: Bearer <token>` (business role required)

**Body:**
```json
{
  "name": "Mario's Pizza Palace",
  "description": "Authentic Italian pizza with fresh ingredients",
  "category": "restaurant",
  "phone": "+1-555-0123",
  "email": "info@mariospizza.com",
  "address": "123 Main Street",
  "city": "New York",
  "state": "NY",
  "postal_code": "10001",
  "latitude": 40.7128,
  "longitude": -74.0060,
  "amenities": ["wifi", "parking", "outdoor_seating"],
  "opening_hours": {
    "monday": {"open": "11:00", "close": "22:00"},
    "tuesday": {"open": "11:00", "close": "22:00"}
  }
}
```

#### Get Business Analytics
```http
GET /business/analytics
```

**Headers:** `Authorization: Bearer <token>` (business owner required)

**Parameters:**
- `days` (int): Number of days for analytics (default: 30)

## ❌ Error Handling

### Error Response Format
```json
{
  "detail": "Human-readable error message",
  "error_code": "SPECIFIC_ERROR_CODE",
  "field_errors": [
    {
      "field": "email",
      "message": "Invalid email format",
      "code": "INVALID_FORMAT"
    }
  ],
  "request_id": "req_123456789"
}
```

### HTTP Status Codes
- `200` - Success
- `201` - Created
- `400` - Bad Request (validation errors)
- `401` - Unauthorized (authentication required)
- `403` - Forbidden (insufficient permissions)
- `404` - Not Found
- `422` - Unprocessable Entity (validation errors)
- `429` - Too Many Requests (rate limited)
- `500` - Internal Server Error

### Common Error Codes
- `INVALID_CREDENTIALS` - Login failed
- `TOKEN_EXPIRED` - JWT token has expired
- `VALIDATION_ERROR` - Request validation failed
- `RESOURCE_NOT_FOUND` - Requested resource doesn't exist
- `RATE_LIMIT_EXCEEDED` - Too many requests
- `INSUFFICIENT_PERMISSIONS` - User lacks required permissions

## ⏱️ Rate Limiting

### Limits
- **Authenticated users**: 1,000 requests per hour
- **Anonymous users**: 100 requests per hour
- **Business owners**: 2,000 requests per hour
- **Admin users**: 10,000 requests per hour

### Headers
Rate limit information is included in response headers:
```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1640995200
X-RateLimit-Retry-After: 3600
```

### Handling Rate Limits
```python
import requests
import time

def make_api_request(url, headers):
    response = requests.get(url, headers=headers)
    
    if response.status_code == 429:
        retry_after = int(response.headers.get('X-RateLimit-Retry-After', 60))
        print(f"Rate limited. Waiting {retry_after} seconds...")
        time.sleep(retry_after)
        return make_api_request(url, headers)
    
    return response
```

## 💡 Best Practices

### 1. Authentication
- Store JWT tokens securely (not in localStorage for web apps)
- Implement token refresh logic
- Handle authentication errors gracefully

### 2. Error Handling
- Always check response status codes
- Implement retry logic for transient errors
- Log errors for debugging

### 3. Performance
- Use appropriate pagination limits
- Cache responses when possible
- Include only necessary fields in requests

### 4. Location Data
- Always include user location for better search results
- Use user's current location when available
- Handle location permission denials gracefully

### 5. Rate Limiting
- Implement backoff strategies
- Monitor rate limit headers
- Cache responses to reduce API calls

## 📱 SDK Usage

### Python SDK
```python
from lishfind import LishFindClient

# Initialize client
client = LishFindClient(api_key="your-jwt-token")

# Search for businesses
businesses = client.search(
    query="best pizza restaurants",
    latitude=40.7128,
    longitude=-74.0060
)

# Get recommendations
recommendations = client.get_recommendations(
    recommendation_type="recommended_for_you",
    latitude=40.7128,
    longitude=-74.0060
)
```

### JavaScript SDK
```javascript
import { LishFindClient } from 'lishfind-js';

// Initialize client
const client = new LishFindClient({ apiKey: 'your-jwt-token' });

// Search for businesses
const businesses = await client.search({
  query: 'best pizza restaurants',
  latitude: 40.7128,
  longitude: -74.0060
});

// Get recommendations
const recommendations = await client.getRecommendations({
  recommendationType: 'recommended_for_you',
  latitude: 40.7128,
  longitude: -74.0060
});
```

## 📝 Examples

### Complete User Journey
```python
import requests

BASE_URL = "https://api.lishfind.com/api/v1"

# 1. User registration
register_response = requests.post(f"{BASE_URL}/auth/register", json={
    "email": "user@example.com",
    "password": "SecurePassword123",
    "full_name": "John Doe"
})

# 2. User login
login_response = requests.post(f"{BASE_URL}/auth/login", json={
    "email": "user@example.com",
    "password": "SecurePassword123"
})
token = login_response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# 3. Search for businesses
search_response = requests.get(f"{BASE_URL}/search/businesses", params={
    "query": "italian restaurants near me",
    "latitude": 40.7128,
    "longitude": -74.0060
})
businesses = search_response.json()

# 4. Get personalized recommendations
rec_response = requests.get(f"{BASE_URL}/recommendations/", 
    headers=headers,
    params={
        "latitude": 40.7128,
        "longitude": -74.0060
    }
)
recommendations = rec_response.json()

# 5. Record user interaction
requests.post(f"{BASE_URL}/recommendations/interaction",
    headers=headers,
    json={
        "business_id": businesses["businesses"][0]["id"],
        "interaction_type": "click"
    }
)
```

### Business Owner Journey
```python
# 1. Business owner registration
register_response = requests.post(f"{BASE_URL}/auth/register", json={
    "email": "owner@restaurant.com",
    "password": "SecurePassword123",
    "full_name": "Restaurant Owner",
    "role": "business"
})

# 2. Login and get token
login_response = requests.post(f"{BASE_URL}/auth/login", json={
    "email": "owner@restaurant.com",
    "password": "SecurePassword123"
})
token = login_response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# 3. Create business listing
business_response = requests.post(f"{BASE_URL}/business/create",
    headers=headers,
    json={
        "name": "Mario's Pizza Palace",
        "description": "Authentic Italian pizza",
        "category": "restaurant",
        "phone": "+1-555-0123",
        "email": "info@mariospizza.com",
        "address": "123 Main St",
        "city": "New York",
        "state": "NY",
        "postal_code": "10001",
        "latitude": 40.7128,
        "longitude": -74.0060
    }
)

# 4. Get business analytics
analytics_response = requests.get(f"{BASE_URL}/business/analytics", headers=headers)
analytics = analytics_response.json()

print(f"Total views: {analytics['total_views']}")
print(f"Click-through rate: {analytics['click_through_rate']}%")
```

## 🔍 Testing Your Integration

### Health Check
```bash
curl "https://api.lishfind.com/health"
```

### API Status
```bash
curl "https://api.lishfind.com/api/v1/health"
```

### Authentication Test
```bash
# This should return 401
curl "https://api.lishfind.com/api/v1/recommendations/"

# This should return recommendations
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "https://api.lishfind.com/api/v1/recommendations/"
```

## 📞 Support

- **Documentation**: https://docs.lishfind.com
- **API Status**: https://status.lishfind.com
- **Support Email**: api-support@lishfind.com
- **Community Forum**: https://community.lishfind.com

## 🔄 Changelog

### v1.0.0 (Current)
- Initial API release
- Search and recommendations
- Business management
- Authentication system
- Rate limiting and caching

---

For more detailed information, visit our [complete API documentation](https://api.lishfind.com/docs).