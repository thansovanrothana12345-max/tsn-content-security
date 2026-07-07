from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
import os
import logging
import logging.handlers
from backend.config import Config
from backend.database import init_db
from backend.routes import auth, cases, originals, evidence, reports, verification, ai_fingerprint, assets_router, scans_router, health, detection
from backend.middleware.rate_limiter import RateLimiterMiddleware

app = FastAPI(
    title="Copyright Center API",
    description="Enterprise backend services for copyright checking and case tracking",
    version="1.0.0"
)

# Enable CORS restricted to localhost/loopback origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RateLimiterMiddleware)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORAGE_DIR = os.path.join(PROJECT_ROOT, Config.STORAGE_DIR)
STATIC_DIR = os.path.join(PROJECT_ROOT, "frontend", "static")

# Create directories if they do not exist
os.makedirs(STORAGE_DIR, exist_ok=True)
os.makedirs(os.path.join(STORAGE_DIR, "originals"), exist_ok=True)
os.makedirs(os.path.join(STORAGE_DIR, "evidence"), exist_ok=True)
os.makedirs(os.path.join(STORAGE_DIR, "temp"), exist_ok=True)
os.makedirs(os.path.join(STORAGE_DIR, "logs"), exist_ok=True)

# Configure Production Rotating File Logging
log_file = os.path.join(STORAGE_DIR, "logs", "app.log")
log_handler = logging.handlers.RotatingFileHandler(
    log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
)
formatter = logging.Formatter("[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] - %(message)s")
log_handler.setFormatter(formatter)

# Hook loggers to file handler
root_logger = logging.getLogger()
root_logger.setLevel(logging.WARNING)
root_logger.addHandler(log_handler)

logger = logging.getLogger("backend")
logger.setLevel(logging.INFO)
logger.addHandler(log_handler)

logger.info("Application starting up in production security mode...")

# Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.googleapis.com https://fonts.gstatic.com; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.googleapis.com https://fonts.gstatic.com; "
        "font-src 'self' data: https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.googleapis.com https://fonts.gstatic.com; "
        "img-src 'self' data: blob: https: https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.googleapis.com https://fonts.gstatic.com; "
        "connect-src 'self' http://127.0.0.1:* http://localhost:* ws://127.0.0.1:* ws://localhost:* https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.googleapis.com https://fonts.gstatic.com; "
        "frame-src 'self';"
    )
    return response

# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    from backend.services.logger import log_api_error
    log_api_error(request.url.path, str(exc), 500)
    logger.exception(f"Unhandled exception during request to {request.url.path}: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

# Register versioned routers
app.include_router(auth.router)
app.include_router(auth.router_v2)
app.include_router(cases.router)
app.include_router(originals.router)
app.include_router(evidence.router)
app.include_router(evidence.router_jobs)
app.include_router(reports.router)
app.include_router(verification.router)
app.include_router(ai_fingerprint.router)
app.include_router(assets_router.router)
app.include_router(scans_router.router)
app.include_router(health.router)
app.include_router(detection.router)

# Mount Static Folders
app.mount("/storage", StaticFiles(directory=STORAGE_DIR), name="storage")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
# Database initialization on app startup
@app.on_event("startup")
def on_startup():
    Config.validate_config()
    init_db()

# Serve frontend landing page
@app.get("/")
def serve_index():
    index_path = os.path.join(STATIC_DIR, "index.html")

    print("=" * 60)
    print("STATIC_DIR :", STATIC_DIR)
    print("INDEX PATH :", index_path)
    print("EXISTS     :", os.path.exists(index_path))
    print("=" * 60)

    if os.path.exists(index_path):
        return FileResponse(index_path)

    return {"error": "index.html not found"}
