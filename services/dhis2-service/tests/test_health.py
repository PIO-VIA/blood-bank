import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch
import time

from app.main import app


@pytest.mark.asyncio
async def test_health_check_success():
    """Test successful health check."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch('app.routers.health.get_db_session') as mock_db, \
             patch('app.services.dhis2_client.DHIS2Client') as mock_dhis2:
            
            # Mock database session
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            mock_session.execute = AsyncMock()
            
            # Mock DHIS2 client
            mock_client = AsyncMock()
            mock_dhis2.return_value.__aenter__.return_value = mock_client
            mock_client.test_connection.return_value = True
            
            response = await client.get("/api/v1/health/")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["database_status"] == "healthy"
            assert data["dhis2_status"] == "healthy"
            assert "uptime_seconds" in data
            assert "version" in data


@pytest.mark.asyncio
async def test_health_check_database_failure():
    """Test health check with database failure."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch('app.routers.health.get_db_session') as mock_db, \
             patch('app.services.dhis2_client.DHIS2Client') as mock_dhis2:
            
            # Mock database failure
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            mock_session.execute.side_effect = Exception("Database connection failed")
            
            # Mock DHIS2 client success
            mock_client = AsyncMock()
            mock_dhis2.return_value.__aenter__.return_value = mock_client
            mock_client.test_connection.return_value = True
            
            response = await client.get("/api/v1/health/")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "degraded"
            assert "unhealthy" in data["database_status"]
            assert data["dhis2_status"] == "healthy"


@pytest.mark.asyncio
async def test_health_check_dhis2_failure():
    """Test health check with DHIS2 failure."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch('app.routers.health.get_db_session') as mock_db, \
             patch('app.services.dhis2_client.DHIS2Client') as mock_dhis2:
            
            # Mock database success
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            mock_session.execute = AsyncMock()
            
            # Mock DHIS2 failure
            mock_client = AsyncMock()
            mock_dhis2.return_value.__aenter__.return_value = mock_client
            mock_client.test_connection.return_value = False
            
            response = await client.get("/api/v1/health/")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "degraded"
            assert data["database_status"] == "healthy"
            assert "unhealthy" in data["dhis2_status"]


@pytest.mark.asyncio
async def test_liveness_probe():
    """Test liveness probe endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/health/live")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"
        assert "timestamp" in data


@pytest.mark.asyncio
async def test_readiness_probe_success():
    """Test successful readiness probe."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch('app.routers.health.get_db_session') as mock_db:
            # Mock database session
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            mock_session.execute = AsyncMock()
            
            response = await client.get("/api/v1/health/ready")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ready"
            assert "timestamp" in data


@pytest.mark.asyncio
async def test_readiness_probe_failure():
    """Test readiness probe with database failure."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch('app.routers.health.get_db_session') as mock_db:
            # Mock database failure
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            mock_session.execute.side_effect = Exception("Database not ready")
            
            response = await client.get("/api/v1/health/ready")
            
            assert response.status_code == 503
            data = response.json()
            assert "Service not ready" in data["detail"]


@pytest.mark.asyncio
async def test_get_metrics():
    """Test metrics endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch('app.routers.health.get_db_session') as mock_db:
            # Mock database session
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            
            # Mock database queries
            mock_result = AsyncMock()
            mock_result.scalar.return_value = 100
            mock_session.execute.return_value = mock_result
            
            response = await client.get("/api/v1/health/metrics")
            
            assert response.status_code == 200
            data = response.json()
            assert "total_donations" in data
            assert "total_products" in data
            assert "available_products" in data
            assert "expired_products" in data
            assert "blood_type_distribution" in data
            assert "last_updated" in data


@pytest.mark.asyncio
async def test_get_version():
    """Test version endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/health/version")
        
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "version" in data
        assert "api_version" in data
        assert "build_time" in data


@pytest.mark.asyncio
async def test_health_check_uptime():
    """Test that uptime is calculated correctly."""
    start_time = time.time()
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch('app.routers.health.get_db_session') as mock_db, \
             patch('app.services.dhis2_client.DHIS2Client') as mock_dhis2:
            
            # Mock successful dependencies
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            mock_session.execute = AsyncMock()
            
            mock_client = AsyncMock()
            mock_dhis2.return_value.__aenter__.return_value = mock_client
            mock_client.test_connection.return_value = True
            
            response = await client.get("/api/v1/health/")
            
            assert response.status_code == 200
            data = response.json()
            
            # Uptime should be positive and reasonable
            assert data["uptime_seconds"] >= 0
            assert data["uptime_seconds"] < (time.time() - start_time + 10)  # Allow some margin