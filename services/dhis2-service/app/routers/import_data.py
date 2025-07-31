from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import uuid
from datetime import datetime
import structlog

from ..models.dhis2_models import (
    BloodDonation, 
    BloodProduct, 
    DonorDemographics,
    BloodScreeningResult,
    DHIS2ImportResponse,
    ErrorResponse
)
from ..models.database import get_db_session, Donor, Donation, BloodProduct as DBBloodProduct, ScreeningResult
from ..services.dhis2_client import DHIS2Client
from ..core.config import settings

logger = structlog.get_logger()
router = APIRouter(prefix="/import", tags=["import"])


@router.post("/donors", response_model=dict)
async def import_donors(
    donors: List[DonorDemographics],
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Import donor demographics data.
    
    This endpoint accepts a list of donor demographic data and stores it
    in the local database. It also schedules background synchronization with DHIS2.
    """
    try:
        imported_count = 0
        failed_count = 0
        errors = []
        
        for donor_data in donors:
            try:
                # Check if donor already exists
                existing_donor = await db.get(Donor, donor_data.id)
                
                if existing_donor:
                    # Update existing donor
                    existing_donor.age = donor_data.age
                    existing_donor.gender = donor_data.gender.value
                    existing_donor.occupation = donor_data.occupation
                    existing_donor.location = donor_data.location
                    existing_donor.contact_info = donor_data.contact_info
                    existing_donor.updated_at = datetime.now()
                else:
                    # Create new donor
                    new_donor = Donor(
                        id=donor_data.id,
                        age=donor_data.age,
                        gender=donor_data.gender.value,
                        occupation=donor_data.occupation,
                        location=donor_data.location,
                        contact_info=donor_data.contact_info
                    )
                    db.add(new_donor)
                
                imported_count += 1
                
            except Exception as e:
                failed_count += 1
                errors.append(f"Donor {donor_data.id}: {str(e)}")
                logger.error("Failed to import donor", donor_id=donor_data.id, error=str(e))
        
        # Commit all changes
        await db.commit()
        
        # Schedule background sync with DHIS2
        background_tasks.add_task(sync_donors_to_dhis2, [d.dict() for d in donors])
        
        logger.info("Donors import completed", 
                   imported=imported_count, 
                   failed=failed_count)
        
        return {
            "status": "completed",
            "imported_count": imported_count,
            "failed_count": failed_count,
            "errors": errors,
            "message": f"Successfully imported {imported_count} donors"
        }
        
    except Exception as e:
        logger.error("Donors import failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@router.post("/donations", response_model=dict)
async def import_donations(
    donations: List[BloodDonation],
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Import blood donation data.
    
    Accepts blood donation records and stores them locally,
    then syncs with DHIS2 in the background.
    """
    try:
        imported_count = 0
        failed_count = 0
        errors = []
        
        for donation_data in donations:
            try:
                # Verify donor exists
                donor = await db.get(Donor, donation_data.donor_id)
                if not donor:
                    errors.append(f"Donation {donation_data.id}: Donor {donation_data.donor_id} not found")
                    failed_count += 1
                    continue
                
                # Check if donation already exists
                existing_donation = await db.get(Donation, donation_data.id)
                
                if existing_donation:
                    # Update existing donation
                    existing_donation.donation_date = donation_data.donation_date
                    existing_donation.blood_type = donation_data.blood_type.value
                    existing_donation.volume_collected = donation_data.volume_collected
                    existing_donation.collection_site = donation_data.collection_site
                    existing_donation.staff_id = donation_data.staff_id
                    existing_donation.updated_at = datetime.now()
                else:
                    # Create new donation
                    new_donation = Donation(
                        id=donation_data.id,
                        donor_id=donation_data.donor_id,
                        donation_date=donation_data.donation_date,
                        blood_type=donation_data.blood_type.value,
                        volume_collected=donation_data.volume_collected,
                        collection_site=donation_data.collection_site,
                        staff_id=donation_data.staff_id
                    )
                    db.add(new_donation)
                
                imported_count += 1
                
            except Exception as e:
                failed_count += 1
                errors.append(f"Donation {donation_data.id}: {str(e)}")
                logger.error("Failed to import donation", donation_id=donation_data.id, error=str(e))
        
        await db.commit()
        
        # Schedule background sync with DHIS2
        background_tasks.add_task(sync_donations_to_dhis2, [d.dict() for d in donations])
        
        logger.info("Donations import completed", 
                   imported=imported_count, 
                   failed=failed_count)
        
        return {
            "status": "completed",
            "imported_count": imported_count,
            "failed_count": failed_count,
            "errors": errors,
            "message": f"Successfully imported {imported_count} donations"
        }
        
    except Exception as e:
        logger.error("Donations import failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@router.post("/blood-products", response_model=dict)
async def import_blood_products(
    products: List[BloodProduct],
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Import blood product inventory data.
    
    Accepts blood product records for inventory tracking.
    """
    try:
        imported_count = 0
        failed_count = 0
        errors = []
        
        for product_data in products:
            try:
                # Verify donation exists
                donation = await db.get(Donation, product_data.donation_id)
                if not donation:
                    errors.append(f"Product {product_data.id}: Donation {product_data.donation_id} not found")
                    failed_count += 1
                    continue
                
                # Check if product already exists
                existing_product = await db.get(DBBloodProduct, product_data.id)
                
                if existing_product:
                    # Update existing product
                    existing_product.blood_type = product_data.blood_type.value
                    existing_product.product_type = product_data.product_type
                    existing_product.volume = product_data.volume
                    existing_product.collection_date = product_data.collection_date
                    existing_product.expiry_date = product_data.expiry_date
                    existing_product.status = product_data.status.value
                    existing_product.location = product_data.location
                    existing_product.temperature = product_data.temperature
                    existing_product.updated_at = datetime.now()
                else:
                    # Create new product
                    new_product = DBBloodProduct(
                        id=product_data.id,
                        donation_id=product_data.donation_id,
                        blood_type=product_data.blood_type.value,
                        product_type=product_data.product_type,
                        volume=product_data.volume,
                        collection_date=product_data.collection_date,
                        expiry_date=product_data.expiry_date,
                        status=product_data.status.value,
                        location=product_data.location,
                        temperature=product_data.temperature
                    )
                    db.add(new_product)
                
                imported_count += 1
                
            except Exception as e:
                failed_count += 1
                errors.append(f"Product {product_data.id}: {str(e)}")
                logger.error("Failed to import blood product", product_id=product_data.id, error=str(e))
        
        await db.commit()
        
        # Schedule background sync with DHIS2
        background_tasks.add_task(sync_inventory_to_dhis2, [p.dict() for p in products])
        
        logger.info("Blood products import completed", 
                   imported=imported_count, 
                   failed=failed_count)
        
        return {
            "status": "completed",
            "imported_count": imported_count,
            "failed_count": failed_count,
            "errors": errors,
            "message": f"Successfully imported {imported_count} blood products"
        }
        
    except Exception as e:
        logger.error("Blood products import failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@router.post("/screening-results", response_model=dict)
async def import_screening_results(
    results: List[BloodScreeningResult],
    db: AsyncSession = Depends(get_db_session)
):
    """
    Import blood screening test results.
    """
    try:
        imported_count = 0
        failed_count = 0
        errors = []
        
        for result_data in results:
            try:
                # Verify donor exists
                donor = await db.get(Donor, result_data.donor_id)
                if not donor:
                    errors.append(f"Screening result for donor {result_data.donor_id}: Donor not found")
                    failed_count += 1
                    continue
                
                # Create new screening result
                new_result = ScreeningResult(
                    id=str(uuid.uuid4()),
                    donor_id=result_data.donor_id,
                    blood_type=result_data.blood_type.value,
                    hemoglobin_level=result_data.hemoglobin_level,
                    hiv_test=result_data.hiv_test,
                    hepatitis_b_test=result_data.hepatitis_b_test,
                    hepatitis_c_test=result_data.hepatitis_c_test,
                    syphilis_test=result_data.syphilis_test,
                    screening_date=result_data.screening_date
                )
                db.add(new_result)
                imported_count += 1
                
            except Exception as e:
                failed_count += 1
                errors.append(f"Screening result for donor {result_data.donor_id}: {str(e)}")
                logger.error("Failed to import screening result", donor_id=result_data.donor_id, error=str(e))
        
        await db.commit()
        
        logger.info("Screening results import completed", 
                   imported=imported_count, 
                   failed=failed_count)
        
        return {
            "status": "completed",
            "imported_count": imported_count,
            "failed_count": failed_count,
            "errors": errors,
            "message": f"Successfully imported {imported_count} screening results"
        }
        
    except Exception as e:
        logger.error("Screening results import failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


# Background tasks for DHIS2 synchronization

async def sync_donors_to_dhis2(donors_data: List[dict]):
    """Background task to sync donors to DHIS2."""
    try:
        async with DHIS2Client() as client:
            for donor_data in donors_data:
                await client.create_tracked_entity_instance(donor_data)
        logger.info("Donors synced to DHIS2", count=len(donors_data))
    except Exception as e:
        logger.error("Failed to sync donors to DHIS2", error=str(e))


async def sync_donations_to_dhis2(donations_data: List[dict]):
    """Background task to sync donations to DHIS2."""
    try:
        async with DHIS2Client() as client:
            # Convert to BloodDonation objects for export
            donations = [BloodDonation(**data) for data in donations_data]
            result = await client.export_blood_donations(donations)
            logger.info("Donations synced to DHIS2", result=result.dict())
    except Exception as e:
        logger.error("Failed to sync donations to DHIS2", error=str(e))


async def sync_inventory_to_dhis2(products_data: List[dict]):
    """Background task to sync inventory to DHIS2."""
    try:
        async with DHIS2Client() as client:
            # Convert to BloodProduct objects for export
            products = [BloodProduct(**data) for data in products_data]
            result = await client.export_blood_inventory(products)
            logger.info("Inventory synced to DHIS2", result=result.dict())
    except Exception as e:
        logger.error("Failed to sync inventory to DHIS2", error=str(e))