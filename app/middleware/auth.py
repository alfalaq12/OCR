from fastapi import Request, HTTPException, Security
from fastapi.security import APIKeyHeader
from starlette.middleware.base import BaseHTTPMiddleware
from collections import defaultdict
import time
from app.config import settings

# API Key header
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    """Verify API key from header"""
    if not settings.API_KEYS_ENABLED:
        return "anonymous"
    
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "API key required",
                "error_code": "AUTH_MISSING_KEY",
                "details": "Please provide X-API-Key header"
            }
        )
    
    # Check static keys from .env
    if api_key in settings.API_KEYS:
        return api_key
    
    # Check dynamic keys from database
    from app.services.db_service import db_service
    key_info = db_service.validate_api_key(api_key)
    if key_info:
        return api_key
    
    raise HTTPException(
        status_code=403,
        detail={
            "error": "Invalid API key",
            "error_code": "AUTH_INVALID_KEY",
            "details": "The provided API key is not valid"
        }
    )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware"""
    
    def __init__(self, app, requests_per_minute: int = 30):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests = defaultdict(list)
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for docs and health endpoints
        if request.url.path in ["/", "/health", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)
        
        # Get client identifier (API key or IP)
        api_key = request.headers.get("X-API-Key")
        client_id = api_key if api_key else request.client.host
        
        # Check rate limit
        now = time.time()
        minute_ago = now - 60
        
        # Clean old requests
        self.requests[client_id] = [
            req_time for req_time in self.requests[client_id]
            if req_time > minute_ago
        ]
        
        # Check if over limit
        if len(self.requests[client_id]) >= self.requests_per_minute:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "error": "Rate limit exceeded",
                    "error_code": "RATE_LIMIT_EXCEEDED",
                    "details": f"Maximum {self.requests_per_minute} requests per minute"
                }
            )
        
        # Record request
        self.requests[client_id].append(now)
        
        # Add rate limit headers
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(
            self.requests_per_minute - len(self.requests[client_id])
        )
        
        return response
