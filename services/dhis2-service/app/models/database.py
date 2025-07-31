from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, Text, ForeignKey, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum
from contextlib import asynccontextmanager

from ..core.config import settings

Base = declarative_base()

# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True
)

# Create async session factory
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def init_database():
    """Initialize database tables."""
    async with engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)


@asynccontextmanager
async def get_db_session() -> AsyncSession:
    """Get database session context manager."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Dependency for FastAPI
async def get_db() -> AsyncSession:
    """Database dependency for FastAPI."""
    async with get_db_session() as session:
        yield session


class BloodTypeEnum(enum.Enum):
    """Blood type enumeration for database."""
    A_POSITIVE = "A+"
    A_NEGATIVE = "A-"
    B_POSITIVE = "B+"
    B_NEGATIVE = "B-"
    AB_POSITIVE = "AB+"
    AB_NEGATIVE = "AB-"
    O_POSITIVE = "O+"
    O_NEGATIVE = "O-"


class GenderEnum(enum.Enum):
    """Gender enumeration for database."""
    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHER = "OTHER"


class ProductStatusEnum(enum.Enum):
    """Product status enumeration for database."""
    AVAILABLE = "AVAILABLE"
    RESERVED = "RESERVED"
    EXPIRED = "EXPIRED"
    USED = "USED"
    QUARANTINE = "QUARANTINE"


class Donor(Base):
    """Donor database model."""
    __tablename__ = "donors"
    
    id = Column(String, primary_key=True, index=True)
    age = Column(Integer, nullable=False)
    gender = Column(Enum(GenderEnum), nullable=False)
    occupation = Column(String, nullable=True)
    location = Column(String, nullable=True)
    contact_info = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    donations = relationship("Donation", back_populates="donor")
    screening_results = relationship("ScreeningResult", back_populates="donor")


class ScreeningResult(Base):
    """Blood screening result database model."""
    __tablename__ = "screening_results"
    
    id = Column(String, primary_key=True, index=True)
    donor_id = Column(String, ForeignKey("donors.id"), nullable=False)
    blood_type = Column(Enum(BloodTypeEnum), nullable=False)
    hemoglobin_level = Column(Float, nullable=False)
    hiv_test = Column(Boolean, nullable=False)
    hepatitis_b_test = Column(Boolean, nullable=False)
    hepatitis_c_test = Column(Boolean, nullable=False)
    syphilis_test = Column(Boolean, nullable=False)
    screening_date = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    donor = relationship("Donor", back_populates="screening_results")


class Donation(Base):
    """Blood donation database model."""
    __tablename__ = "donations"
    
    id = Column(String, primary_key=True, index=True)
    donor_id = Column(String, ForeignKey("donors.id"), nullable=False)
    donation_date = Column(DateTime, nullable=False)
    blood_type = Column(Enum(BloodTypeEnum), nullable=False)
    volume_collected = Column(Float, nullable=False)
    collection_site = Column(String, nullable=False)
    staff_id = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    donor = relationship("Donor", back_populates="donations")
    products = relationship("BloodProduct", back_populates="donation")


class BloodProduct(Base):
    """Blood product database model."""
    __tablename__ = "blood_products"
    
    id = Column(String, primary_key=True, index=True)
    donation_id = Column(String, ForeignKey("donations.id"), nullable=False)
    blood_type = Column(Enum(BloodTypeEnum), nullable=False)
    product_type = Column(String, nullable=False)
    volume = Column(Float, nullable=False)
    collection_date = Column(DateTime, nullable=False)
    expiry_date = Column(DateTime, nullable=False)
    status = Column(Enum(ProductStatusEnum), default=ProductStatusEnum.AVAILABLE)
    location = Column(String, nullable=False)
    temperature = Column(Float, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    donation = relationship("Donation", back_populates="products")
    movements = relationship("StockMovement", back_populates="product")


class StockMovement(Base):
    """Stock movement database model."""
    __tablename__ = "stock_movements"
    
    id = Column(String, primary_key=True, index=True)
    product_id = Column(String, ForeignKey("blood_products.id"), nullable=False)
    movement_type = Column(String, nullable=False)  # IN, OUT, TRANSFER
    quantity = Column(Integer, nullable=False)
    movement_date = Column(DateTime, default=func.now())
    from_location = Column(String, nullable=True)
    to_location = Column(String, nullable=True)
    reason = Column(Text, nullable=False)
    staff_id = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    product = relationship("BloodProduct", back_populates="movements")


class SyncLog(Base):
    """DHIS2 synchronization log."""
    __tablename__ = "sync_logs"
    
    id = Column(String, primary_key=True, index=True)
    sync_type = Column(String, nullable=False)  # IMPORT, EXPORT
    status = Column(String, nullable=False)  # SUCCESS, FAILED, PARTIAL
    records_processed = Column(Integer, default=0)
    records_success = Column(Integer, default=0)
    records_failed = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    dhis2_response = Column(Text, nullable=True)
    
    
class APIUsage(Base):
    """API usage tracking."""
    __tablename__ = "api_usage"
    
    id = Column(String, primary_key=True, index=True)
    endpoint = Column(String, nullable=False)
    method = Column(String, nullable=False)
    status_code = Column(Integer, nullable=False)
    response_time = Column(Float, nullable=False)
    user_agent = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    timestamp = Column(DateTime, default=func.now())