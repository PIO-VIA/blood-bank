from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum


class BloodType(str, Enum):
    """Blood type enumeration."""
    A_POSITIVE = "A+"
    A_NEGATIVE = "A-"
    B_POSITIVE = "B+"
    B_NEGATIVE = "B-"
    AB_POSITIVE = "AB+"
    AB_NEGATIVE = "AB-"
    O_POSITIVE = "O+"
    O_NEGATIVE = "O-"


class DonorGender(str, Enum):
    """Donor gender enumeration."""
    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHER = "OTHER"


class BloodProductStatus(str, Enum):
    """Blood product status enumeration."""
    AVAILABLE = "AVAILABLE"
    RESERVED = "RESERVED"
    EXPIRED = "EXPIRED"
    USED = "USED"
    QUARANTINE = "QUARANTINE"


class DonorDemographics(BaseModel):
    """Donor demographic information."""
    id: str = Field(..., description="Unique donor identifier")
    age: int = Field(..., ge=18, le=65, description="Donor age")
    gender: DonorGender = Field(..., description="Donor gender")
    occupation: Optional[str] = Field(None, description="Donor occupation")
    location: Optional[str] = Field(None, description="Donor location")
    contact_info: Optional[str] = Field(None, description="Contact information")
    
    @validator('age')
    def validate_age(cls, v):
        if not 18 <= v <= 65:
            raise ValueError('Age must be between 18 and 65')
        return v


class BloodScreeningResult(BaseModel):
    """Blood screening test results."""
    donor_id: str = Field(..., description="Donor identifier")
    blood_type: BloodType = Field(..., description="Blood type")
    hemoglobin_level: float = Field(..., ge=12.0, le=20.0, description="Hemoglobin level (g/dL)")
    hiv_test: bool = Field(..., description="HIV test result (True = negative)")
    hepatitis_b_test: bool = Field(..., description="Hepatitis B test result (True = negative)")
    hepatitis_c_test: bool = Field(..., description="Hepatitis C test result (True = negative)")
    syphilis_test: bool = Field(..., description="Syphilis test result (True = negative)")
    screening_date: datetime = Field(default_factory=datetime.now, description="Screening date")
    
    @validator('hemoglobin_level')
    def validate_hemoglobin(cls, v):
        if not 12.0 <= v <= 20.0:
            raise ValueError('Hemoglobin level must be between 12.0 and 20.0 g/dL')
        return v


class BloodDonation(BaseModel):
    """Blood donation record."""
    id: str = Field(..., description="Unique donation identifier")
    donor_id: str = Field(..., description="Donor identifier")
    donation_date: datetime = Field(..., description="Date of donation")
    blood_type: BloodType = Field(..., description="Blood type")
    volume_collected: float = Field(..., ge=300, le=500, description="Volume collected (mL)")
    collection_site: str = Field(..., description="Collection site")
    staff_id: str = Field(..., description="Collection staff identifier")
    
    @validator('volume_collected')
    def validate_volume(cls, v):
        if not 300 <= v <= 500:
            raise ValueError('Volume must be between 300 and 500 mL')
        return v


class BloodProduct(BaseModel):
    """Blood product inventory item."""
    id: str = Field(..., description="Unique product identifier")
    donation_id: str = Field(..., description="Source donation identifier")
    blood_type: BloodType = Field(..., description="Blood type")
    product_type: str = Field(..., description="Product type (whole blood, plasma, etc.)")
    volume: float = Field(..., gt=0, description="Product volume (mL)")
    collection_date: datetime = Field(..., description="Collection date")
    expiry_date: datetime = Field(..., description="Expiry date")
    status: BloodProductStatus = Field(default=BloodProductStatus.AVAILABLE, description="Product status")
    location: str = Field(..., description="Storage location")
    temperature: Optional[float] = Field(None, description="Storage temperature")
    
    @validator('expiry_date')
    def validate_expiry_date(cls, v, values):
        if 'collection_date' in values and v <= values['collection_date']:
            raise ValueError('Expiry date must be after collection date')
        return v


class StockMovement(BaseModel):
    """Blood stock movement record."""
    id: str = Field(..., description="Unique movement identifier")
    product_id: str = Field(..., description="Blood product identifier")
    movement_type: str = Field(..., description="Movement type (IN/OUT/TRANSFER)")
    quantity: int = Field(..., gt=0, description="Quantity moved")
    movement_date: datetime = Field(default_factory=datetime.now, description="Movement date")
    from_location: Optional[str] = Field(None, description="Source location")
    to_location: Optional[str] = Field(None, description="Destination location")
    reason: str = Field(..., description="Movement reason")
    staff_id: str = Field(..., description="Staff identifier")


class DHIS2DataElement(BaseModel):
    """DHIS2 data element structure."""
    id: str = Field(..., description="Data element ID")
    name: str = Field(..., description="Data element name")
    value_type: str = Field(..., description="Value type")
    domain_type: str = Field(..., description="Domain type")


class DHIS2DataValue(BaseModel):
    """DHIS2 data value structure."""
    data_element: str = Field(..., description="Data element ID")
    period: str = Field(..., description="Period")
    org_unit: str = Field(..., description="Organization unit ID")
    value: Union[str, int, float] = Field(..., description="Value")
    attribute_option_combo: Optional[str] = Field(None, description="Attribute option combo")


class DHIS2ImportRequest(BaseModel):
    """DHIS2 data import request."""
    data_values: List[DHIS2DataValue] = Field(..., description="Data values to import")


class DHIS2ImportResponse(BaseModel):
    """DHIS2 import response."""
    status: str = Field(..., description="Import status")
    imported_count: int = Field(..., description="Number of imported items")
    updated_count: int = Field(..., description="Number of updated items")
    ignored_count: int = Field(..., description="Number of ignored items")
    deleted_count: int = Field(..., description="Number of deleted items")
    conflicts: List[Dict[str, Any]] = Field(default_factory=list, description="Import conflicts")


class HealthCheckResponse(BaseModel):
    """Health check response model."""
    status: str = Field(..., description="Health status")
    timestamp: datetime = Field(default_factory=datetime.now, description="Check timestamp")
    version: str = Field(..., description="Service version")
    database_status: str = Field(..., description="Database connection status")
    dhis2_status: str = Field(..., description="DHIS2 connection status")
    uptime_seconds: float = Field(..., description="Service uptime in seconds")


class SyncStatusResponse(BaseModel):
    """Synchronization status response."""
    last_sync: Optional[datetime] = Field(None, description="Last successful sync")
    sync_status: str = Field(..., description="Current sync status")
    records_synced: int = Field(..., description="Number of records synced")
    errors: List[str] = Field(default_factory=list, description="Sync errors")


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Error details")
    timestamp: datetime = Field(default_factory=datetime.now, description="Error timestamp")


class MetricsResponse(BaseModel):
    """Metrics response model."""
    total_donations: int = Field(..., description="Total donations count")
    total_products: int = Field(..., description="Total products count")
    available_products: int = Field(..., description="Available products count")
    expired_products: int = Field(..., description="Expired products count")
    blood_type_distribution: Dict[str, int] = Field(..., description="Blood type distribution")
    last_updated: datetime = Field(default_factory=datetime.now, description="Last update timestamp")