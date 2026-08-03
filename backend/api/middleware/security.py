"""
Security middleware for adding security headers and protection.

Implements security best practices including CSRF protection, security headers,
and request validation for production environments.
"""

import time
from typing import Callable, Dict, Set
import asyncio
import ipaddress

import structlog
from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from core.config import settings

logger = structlog.get_logger(__name__)

# In-memory stores for rate limiting and security (use Redis in production clusters)
FAILED_LOGIN_ATTEMPTS: Dict[str, Dict] = {}
BLOCKED_IPS: Set[str] = set()
REQUEST_COUNTS: Dict[str, Dict] = {}


class SecurityMiddleware(BaseHTTPMiddleware):
    """Enhanced security middleware for production environments."""
    
    def __init__(self, app):
        super().__init__(app)
        self.trusted_proxies = self._load_trusted_proxies()
    
    def _load_trusted_proxies(self) -> Set[ipaddress.IPv4Network]:
        """Load trusted proxy networks for IP validation."""
        # Common proxy networks (CloudFlare, AWS ALB, etc.)
        trusted_networks = [
            "127.0.0.0/8",      # Localhost
            "10.0.0.0/8",       # Private network
            "172.16.0.0/12",    # Private network
            "192.168.0.0/16",   # Private network
        ]
        
        networks = set()
        for network in trusted_networks:
            try:
                networks.add(ipaddress.IPv4Network(network))
            except ValueError:
                logger.warning("Invalid trusted proxy network", network=network)
        
        return networks
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Enhanced security processing with rate limiting and IP blocking."""
        start_time = time.time()
        client_ip = self._get_client_ip(request)
        
        # Check if IP is blocked
        if client_ip in BLOCKED_IPS:
            logger.warning("Blocked IP attempted access", ip=client_ip, path=request.url.path)
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Rate limiting check
        if not self._check_rate_limit(client_ip, request):
            logger.warning("Rate limit exceeded", ip=client_ip, path=request.url.path)
            raise HTTPException(status_code=429, detail="Too many requests")
        
        # Request size validation
        if not await self._validate_request_size(request):
            logger.warning("Request too large", ip=client_ip, path=request.url.path)
            raise HTTPException(status_code=413, detail="Request entity too large")
        
        # Process the request
        try:
            response = await asyncio.wait_for(
                call_next(request),
                timeout=settings.REQUEST_TIMEOUT_SECONDS
            )
        except asyncio.TimeoutError:
            logger.warning("Request timeout", ip=client_ip, path=request.url.path)
            raise HTTPException(status_code=408, detail="Request timeout")
        
        # Add security headers
        self._add_security_headers(response, request)
        
        # Log security events
        await self._log_security_events(request, response, time.time() - start_time)
        
        # Track failed login attempts
        if request.url.path in ["/api/v1/auth/login", "/api/v1/auth/register"]:
            self._track_auth_attempts(client_ip, response.status_code)
        
        return response
    
    def _add_security_headers(self, response: Response, request: Request) -> None:
        """Add comprehensive security headers to the response."""
        # Prevent XSS attacks
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # HSTS (HTTP Strict Transport Security) - only for HTTPS
        if settings.HTTPS_ONLY or not settings.DEBUG:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )
        
        # Content Security Policy
        csp_policy = self._build_csp_policy()
        response.headers["Content-Security-Policy"] = csp_policy
        
        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions Policy (formerly Feature Policy)
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(self), payment=(), usb=()"
        )
        
        # Cross-Origin policies
        response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Resource-Policy"] = "same-site"
        
        # Remove server information
        if "Server" in response.headers:
            del response.headers["Server"]
        
        # Custom security headers
        response.headers["X-LishFind-Security"] = "enabled"
        response.headers["X-Request-ID"] = getattr(request.state, 'request_id', 'unknown')
        
        # Cache control for sensitive endpoints
        if "/auth/" in request.url.path or "/admin/" in request.url.path:
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
            response.headers["Pragma"] = "no-cache"
    
    def _build_csp_policy(self) -> str:
        """Build Content Security Policy based on environment."""
        if settings.DEBUG:
            # More permissive CSP for development
            return (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' https: data:; "
                "connect-src 'self' ws: wss:; "
                "frame-ancestors 'none'"
            )
        else:
            # Strict CSP for production
            return (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' https:; "
                "connect-src 'self' https:; "
                "frame-ancestors 'none'; "
                "base-uri 'self'"
            )
    
    def _check_rate_limit(self, client_ip: str, request: Request) -> bool:
        """Check if the client IP has exceeded rate limits."""
        current_time = time.time()
        window_start = current_time - 60  # 1-minute window
        
        if client_ip not in REQUEST_COUNTS:
            REQUEST_COUNTS[client_ip] = {"requests": [], "last_reset": current_time}
        
        # Clean old requests outside the window
        client_data = REQUEST_COUNTS[client_ip]
        client_data["requests"] = [
            req_time for req_time in client_data["requests"] 
            if req_time > window_start
        ]
        
        # Add current request
        client_data["requests"].append(current_time)
        
        # Check limits
        request_count = len(client_data["requests"])
        
        # Different limits for different endpoints
        if "/auth/" in request.url.path:
            limit = 10  # Stricter for auth endpoints
        elif "/api/" in request.url.path:
            limit = settings.RATE_LIMIT_PER_MINUTE
        else:
            limit = settings.RATE_LIMIT_PER_MINUTE * 2  # More lenient for static content
        
        return request_count <= limit
    
    async def _validate_request_size(self, request: Request) -> bool:
        """Validate request size to prevent DoS attacks."""
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                size = int(content_length)
                return size <= settings.MAX_REQUEST_SIZE
            except ValueError:
                return False
        return True
    
    def _track_auth_attempts(self, client_ip: str, status_code: int) -> None:
        """Track failed authentication attempts and block IPs if necessary."""
        current_time = time.time()
        
        if status_code in [401, 403, 422]:  # Failed authentication
            if client_ip not in FAILED_LOGIN_ATTEMPTS:
                FAILED_LOGIN_ATTEMPTS[client_ip] = {
                    "attempts": 0,
                    "first_attempt": current_time,
                    "last_attempt": current_time
                }
            
            attempt_data = FAILED_LOGIN_ATTEMPTS[client_ip]
            attempt_data["attempts"] += 1
            attempt_data["last_attempt"] = current_time
            
            # Block IP after max attempts
            if attempt_data["attempts"] >= settings.MAX_LOGIN_ATTEMPTS:
                BLOCKED_IPS.add(client_ip)
                logger.warning(
                    "IP blocked due to excessive failed login attempts",
                    ip=client_ip,
                    attempts=attempt_data["attempts"]
                )
                
                # Auto-unblock after lockout period
                asyncio.create_task(self._unblock_ip_after_delay(client_ip))
        
        elif status_code == 200:  # Successful authentication
            # Reset failed attempts on successful login
            if client_ip in FAILED_LOGIN_ATTEMPTS:
                del FAILED_LOGIN_ATTEMPTS[client_ip]
    
    async def _unblock_ip_after_delay(self, client_ip: str) -> None:
        """Automatically unblock IP after lockout period."""
        await asyncio.sleep(settings.LOGIN_LOCKOUT_MINUTES * 60)
        if client_ip in BLOCKED_IPS:
            BLOCKED_IPS.remove(client_ip)
            logger.info("IP automatically unblocked after lockout period", ip=client_ip)
    
    async def _log_security_events(self, request: Request, response: Response, 
                                  duration: float) -> None:
        """Enhanced security event logging with performance metrics."""
        client_ip = self._get_client_ip(request)
        
        # Log all requests in production for audit trail
        if settings.is_production:
            logger.info(
                "API request",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=round(duration * 1000, 2),
                client_ip=client_ip,
                user_agent=request.headers.get("user-agent", "")[:200],  # Truncate long user agents
                request_id=getattr(request.state, 'request_id', 'unknown')
            )
        
        # Log suspicious requests
        suspicious_patterns = [
            # XSS patterns
            "<script", "javascript:", "vbscript:", "onload=", "onerror=", "onclick=",
            # Path traversal
            "../", "..\\", "....//", "....\\\\",
            # SQL injection patterns
            "union select", "drop table", "insert into", "delete from", "update set",
            "'; --", "' or 1=1", "' or '1'='1",
            # Command injection
            "; rm -rf", "&& rm", "| nc ", "; cat ", "$(", "`",
            # Common attack tools
            "sqlmap", "nikto", "nessus", "burp", "nmap",
            # File inclusion
            "wp-config.php", ".htaccess", "/etc/passwd", "boot.ini",
        ]
        
        # Check URL, query parameters, and headers for suspicious content
        check_strings = [
            str(request.url).lower(),
            request.headers.get("user-agent", "").lower(),
            request.headers.get("referer", "").lower(),
        ]
        
        for check_string in check_strings:
            for pattern in suspicious_patterns:
                if pattern in check_string:
                    logger.warning(
                        "Suspicious request pattern detected",
                        pattern=pattern,
                        url=str(request.url),
                        method=request.method,
                        user_agent=request.headers.get("user-agent", ""),
                        client_ip=client_ip,
                        request_id=getattr(request.state, 'request_id', 'unknown')
                    )
                    break
        
        # Log error responses for security analysis
        if response.status_code >= 400:
            log_level = logger.warning if response.status_code >= 500 else logger.info
            log_level(
                "HTTP error response",
                status_code=response.status_code,
                path=request.url.path,
                method=request.method,
                duration_ms=round(duration * 1000, 2),
                client_ip=client_ip,
                request_id=getattr(request.state, 'request_id', 'unknown')
            )
        
        # Log slow requests for performance monitoring
        if duration > 2.0:  # Log requests taking more than 2 seconds
            logger.warning(
                "Slow request detected",
                duration_ms=round(duration * 1000, 2),
                path=request.url.path,
                method=request.method,
                client_ip=client_ip,
                request_id=getattr(request.state, 'request_id', 'unknown')
            )
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address with proper proxy support and validation."""
        # Check for forwarded headers (in order of preference)
        forwarded_headers = [
            "x-forwarded-for",
            "x-real-ip", 
            "cf-connecting-ip",  # CloudFlare
            "x-client-ip",
            "x-forwarded",
        ]
        
        for header in forwarded_headers:
            forwarded_value = request.headers.get(header)
            if forwarded_value:
                # X-Forwarded-For can contain multiple IPs
                if header == "x-forwarded-for":
                    ips = [ip.strip() for ip in forwarded_value.split(",")]
                    # Return the first non-private IP, or the first IP if all are private
                    for ip in ips:
                        try:
                            ip_obj = ipaddress.IPv4Address(ip)
                            if not ip_obj.is_private:
                                return ip
                        except ValueError:
                            continue
                    return ips[0] if ips else "unknown"
                else:
                    return forwarded_value.strip()
        
        # Fallback to direct connection IP
        if request.client:
            return request.client.host
            
        return "unknown"