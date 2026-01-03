"""
MahaSeWA Backend - Main FastAPI Application
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager
import logging
import os

from app.config import settings
from app.middleware.rate_limit import limiter, rate_limit_exceeded_handler
from app.api.v1 import (
    auth,
    societies,
    members,
    providers,
    subscriptions,
    consultations,
    bookings,
    compliance,
    content,
    admin,
    lms,
    analytics,
    publication_ads,
    uploads,
    invoices,
    payments,
    geocoding
)
from app.api.v1 import files

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events
    """
    # Startup
    logger.info(f"Starting {settings.APP_NAME}...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    
    # Initialize database connection pool
    # Initialize Redis connection
    # Load ML models if any
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    # Close database connections
    # Close Redis connections


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    description="Housing Society Management & Service Provider Platform API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    lifespan=lifespan,
    debug=settings.DEBUG
)

# Add rate limiter to app state
app.state.limiter = limiter
# Add custom rate limit exception handler
from slowapi.errors import RateLimitExceeded
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)


# ============================================================================
# MIDDLEWARE
# ============================================================================

# CORS Middleware - Allow frontend to connect
# CRITICAL: When allow_credentials=True, must use allow_origin_regex OR specific origins
# FastAPI CORS middleware with credentials requires either:
# 1. Specific origins in allow_origins list, OR
# 2. allow_origin_regex pattern (works with credentials in FastAPI 0.100+)
# Solution: Use regex for all *.vercel.app domains + specific origins
import json

# Parse CORS_ORIGINS from environment (could be JSON string or list)
cors_origins_raw = settings.CORS_ORIGINS
if isinstance(cors_origins_raw, str):
    try:
        cors_origins_raw = json.loads(cors_origins_raw)
    except json.JSONDecodeError:
        # If not JSON, treat as comma-separated string
        cors_origins_raw = [origin.strip() for origin in cors_origins_raw.split(",")]

# Separate specific origins from wildcards
specific_origins = []
for origin in cors_origins_raw:
    if "*" not in origin:
        specific_origins.append(origin)

# Default origins if none provided
if not specific_origins:
    specific_origins = [
        "https://mahasewa.vercel.app",
        "https://mahasewa-frontend.vercel.app",
        "https://mahasewa.org",
        "https://www.mahasewa.org",
        "http://localhost:3000",
        "http://localhost:8080",
    ]

# Regex pattern for all Vercel deployment URLs (supports any subdomain.vercel.app)
vercel_regex = r"https://.*\.vercel\.app"

logger.info(f"CORS configured for specific origins: {specific_origins}")
logger.info(f"CORS regex pattern for Vercel: {vercel_regex}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=specific_origins,  # Specific origins
    allow_origin_regex=vercel_regex,  # Regex for all *.vercel.app domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Trusted Host Middleware (security)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS
)


# ============================================================================
# ROUTES
# ============================================================================

# Health check endpoint
@app.get("/")
async def root():
    """
    Root endpoint - API status
    """
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring
    """
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT
    }


# Include API routers
app.include_router(
    auth.router,
    prefix=f"{settings.API_V1_PREFIX}/auth",
    tags=["Authentication"]
)

app.include_router(
    societies.router,
    prefix=f"{settings.API_V1_PREFIX}/societies",
    tags=["Societies"]
)

app.include_router(
    members.router,
    prefix=f"{settings.API_V1_PREFIX}/members",
    tags=["Members"]
)

app.include_router(
    providers.router,
    prefix=f"{settings.API_V1_PREFIX}/providers",
    tags=["Service Providers"]
)

app.include_router(
    subscriptions.router,
    prefix=f"{settings.API_V1_PREFIX}/subscriptions",
    tags=["Vendor Subscriptions"]
)

app.include_router(
    consultations.router,
    prefix=f"{settings.API_V1_PREFIX}/consultations",
    tags=["Consultations"]
)

app.include_router(
    bookings.router,
    prefix=f"{settings.API_V1_PREFIX}/bookings",
    tags=["Service Bookings"]
)

app.include_router(
    compliance.router,
    prefix=f"{settings.API_V1_PREFIX}/compliance",
    tags=["Compliance"]
)

app.include_router(
    content.router,
    prefix=f"{settings.API_V1_PREFIX}/content",
    tags=["Content & Knowledge Base"]
)

app.include_router(
    admin.router,
    prefix=f"{settings.API_V1_PREFIX}/admin",
    tags=["Admin & Approvals"]
)

app.include_router(
    analytics.router,
    prefix=f"{settings.API_V1_PREFIX}",
    tags=["Analytics & Reports"]
)

app.include_router(
    publication_ads.router,
    prefix=f"{settings.API_V1_PREFIX}",
    tags=["Publication Ads"]
)

app.include_router(
    lms.router,
    prefix=f"{settings.API_V1_PREFIX}",
    tags=["Learning Management System"]
)

app.include_router(
    uploads.router,
    prefix=f"{settings.API_V1_PREFIX}/uploads",
    tags=["File Uploads"]
)

app.include_router(
    invoices.router,
    prefix=f"{settings.API_V1_PREFIX}/invoices",
    tags=["Invoices & Billing"]
)

app.include_router(
    payments.router,
    prefix=f"{settings.API_V1_PREFIX}/payments",
    tags=["Payments"]
)

app.include_router(
    geocoding.router,
    prefix=f"{settings.API_V1_PREFIX}",
    tags=["Geocoding & Location"]
)

app.include_router(
    files.router,
    prefix=f"{settings.API_V1_PREFIX}",
    tags=["File Serving"]
)


# ============================================================================
# STATIC FILES (for VPS file storage)
# ============================================================================

# Mount static files directory for serving uploaded files
upload_base_dir = os.getenv("UPLOAD_BASE_DIR", os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads"))
if os.path.exists(upload_base_dir):
    app.mount("/static", StaticFiles(directory=upload_base_dir), name="static")
    logger.info(f"Static files mounted at /static from {upload_base_dir}")
else:
    logger.warning(f"Upload directory does not exist: {upload_base_dir}. Static file serving disabled.")


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """
    Custom 404 handler
    """
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not Found",
            "message": "The requested resource was not found",
            "path": str(request.url)
        }
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    """
    Custom 500 handler
    """
    logger.error(f"Internal server error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred. Please try again later."
        }
    )


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )

