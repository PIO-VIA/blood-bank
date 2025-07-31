import pytest
import asyncio
from unittest.mock import AsyncMock
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import os
import sys

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.models.database import Base
from app.core.config import settings


# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        future=True
    )
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Drop tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture
async def test_session(test_engine):
    """Create test database session."""
    async_session = sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session


@pytest.fixture
def mock_dhis2_client():
    """Mock DHIS2 client for testing."""
    client = AsyncMock()
    client.test_connection.return_value = True
    client.get_organization_units.return_value = [
        {"id": "ORG_001", "name": "Test Org Unit"}
    ]
    client.get_data_elements.return_value = [
        {"id": "DE_001", "name": "Test Data Element", "valueType": "TEXT"}
    ]
    client.import_data_values.return_value = AsyncMock(
        status="SUCCESS",
        imported_count=1,
        updated_count=0,
        ignored_count=0,
        deleted_count=0,
        conflicts=[]
    )
    return client


@pytest.fixture
def sample_donor_data():
    """Sample donor data for testing."""
    return {
        "id": "DONOR_TEST_001",
        "age": 30,
        "gender": "MALE",
        "occupation": "Teacher",
        "location": "Douala",
        "contact_info": "+237123456789"
    }


@pytest.fixture
def sample_donation_data():
    """Sample donation data for testing."""
    return {
        "id": "DONATION_TEST_001",
        "donor_id": "DONOR_TEST_001",
        "donation_date": "2024-01-15T10:00:00Z",
        "blood_type": "A+",
        "volume_collected": 450.0,
        "collection_site": "Douala General Hospital",
        "staff_id": "STAFF_001"
    }


@pytest.fixture
def sample_blood_product_data():
    """Sample blood product data for testing."""
    return {
        "id": "PRODUCT_TEST_001",
        "donation_id": "DONATION_TEST_001",
        "blood_type": "A+",
        "product_type": "Whole Blood",
        "volume": 450.0,
        "collection_date": "2024-01-15T10:00:00Z",
        "expiry_date": "2024-02-15T10:00:00Z",
        "status": "AVAILABLE",
        "location": "Fridge_A_01",
        "temperature": 4.0
    }


@pytest.fixture
def sample_screening_data():
    """Sample screening results data for testing."""
    return {
        "donor_id": "DONOR_TEST_001",
        "blood_type": "A+",
        "hemoglobin_level": 14.5,
        "hiv_test": True,
        "hepatitis_b_test": True,
        "hepatitis_c_test": True,
        "syphilis_test": True,
        "screening_date": "2024-01-15T09:00:00Z"
    }


@pytest.fixture(autouse=True)
def override_settings():
    """Override settings for testing."""
    settings.DATABASE_URL = TEST_DATABASE_URL
    settings.DHIS2_BASE_URL = "https://test.dhis2.org"
    settings.DHIS2_USERNAME = "test_user"
    settings.DHIS2_PASSWORD = "test_password"
    settings.SECRET_KEY = "test_secret_key"
    settings.DEBUG = True


@pytest.fixture
def mock_background_tasks():
    """Mock background tasks for testing."""
    return AsyncMock()


class MockSQLAlchemyResult:
    """Mock SQLAlchemy result for testing."""
    
    def __init__(self, data=None, scalar_value=None):
        self.data = data or []
        self.scalar_value = scalar_value
    
    def scalars(self):
        return MockScalars(self.data)
    
    def scalar(self):
        return self.scalar_value
    
    def scalar_one_or_none(self):
        return self.data[0] if self.data else None
    
    def __iter__(self):
        return iter(self.data)


class MockScalars:
    """Mock SQLAlchemy scalars for testing."""
    
    def __init__(self, data):
        self.data = data
    
    def all(self):
        return self.data
    
    def first(self):
        return self.data[0] if self.data else None


@pytest.fixture
def mock_sqlalchemy_result():
    """Factory for creating mock SQLAlchemy results."""
    return MockSQLAlchemyResult