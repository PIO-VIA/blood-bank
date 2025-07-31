import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch
from datetime import datetime
import uuid

from app.main import app
from app.models.dhis2_models import DonorGender, BloodType, BloodProductStatus


@pytest.mark.asyncio
async def test_import_donors_success():
    """Test successful donor import."""
    donor_data = [
        {
            "id": "DONOR_001",
            "age": 25,
            "gender": DonorGender.MALE,
            "occupation": "Teacher",
            "location": "Douala",
            "contact_info": "+237123456789"
        },
        {
            "id": "DONOR_002", 
            "age": 30,
            "gender": DonorGender.FEMALE,
            "occupation": "Nurse",
            "location": "Yaounde",
            "contact_info": "+237987654321"
        }
    ]
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch('app.routers.import_data.get_db_session') as mock_db:
            # Mock database session
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            mock_session.get.return_value = None  # No existing donors
            mock_session.add = AsyncMock()
            mock_session.commit = AsyncMock()
            
            response = await client.post("/api/v1/import/donors", json=donor_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"
            assert data["imported_count"] == 2
            assert data["failed_count"] == 0
            assert len(data["errors"]) == 0


@pytest.mark.asyncio
async def test_import_donors_with_existing():
    """Test donor import with existing donors (update scenario)."""
    donor_data = [
        {
            "id": "DONOR_001",
            "age": 26,  # Updated age
            "gender": DonorGender.MALE,
            "occupation": "Teacher",
            "location": "Douala",
            "contact_info": "+237123456789"
        }
    ]
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch('app.routers.import_data.get_db_session') as mock_db:
            # Mock database session
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            
            # Mock existing donor
            existing_donor = AsyncMock()
            existing_donor.id = "DONOR_001"
            mock_session.get.return_value = existing_donor
            mock_session.commit = AsyncMock()
            
            response = await client.post("/api/v1/import/donors", json=donor_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"
            assert data["imported_count"] == 1
            assert data["failed_count"] == 0


@pytest.mark.asyncio
async def test_import_donations_success():
    """Test successful donation import."""
    donation_data = [
        {
            "id": "DONATION_001",
            "donor_id": "DONOR_001",
            "donation_date": "2024-01-15T10:00:00",
            "blood_type": BloodType.A_POSITIVE,
            "volume_collected": 450.0,
            "collection_site": "Douala General Hospital",
            "staff_id": "STAFF_001"
        }
    ]
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch('app.routers.import_data.get_db_session') as mock_db:
            # Mock database session
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            
            # Mock existing donor
            existing_donor = AsyncMock()
            existing_donor.id = "DONOR_001"
            mock_session.get.return_value = existing_donor
            mock_session.add = AsyncMock()
            mock_session.commit = AsyncMock()
            
            response = await client.post("/api/v1/import/donations", json=donation_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"
            assert data["imported_count"] == 1
            assert data["failed_count"] == 0


@pytest.mark.asyncio
async def test_import_donations_missing_donor():
    """Test donation import with missing donor."""
    donation_data = [
        {
            "id": "DONATION_001",
            "donor_id": "MISSING_DONOR",
            "donation_date": "2024-01-15T10:00:00",
            "blood_type": BloodType.A_POSITIVE,
            "volume_collected": 450.0,
            "collection_site": "Douala General Hospital",
            "staff_id": "STAFF_001"
        }
    ]
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch('app.routers.import_data.get_db_session') as mock_db:
            # Mock database session
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            mock_session.get.return_value = None  # No donor found
            mock_session.commit = AsyncMock()
            
            response = await client.post("/api/v1/import/donations", json=donation_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"
            assert data["imported_count"] == 0
            assert data["failed_count"] == 1
            assert len(data["errors"]) == 1
            assert "Donor MISSING_DONOR not found" in data["errors"][0]


@pytest.mark.asyncio
async def test_import_blood_products_success():
    """Test successful blood product import."""
    product_data = [
        {
            "id": "PRODUCT_001",
            "donation_id": "DONATION_001",
            "blood_type": BloodType.A_POSITIVE,
            "product_type": "Whole Blood",
            "volume": 450.0,
            "collection_date": "2024-01-15T10:00:00",
            "expiry_date": "2024-02-15T10:00:00",
            "status": BloodProductStatus.AVAILABLE,
            "location": "Fridge_A_01",
            "temperature": 4.0
        }
    ]
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch('app.routers.import_data.get_db_session') as mock_db:
            # Mock database session
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            
            # Mock existing donation
            existing_donation = AsyncMock()
            existing_donation.id = "DONATION_001"
            mock_session.get.return_value = existing_donation
            mock_session.add = AsyncMock()
            mock_session.commit = AsyncMock()
            
            response = await client.post("/api/v1/import/blood-products", json=product_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"
            assert data["imported_count"] == 1
            assert data["failed_count"] == 0


@pytest.mark.asyncio
async def test_import_screening_results_success():
    """Test successful screening results import."""
    screening_data = [
        {
            "donor_id": "DONOR_001",
            "blood_type": BloodType.A_POSITIVE,
            "hemoglobin_level": 14.5,
            "hiv_test": True,
            "hepatitis_b_test": True,
            "hepatitis_c_test": True,
            "syphilis_test": True,
            "screening_date": "2024-01-15T09:00:00"
        }
    ]
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch('app.routers.import_data.get_db_session') as mock_db:
            # Mock database session
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            
            # Mock existing donor
            existing_donor = AsyncMock()
            existing_donor.id = "DONOR_001"
            mock_session.get.return_value = existing_donor
            mock_session.add = AsyncMock()
            mock_session.commit = AsyncMock()
            
            response = await client.post("/api/v1/import/screening-results", json=screening_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"
            assert data["imported_count"] == 1
            assert data["failed_count"] == 0


@pytest.mark.asyncio
async def test_import_invalid_data():
    """Test import with invalid data format."""
    invalid_donor_data = [
        {
            "id": "DONOR_001",
            "age": 17,  # Invalid age (too young)
            "gender": "INVALID_GENDER",
            "occupation": "Student"
        }
    ]
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/api/v1/import/donors", json=invalid_donor_data)
        
        # Should return validation error
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_import_database_error():
    """Test import with database error."""
    donor_data = [
        {
            "id": "DONOR_001",
            "age": 25,
            "gender": DonorGender.MALE,
            "occupation": "Teacher"
        }
    ]
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch('app.routers.import_data.get_db_session') as mock_db:
            # Mock database error
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            mock_session.get.return_value = None
            mock_session.commit.side_effect = Exception("Database error")
            
            response = await client.post("/api/v1/import/donors", json=donor_data)
            
            assert response.status_code == 500
            data = response.json()
            assert "Import failed" in data["detail"]


@pytest.mark.asyncio
async def test_import_empty_list():
    """Test import with empty data list."""
    empty_data = []
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch('app.routers.import_data.get_db_session') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            mock_session.commit = AsyncMock()
            
            response = await client.post("/api/v1/import/donors", json=empty_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"
            assert data["imported_count"] == 0
            assert data["failed_count"] == 0