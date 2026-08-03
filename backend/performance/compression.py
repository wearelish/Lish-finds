"""
Response compression and optimization for LishFind API.

Implements GZIP compression, response minification, and bandwidth optimization.
"""

import gzip
import json
import re
from typing import Any, Dict, List, Optional, Union
from io import BytesIO

import structlog
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from core.config import settings

logger = structlog.get_logger(__name__)

class CompressionMiddleware(BaseHTTPMiddleware):
    """Middleware for response compression and optimization."""
    
    def __init__(self, app, min_size: int = 1024):
        super().__init__(app)
        self.min_size = min_size
        self.compressible_types = {
            "application/json",
            "application/javascript",
            "text/html",
            "text/css",
            "text/plain",
            "text/xml",
            "application/xml",
            "image/svg+xml"
        }
    
    async def dispatch(self, request: Request, call_next):
        """Process request and compress response if appropriate."""
        
        # Check if client accepts gzip compression
        accept_encoding = request.headers.get("accept-encoding", "")
        supports_gzip = "gzip" in accept_encoding.lower()
        
        # Process request
        response = await call_next(request)
        
        # Skip compression for certain conditions
        if not supports_gzip:
            return response
        
        if not self._should_compress(response):
            return response
        
        # Compress response
        try:
            compressed_response = await self._compress_response(response)
            return compressed_response
        except Exception as e:
            logger.warning("Response compression failed", error=str(e))
            return response
    
    def _should_compress(self, response: Response) -> bool:
        """Determine if response should be compressed."""
        
        # Skip if already compressed
        if "content-encoding" in response.headers:
            return False
        
        # Skip if content-length header indicates small response
        content_length = response.headers.get("content-length")
        if content_length and int(content_length) < self.min_size:
            return False
        
        # Check content type
        content_type = response.headers.get("content-type", "").split(";")[0]
        return content_type in self.compressible_types
    
    async def _compress_response(self, response: Response) -> Response:
        """Compress response body using gzip."""
        
        # Get response body
        if hasattr(response, 'body') and response.body:
            body = response.body
        elif hasattr(response, 'content') and response.content:
            body = response.content
        else:
            return response
        
        # Skip if body is too small
        if len(body) < self.min_size:
            return response
        
        # Compress body
        compressed_body = gzip.compress(body)
        
        # Only use compressed version if it's actually smaller
        if len(compressed_body) >= len(body):
            return response
        
        # Create new response with compressed body
        new_response = Response(
            content=compressed_body,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.headers.get("content-type")
        )
        
        # Update headers
        new_response.headers["content-encoding"] = "gzip"
        new_response.headers["content-length"] = str(len(compressed_body))
        new_response.headers["vary"] = "Accept-Encoding"
        
        # Add compression ratio to response headers for debugging
        if settings.DEBUG:
            compression_ratio = len(body) / len(compressed_body)
            new_response.headers["x-compression-ratio"] = f"{compression_ratio:.2f}"
        
        logger.debug(
            "Response compressed",
            original_size=len(body),
            compressed_size=len(compressed_body),
            ratio=f"{(1 - len(compressed_body) / len(body)) * 100:.1f}%"
        )
        
        return new_response


