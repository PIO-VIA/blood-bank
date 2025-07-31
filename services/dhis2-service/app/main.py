from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import time
import structlog
from contextlib import asynccontextmanager

from .core.config import settings
from .routers import health, import_data, sync
from .models.database import init_database
from .utils.monitoring import setup_prometheus_metrics

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting DHIS2 Blood Bank Service", version=settings.APP_VERSION)
    
    # Initialize database
    await init_database()
    
    # Setup monitoring
    if settings.ENABLE_METRICS:
        setup_prometheus_metrics()
    
    logger.info("Service startup completed")
    
    yield
    
    # Shutdown
    logger.info("Shutting down DHIS2 Blood Bank Service")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="DHIS2 integration service for blood bank management system",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add trusted host middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # Configure appropriately for production
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests."""
    start_time = time.time()
    
    # Log request
    logger.info(
        "Request started",
        method=request.method,
        url=str(request.url),
        client=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    
    # Process request
    try:
        response = await call_next(request)
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Log response
        logger.info(
            "Request completed",
            method=request.method,
            url=str(request.url),
            status_code=response.status_code,
            process_time=process_time
        )
        
        # Add processing time header
        response.headers["X-Process-Time"] = str(process_time)
        
        return response
        
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(
            "Request failed",
            method=request.method,
            url=str(request.url),
            error=str(e),
            process_time=process_time
        )
        raise


# Global exception handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    logger.error(
        "HTTP exception",
        method=request.method,
        url=str(request.url),
        status_code=exc.status_code,
        detail=exc.detail
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": time.time()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.error(
        "Unhandled exception",
        method=request.method,
        url=str(request.url),
        error=str(exc),
        error_type=type(exc).__name__
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "status_code": 500,
            "timestamp": time.time()
        }
    )


# Include routers
app.include_router(health.router, prefix=settings.API_V1_STR)
app.include_router(import_data.router, prefix=settings.API_V1_STR)
app.include_router(sync.router, prefix=settings.API_V1_STR)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
        "health": f"{settings.API_V1_STR}/health",
        "timestamp": time.time()
    }


# API information endpoint
@app.get(f"{settings.API_V1_STR}/info")
async def api_info():
    """API information endpoint."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "api_version": settings.API_V1_STR,
        "environment": "development" if settings.DEBUG else "production",
        "dhis2_base_url": settings.DHIS2_BASE_URL,
        "features": {
            "health_checks": True,
            "data_import": True,
            "dhis2_sync": True,
            "monitoring": settings.ENABLE_METRICS
        },
        "endpoints": {
            "health": f"{settings.API_V1_STR}/health",
            "import": f"{settings.API_V1_STR}/import",
            "sync": f"{settings.API_V1_STR}/sync"
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )