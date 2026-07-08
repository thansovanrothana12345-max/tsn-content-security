import time
import os
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from fastapi import Request
from backend.config import Config

logger = logging.getLogger("tsn.rate_limiter")

class RateLimiterMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.requests = {} # map client_ip -> dict of category -> list of timestamps
        
    async def dispatch(self, request: Request, call_next):
        # Allow disabling rate limiting via config
        if not getattr(Config, "RATE_LIMIT_ENABLED", True):
            return await call_next(request)
            
        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()
        
        path = request.url.path
        
        if "/api/v1/auth" in path:
            category = "auth"
            limit = getattr(Config, "RATE_LIMIT_AUTH_COUNT", 10)
            window = getattr(Config, "RATE_LIMIT_AUTH_WINDOW", 60)
        elif "/api/v1/scans" in path or "/api/v1/scan" in path:
            category = "scans"
            limit = getattr(Config, "RATE_LIMIT_SCANS_COUNT", 120)  # Polling friendly limit
            window = getattr(Config, "RATE_LIMIT_SCANS_WINDOW", 60)
        else:
            category = "general"
            limit = getattr(Config, "RATE_LIMIT_GENERAL_COUNT", 120)
            window = getattr(Config, "RATE_LIMIT_GENERAL_WINDOW", 60)
            
        # Initialize structure for client_ip if not exists
        if client_ip not in self.requests:
            self.requests[client_ip] = {}
            
        if category not in self.requests[client_ip]:
            self.requests[client_ip][category] = []
            
        timestamps = self.requests[client_ip][category]
        
        # Filter out timestamps older than the sliding window
        self.requests[client_ip][category] = [t for t in timestamps if current_time - t < window]
        
        if len(self.requests[client_ip][category]) >= limit:
            logger.warning(f"Rate limit exceeded for client {client_ip} on category {category} for path {path}.")
            
            # Record security log entry
            try:
                log_dir = os.path.join(Config.PROJECT_ROOT, "storage", "logs")
                os.makedirs(log_dir, exist_ok=True)
                log_file = os.path.join(log_dir, "security_events.log")
                with open(log_file, "a") as f:
                    f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [RATE_LIMIT_EXCEEDED] Client {client_ip} on {path}\n")
            except Exception:
                pass
                
            return JSONResponse(
                status_code=429,
                content={"error": "RATE_LIMIT_EXCEEDED", "message": "Too many requests. Please try again later."}
            )
            
        self.requests[client_ip][category].append(current_time)
        return await call_next(request)