class ResponseOptimizer:
    """Optimize API responses for better performance."""
    
    @staticmethod
    def minify_json(data: Any) -> str:
        """Minify JSON response by removing unnecessary whitespace."""
        return json.dumps(data, separators=(',', ':'), ensure_ascii=False)
    
    @staticmethod
    def optimize_business_data(business: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize business data for API responses."""
        # Remove empty or null fields to reduce payload size
        optimized = {}
        
        for key, value in business.items():
            if value is not None and value != "":
                if isinstance(value, str):
                    # Trim whitespace
                    value = value.strip()
                    if value:  # Only include non-empty strings
                        optimized[key] = value
                elif isinstance(value, list):
                    # Remove empty lists
                    if value:
                        optimized[key] = value
                elif isinstance(value, dict):
                    # Recursively optimize nested objects
                    nested_optimized = ResponseOptimizer.optimize_business_data(value)
                    if nested_optimized:  # Only include non-empty objects
                        optimized[key] = nested_optimized
                else:
                    optimized[key] = value
        
        return optimized
    
    @staticmethod
    def paginate_response(
        items: List[Any],
        page: int = 1,
        page_size: int = 20,
        max_page_size: int = 100
    ) -> Dict[str, Any]:
        """Create paginated response to reduce payload size."""
        
        # Enforce page size limits
        page_size = min(page_size, max_page_size)
        page = max(1, page)  # Ensure page is at least 1
        
        # Calculate pagination
        total_items = len(items)
        total_pages = (total_items + page_size - 1) // page_size
        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        
        # Get page items
        page_items = items[start_index:end_index]
        
        return {
            "items": page_items,
            "pagination": {
                "current_page": page,
                "page_size": page_size,
                "total_items": total_items,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_previous": page > 1,
                "next_page": page + 1 if page < total_pages else None,
                "previous_page": page - 1 if page > 1 else None
            }
        }
    
    @staticmethod
    def create_lightweight_business_summary(business: Dict[str, Any]) -> Dict[str, Any]:
        """Create lightweight business summary for list responses."""
        # Include only essential fields for list views
        essential_fields = [
            'id', 'name', 'category', 'rating', 'review_count',
            'latitude', 'longitude', 'address', 'phone', 'website',
            'price_level', 'is_open', 'distance'
        ]
        
        summary = {}
        for field in essential_fields:
            if field in business and business[field] is not None:
                summary[field] = business[field]
        
        return summary
    
    @staticmethod
    def optimize_search_results(
        results: List[Dict[str, Any]],
        include_full_details: bool = False
    ) -> List[Dict[str, Any]]:
        """Optimize search results for faster transmission."""
        
        if include_full_details:
            # Full details requested - optimize individual items
            return [
                ResponseOptimizer.optimize_business_data(business)
                for business in results
            ]
        else:
            # Light mode - return summaries only
            return [
                ResponseOptimizer.create_lightweight_business_summary(business)
                for business in results
            ]


class BandwidthOptimizer:
    """Optimize bandwidth usage for mobile and slow connections."""
    
    @staticmethod
    def detect_connection_type(request: Request) -> str:
        """Detect connection type from request headers."""
        
        # Check for mobile user agents
        user_agent = request.headers.get("user-agent", "").lower()
        mobile_keywords = ["mobile", "android", "iphone", "ipad", "tablet"]
        
        if any(keyword in user_agent for keyword in mobile_keywords):
            return "mobile"
        
        # Check for save-data header (data saver mode)
        if request.headers.get("save-data") == "on":
            return "slow"
        
        # Check for connection type hints
        network_info = request.headers.get("downlink")
        if network_info:
            try:
                downlink = float(network_info)
                if downlink < 1.0:  # Less than 1 Mbps
                    return "slow"
                elif downlink < 5.0:  # Less than 5 Mbps
                    return "medium"
            except ValueError:
                pass
        
        return "fast"
    
    @staticmethod
    def get_optimized_response_config(connection_type: str) -> Dict[str, Any]:
        """Get response optimization config based on connection type."""
        
        configs = {
            "slow": {
                "max_results": 10,
                "include_images": False,
                "include_reviews": False,
                "compression_level": 9,  # Maximum compression
                "fields_to_exclude": [
                    "description", "detailed_categories", "attributes",
                    "photos", "reviews", "hours_detailed"
                ]
            },
            "medium": {
                "max_results": 20,
                "include_images": False,
                "include_reviews": True,
                "compression_level": 6,
                "fields_to_exclude": [
                    "photos", "detailed_categories"
                ]
            },
            "mobile": {
                "max_results": 15,
                "include_images": True,
                "include_reviews": True,
                "compression_level": 6,
                "fields_to_exclude": [
                    "hours_detailed"
                ]
            },
            "fast": {
                "max_results": 50,
                "include_images": True,
                "include_reviews": True,
                "compression_level": 3,
                "fields_to_exclude": []
            }
        }
        
        return configs.get(connection_type, configs["fast"])
    
    @staticmethod
    def optimize_for_connection(
        data: Dict[str, Any],
        connection_type: str
    ) -> Dict[str, Any]:
        """Optimize response data based on connection type."""
        
        config = BandwidthOptimizer.get_optimized_response_config(connection_type)
        
        # Limit results if it's a list response
        if "results" in data and isinstance(data["results"], list):
            max_results = config["max_results"]
            if len(data["results"]) > max_results:
                data["results"] = data["results"][:max_results]
                data["truncated"] = True
                data["total_available"] = len(data["results"])
        
        # Remove specified fields
        fields_to_exclude = config["fields_to_exclude"]
        if fields_to_exclude:
            data = BandwidthOptimizer._remove_fields(data, fields_to_exclude)
        
        return data
    
    @staticmethod
    def _remove_fields(data: Any, fields_to_exclude: List[str]) -> Any:
        """Recursively remove specified fields from data."""
        
        if isinstance(data, dict):
            return {
                key: BandwidthOptimizer._remove_fields(value, fields_to_exclude)
                for key, value in data.items()
                if key not in fields_to_exclude
            }
        elif isinstance(data, list):
            return [
                BandwidthOptimizer._remove_fields(item, fields_to_exclude)
                for item in data
            ]
        else:
            return data


# Utility functions for FastAPI responses
def create_optimized_json_response(
    data: Any,
    request: Request,
    status_code: int = 200
) -> JSONResponse:
    """Create optimized JSON response with compression and optimization."""
    
    # Detect connection type
    connection_type = BandwidthOptimizer.detect_connection_type(request)
    
    # Optimize data based on connection
    if isinstance(data, dict):
        optimized_data = BandwidthOptimizer.optimize_for_connection(data, connection_type)
    else:
        optimized_data = data
    
    # Create minified JSON
    content = ResponseOptimizer.minify_json(optimized_data)
    
    # Create response
    response = JSONResponse(
        content=optimized_data,
        status_code=status_code
    )
    
    # Add optimization headers
    response.headers["x-connection-type"] = connection_type
    response.headers["x-optimized"] = "true"
    
    return response


def create_paginated_response(
    items: List[Any],
    request: Request,
    page: int = 1,
    page_size: int = 20
) -> JSONResponse:
    """Create paginated and optimized response."""
    
    # Optimize items first
    connection_type = BandwidthOptimizer.detect_connection_type(request)
    config = BandwidthOptimizer.get_optimized_response_config(connection_type)
    
    # Adjust page size based on connection
    adjusted_page_size = min(page_size, config["max_results"])
    
    # Create paginated response
    paginated_data = ResponseOptimizer.paginate_response(
        items, page, adjusted_page_size
    )
    
    # Optimize the response
    optimized_data = BandwidthOptimizer.optimize_for_connection(
        paginated_data, connection_type
    )
    
    return create_optimized_json_response(optimized_data, request)


# Compression utilities
def compress_string(data: str, level: int = 6) -> bytes:
    """Compress string data using gzip."""
    return gzip.compress(data.encode('utf-8'), compresslevel=level)


def decompress_string(compressed_data: bytes) -> str:
    """Decompress gzip compressed string data."""
    return gzip.decompress(compressed_data).decode('utf-8')


def get_compression_ratio(original: bytes, compressed: bytes) -> float:
    """Calculate compression ratio."""
    if len(original) == 0:
        return 1.0
    return len(compressed) / len(original)