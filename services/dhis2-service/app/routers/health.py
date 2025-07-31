from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import time
import asyncio
import structlog

from ..models.dhis2_models import HealthCheckResponse, MetricsResponse
from ..services.dhis2_client import DHIS2Client
from ..core.config import settings
from ..models.database import get_db_session

logger = structlog.get_logger()
router = APIRouter(prefix="/health", tags=["health"])

# Store service start time for uptime calculation
SERVICE_START_TIME = time.time()


@router.get("/", response_model=HealthCheckResponse)
async def health_check(db: AsyncSession = Depends(get_db_session)):
    """
    Comprehensive health check endpoint.
    
    Checks:
    - Service status
    - Database connectivity
    - DHIS2 connectivity
    - Service uptime
    """
    try:
        # Check database connectivity
        database_status = "healthy"
        try:
            await db.execute("SELECT 1")
        except Exception as e:
            database_status = f"unhealthy: {str(e)}"
            logger.error("Database health check failed", error=str(e))
        
        # Check DHIS2 connectivity
        dhis2_status = "healthy"
        try:
            async with DHIS2Client() as client:
                dhis2_healthy = await client.test_connection()
                if not dhis2_healthy:
                    dhis2_status = "unhealthy: connection failed"
        except Exception as e:
            dhis2_status = f"unhealthy: {str(e)}"
            logger.error("DHIS2 health check failed", error=str(e))
        
        # Calculate uptime
        uptime_seconds = time.time() - SERVICE_START_TIME
        
        # Determine overall status
        overall_status = "healthy"
        if "unhealthy" in database_status or "unhealthy" in dhis2_status:
            overall_status = "degraded"
        
        return HealthCheckResponse(
            status=overall_status,
            version=settings.APP_VERSION,
            database_status=database_status,
            dhis2_status=dhis2_status,
            uptime_seconds=uptime_seconds
        )
        
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


@router.get("/live")
async def liveness_probe():
    """
    Kubernetes liveness probe endpoint.
    Simple check to verify the service is running.
    """
    return {"status": "alive", "timestamp": datetime.now().isoformat()}


@router.get("/ready")
async def readiness_probe(db: AsyncSession = Depends(get_db_session)):
    """
    Kubernetes readiness probe endpoint.
    Checks if the service is ready to handle requests.
    """
    try:
        # Quick database check
        await db.execute("SELECT 1")
        return {"status": "ready", "timestamp": datetime.now().isoformat()}
    except Exception as e:
        logger.error("Readiness probe failed", error=str(e))
        raise HTTPException(status_code=503, detail="Service not ready")


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(db: AsyncSession = Depends(get_db_session)):
    """
    Get service metrics for monitoring.
    
    Returns basic metrics about blood bank data:
    - Total donations
    - Total products
    - Available products
    - Expired products
    - Blood type distribution
    """
    try:
        # This would query actual database tables
        # For now, returning mock data structure
        
        from sqlalchemy import text
        
        # Total donations (mock query)
        total_donations_result = await db.execute(
            text("SELECT COUNT(*) as count FROM donations")
        )
        total_donations = total_donations_result.scalar() or 0
        
        # Total products (mock query)
        total_products_result = await db.execute(
            text("SELECT COUNT(*) as count FROM blood_products")
        )
        total_products = total_products_result.scalar() or 0
        
        # Available products
        available_products_result = await db.execute(
            text("SELECT COUNT(*) as count FROM blood_products WHERE status = 'AVAILABLE'")
        )
        available_products = available_products_result.scalar() or 0
        
        # Expired products
        expired_products_result = await db.execute(
            text("SELECT COUNT(*) as count FROM blood_products WHERE status = 'EXPIRED'")
        )
        expired_products = expired_products_result.scalar() or 0
        
        # Blood type distribution (simplified)
        blood_type_distribution = {
            "A+": 0, "A-": 0, "B+": 0, "B-": 0,
            "AB+": 0, "AB-": 0, "O+": 0, "O-": 0
        }
        
        # Get actual distribution
        distribution_result = await db.execute(
            text("""
                SELECT blood_type, COUNT(*) as count 
                FROM blood_products 
                WHERE status = 'AVAILABLE'
                GROUP BY blood_type
            """)
        )
        
        for row in distribution_result:
            blood_type_distribution[row.blood_type] = row.count
        
        return MetricsResponse(
            total_donations=total_donations,
            total_products=total_products,
            available_products=available_products,
            expired_products=expired_products,
            blood_type_distribution=blood_type_distribution
        )
        
    except Exception as e:
        logger.error("Failed to get metrics", error=str(e))
        # Return default metrics on error
        return MetricsResponse(
            total_donations=0,
            total_products=0,
            available_products=0,
            expired_products=0,
            blood_type_distribution={
                "A+": 0, "A-": 0, "B+": 0, "B-": 0,
                "AB+": 0, "AB-": 0, "O+": 0, "O-": 0
            }
        )


@router.get("/version")
async def get_version():
    """Get service version information."""
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "api_version": settings.API_V1_STR,
        "build_time": datetime.now().isoformat()
    }