import httpx
import asyncio
from typing import Dict, List, Any, Optional
from tenacity import retry, stop_after_attempt, wait_exponential
import structlog
from datetime import datetime

from ..core.config import settings
from ..models.dhis2_models import (
    DHIS2ImportRequest, 
    DHIS2ImportResponse, 
    DHIS2DataValue,
    BloodDonation,
    BloodProduct
)

logger = structlog.get_logger()


class DHIS2Client:
    """DHIS2 API client for blood bank data synchronization."""
    
    def __init__(self):
        self.base_url = settings.DHIS2_BASE_URL
        self.username = settings.DHIS2_USERNAME
        self.password = settings.DHIS2_PASSWORD
        self.api_version = settings.DHIS2_API_VERSION
        self.session: Optional[httpx.AsyncClient] = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = httpx.AsyncClient(
            base_url=f"{self.base_url}/api/{self.api_version}",
            auth=(self.username, self.password),
            timeout=30.0,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.aclose()
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def test_connection(self) -> bool:
        """Test connection to DHIS2 instance."""
        try:
            response = await self.session.get("/me")
            if response.status_code == 200:
                logger.info("DHIS2 connection successful", user_info=response.json())
                return True
            else:
                logger.error("DHIS2 connection failed", status_code=response.status_code)
                return False
        except Exception as e:
            logger.error("DHIS2 connection error", error=str(e))
            return False
    
    async def get_organization_units(self) -> List[Dict[str, Any]]:
        """Retrieve organization units from DHIS2."""
        try:
            response = await self.session.get(
                "/organisationUnits",
                params={
                    "fields": "id,name,level,parent",
                    "paging": "false"
                }
            )
            response.raise_for_status()
            data = response.json()
            return data.get("organisationUnits", [])
        except Exception as e:
            logger.error("Failed to fetch organization units", error=str(e))
            raise
    
    async def get_data_elements(self, domain_type: str = "TRACKER") -> List[Dict[str, Any]]:
        """Retrieve data elements from DHIS2."""
        try:
            response = await self.session.get(
                "/dataElements",
                params={
                    "fields": "id,name,valueType,domainType",
                    "filter": f"domainType:eq:{domain_type}",
                    "paging": "false"
                }
            )
            response.raise_for_status()
            data = response.json()
            return data.get("dataElements", [])
        except Exception as e:
            logger.error("Failed to fetch data elements", error=str(e))
            raise
    
    async def import_data_values(self, data_values: List[DHIS2DataValue]) -> DHIS2ImportResponse:
        """Import data values to DHIS2."""
        try:
            import_request = DHIS2ImportRequest(data_values=data_values)
            
            response = await self.session.post(
                "/dataValueSets",
                json=import_request.dict(),
                params={"importStrategy": "CREATE_AND_UPDATE"}
            )
            response.raise_for_status()
            
            result = response.json()
            import_summary = result.get("importSummary", {})
            
            return DHIS2ImportResponse(
                status=import_summary.get("status", "ERROR"),
                imported_count=import_summary.get("importCount", 0),
                updated_count=import_summary.get("updateCount", 0),
                ignored_count=import_summary.get("ignoreCount", 0),
                deleted_count=import_summary.get("deleteCount", 0),
                conflicts=import_summary.get("conflicts", [])
            )
            
        except Exception as e:
            logger.error("Failed to import data values", error=str(e))
            raise
    
    async def export_blood_donations(self, donations: List[BloodDonation]) -> DHIS2ImportResponse:
        """Export blood donation data to DHIS2."""
        try:
            data_values = []
            
            for donation in donations:
                # Convert donation to DHIS2 data values
                base_data_value = {
                    "period": donation.donation_date.strftime("%Y%m%d"),
                    "orgUnit": "BLOOD_BANK_ORG_UNIT_ID"  # Should be configured
                }
                
                # Blood type data element
                data_values.append(DHIS2DataValue(
                    data_element="BLOOD_TYPE_DATA_ELEMENT_ID",
                    value=donation.blood_type.value,
                    **base_data_value
                ))
                
                # Volume collected data element  
                data_values.append(DHIS2DataValue(
                    data_element="VOLUME_COLLECTED_DATA_ELEMENT_ID",
                    value=donation.volume_collected,
                    **base_data_value
                ))
                
                # Donor age (if available from relationship)
                # This would require fetching donor info
                
            return await self.import_data_values(data_values)
            
        except Exception as e:
            logger.error("Failed to export blood donations", error=str(e))
            raise
    
    async def export_blood_inventory(self, products: List[BloodProduct]) -> DHIS2ImportResponse:
        """Export blood inventory data to DHIS2."""
        try:
            data_values = []
            
            # Group products by blood type and status
            inventory_summary = {}
            for product in products:
                key = f"{product.blood_type.value}_{product.status.value}"
                inventory_summary[key] = inventory_summary.get(key, 0) + 1
            
            # Create data values for inventory summary
            for key, count in inventory_summary.items():
                blood_type, status = key.split("_")
                
                data_values.append(DHIS2DataValue(
                    data_element="BLOOD_INVENTORY_DATA_ELEMENT_ID",
                    period=datetime.now().strftime("%Y%m"),
                    orgUnit="BLOOD_BANK_ORG_UNIT_ID",
                    value=count,
                    attribute_option_combo=f"{blood_type}_{status}_COMBO_ID"
                ))
            
            return await self.import_data_values(data_values)
            
        except Exception as e:
            logger.error("Failed to export blood inventory", error=str(e))
            raise
    
    async def get_sync_status(self) -> Dict[str, Any]:
        """Get synchronization status from DHIS2."""
        try:
            response = await self.session.get("/synchronization/status")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error("Failed to get sync status", error=str(e))
            return {"status": "ERROR", "message": str(e)}
    
    async def create_tracked_entity_instance(self, donor_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a tracked entity instance for a donor."""
        try:
            payload = {
                "trackedEntityType": "DONOR_TRACKED_ENTITY_TYPE_ID",
                "orgUnit": "BLOOD_BANK_ORG_UNIT_ID",
                "attributes": [
                    {
                        "attribute": "DONOR_ID_ATTRIBUTE_ID",
                        "value": donor_data.get("id")
                    },
                    {
                        "attribute": "DONOR_AGE_ATTRIBUTE_ID", 
                        "value": donor_data.get("age")
                    },
                    {
                        "attribute": "DONOR_GENDER_ATTRIBUTE_ID",
                        "value": donor_data.get("gender")
                    }
                ]
            }
            
            response = await self.session.post(
                "/trackedEntityInstances",
                json=payload
            )
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error("Failed to create tracked entity instance", error=str(e))
            raise


class DHIS2DataMapper:
    """Maps blood bank data to DHIS2 format."""
    
    # These would be configured based on actual DHIS2 setup
    DATA_ELEMENT_MAPPING = {
        "blood_type": "BLOOD_TYPE_DATA_ELEMENT_ID",
        "volume_collected": "VOLUME_COLLECTED_DATA_ELEMENT_ID",
        "donor_age": "DONOR_AGE_DATA_ELEMENT_ID",
        "donor_gender": "DONOR_GENDER_DATA_ELEMENT_ID",
        "hemoglobin_level": "HEMOGLOBIN_LEVEL_DATA_ELEMENT_ID",
        "inventory_count": "BLOOD_INVENTORY_DATA_ELEMENT_ID"
    }
    
    ORG_UNIT_MAPPING = {
        "blood_bank": "BLOOD_BANK_ORG_UNIT_ID",
        "collection_site_1": "COLLECTION_SITE_1_ORG_UNIT_ID",
        "collection_site_2": "COLLECTION_SITE_2_ORG_UNIT_ID"
    }
    
    @classmethod
    def map_donation_to_data_values(cls, donation: BloodDonation, org_unit: str) -> List[DHIS2DataValue]:
        """Map a blood donation to DHIS2 data values."""
        period = donation.donation_date.strftime("%Y%m%d")
        base_params = {
            "period": period,
            "orgUnit": cls.ORG_UNIT_MAPPING.get(org_unit, org_unit)
        }
        
        return [
            DHIS2DataValue(
                data_element=cls.DATA_ELEMENT_MAPPING["blood_type"],
                value=donation.blood_type.value,
                **base_params
            ),
            DHIS2DataValue(
                data_element=cls.DATA_ELEMENT_MAPPING["volume_collected"],
                value=donation.volume_collected,
                **base_params
            )
        ]
    
    @classmethod
    def map_inventory_to_data_values(cls, inventory_data: Dict[str, int], org_unit: str) -> List[DHIS2DataValue]:
        """Map inventory data to DHIS2 data values."""
        period = datetime.now().strftime("%Y%m")
        base_params = {
            "period": period,
            "orgUnit": cls.ORG_UNIT_MAPPING.get(org_unit, org_unit),
            "data_element": cls.DATA_ELEMENT_MAPPING["inventory_count"]
        }
        
        data_values = []
        for blood_type, count in inventory_data.items():
            data_values.append(DHIS2DataValue(
                value=count,
                attribute_option_combo=f"{blood_type}_AVAILABLE_COMBO_ID",
                **base_params
            ))
        
        return data_values