import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch
from datetime import datetime, timedelta
import uuid

from app.main import app


@pytest.mark.asyncio
async def test_get_sync_status_healthy():
    """Test sync status when system is healthy."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch('app.routers.sync.get_db_session') as mock_db:
            # Mock database session
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            
            # Mock successful sync log
            mock_last_sync = AsyncMock()
            mock_last_sync.completed_at = datetime.now() - timedelta(minutes=30)
            
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none.return_value = mock_last_sync
            mock_result.scalar.return_value = 5  # 5 successful syncs
            
            mock_session.execute.return_value = mock_result
            
            response = await client.get("/api/v1/sync/status")
            
            assert response.status_code == 200
            data = response.json()
            assert data["sync_status"] == "healthy"
            assert data["records_synced"] == 5
            assert data["last_sync"] is not None
            assert len(data["errors"]) == 0


@pytest.mark.asyncio
async def test_get_sync_status_with_errors():
    """Test sync status when there are recent errors."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch('app.routers.sync.get_db_session') as mock_db:
            # Mock database session
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            
            # Mock results with errors
            mock_results = [
                AsyncMock(scalar_one_or_none=lambda: None),  # No successful sync
                AsyncMock(scalar=lambda: 0),  # 0 successful syncs
                AsyncMock(  # Errors
                    __iter__=lambda x: iter([
                        AsyncMock(error_message="DHIS2 connection failed"),
                        AsyncMock(error_message="Data validation error")
                    ])
                ),
                AsyncMock(scalar_one_or_none=lambda: None)  # No ongoing sync
            ]
            
            mock_session.execute.side_effect = mock_results
            
            response = await client.get("/api/v1/sync/status")
            
            assert response.status_code == 200
            data = response.json()
            assert data["sync_status"] == "error"
            assert data["records_synced"] == 0
            assert data["last_sync"] is None
            assert len(data["errors"]) == 2


@pytest.mark.asyncio
async def test_sync_donations_success():
    """Test successful donation sync initiation."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch('app.routers.sync.get_db_session') as mock_db:
            # Mock database session
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            mock_session.add = AsyncMock()
            mock_session.commit = AsyncMock()
            
            response = await client.post("/api/v1/sync/donations?days_back=7")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "started"
            assert "sync_id" in data
            assert "7 days" in data["message"]


@pytest.mark.asyncio
async def test_sync_inventory_success():
    """Test successful inventory sync initiation."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch('app.routers.sync.get_db_session') as mock_db:
            # Mock database session
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            mock_session.add = AsyncMock()
            mock_session.commit = AsyncMock()
            
            response = await client.post("/api/v1/sync/inventory")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "started"
            assert "sync_id" in data
            assert "Inventory sync initiated" in data["message"]


@pytest.mark.asyncio
async def test_full_sync_success():
    """Test successful full sync initiation."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch('app.routers.sync.get_db_session') as mock_db:
            # Mock database session
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            mock_session.add = AsyncMock()
            mock_session.commit = AsyncMock()
            
            response = await client.post("/api/v1/sync/full")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "started"
            assert "sync_id" in data
            assert "Full sync initiated" in data["message"]


@pytest.mark.asyncio
async def test_get_sync_log_success():
    """Test retrieving sync log details."""
    sync_id = str(uuid.uuid4())
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch('app.routers.sync.get_db_session') as mock_db:
            # Mock database session
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            
            # Mock sync log
            mock_sync_log = AsyncMock()
            mock_sync_log.id = sync_id
            mock_sync_log.sync_type = "EXPORT_DONATIONS"
            mock_sync_log.status = "SUCCESS" 
            mock_sync_log.records_processed = 100
            mock_sync_log.records_success = 95
            mock_sync_log.records_failed = 5
            mock_sync_log.error_message = None
            mock_sync_log.started_at = datetime.now() - timedelta(hours=1)
            mock_sync_log.completed_at = datetime.now() - timedelta(minutes=50)
            mock_sync_log.dhis2_response = '{"status": "SUCCESS"}'
            
            mock_session.get.return_value = mock_sync_log
            
            response = await client.get(f"/api/v1/sync/logs/{sync_id}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == sync_id
            assert data["sync_type"] == "EXPORT_DONATIONS"
            assert data["status"] == "SUCCESS"
            assert data["records_processed"] == 100
            assert data["records_success"] == 95
            assert data["records_failed"] == 5


@pytest.mark.asyncio
async def test_get_sync_log_not_found():
    """Test retrieving non-existent sync log."""
    sync_id = str(uuid.uuid4())
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch('app.routers.sync.get_db_session') as mock_db:
            # Mock database session
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            mock_session.get.return_value = None  # Log not found
            
            response = await client.get(f"/api/v1/sync/logs/{sync_id}")
            
            assert response.status_code == 404
            data = response.json()
            assert "not found" in data["detail"]


@pytest.mark.asyncio
async def test_clear_sync_cache():
    """Test clearing sync cache."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.delete("/api/v1/sync/cache")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "cache cleared" in data["message"]


@pytest.mark.asyncio
async def test_sync_database_error():
    """Test sync initiation with database error."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch('app.routers.sync.get_db_session') as mock_db:
            # Mock database error
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            mock_session.commit.side_effect = Exception("Database error")
            
            response = await client.post("/api/v1/sync/donations")
            
            assert response.status_code == 500
            data = response.json()
            assert "Sync failed" in data["detail"]


@pytest.mark.asyncio
async def test_sync_status_ongoing():
    """Test sync status when sync is ongoing."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch('app.routers.sync.get_db_session') as mock_db:
            # Mock database session
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            
            # Mock ongoing sync
            mock_ongoing_sync = AsyncMock()
            mock_ongoing_sync.started_at = datetime.now() - timedelta(minutes=5)
            mock_ongoing_sync.completed_at = None
            
            mock_results = [
                AsyncMock(scalar_one_or_none=lambda: None),  # No completed sync
                AsyncMock(scalar=lambda: 0),  # 0 successful syncs
                AsyncMock(__iter__=lambda x: iter([])),  # No errors
                AsyncMock(scalar_one_or_none=lambda: mock_ongoing_sync)  # Ongoing sync
            ]
            
            mock_session.execute.side_effect = mock_results
            
            response = await client.get("/api/v1/sync/status")
            
            assert response.status_code == 200
            data = response.json()
            assert data["sync_status"] == "syncing"