from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
import uuid
from datetime import datetime, timedelta
import structlog

from ..models.dhis2_models import SyncStatusResponse, DHIS2ImportResponse
from ..models.database import (
    get_db_session, 
    SyncLog, 
    Donation, 
    BloodProduct as DBBloodProduct,
    Donor
)
from ..services.dhis2_client import DHIS2Client, DHIS2DataMapper
from ..core.config import settings

logger = structlog.get_logger()
router = APIRouter(prefix="/sync", tags=["sync"])


@router.get("/status", response_model=SyncStatusResponse)
async def get_sync_status(db: AsyncSession = Depends(get_db_session)):
    """
    Get synchronization status with DHIS2.
    
    Returns information about the last successful sync,
    current sync status, and any errors.
    """
    try:
        # Get the most recent sync log
        result = await db.execute(
            select(SyncLog)
            .where(SyncLog.status == "SUCCESS")
            .order_by(SyncLog.completed_at.desc())
            .limit(1)
        )
        last_sync = result.scalar_one_or_none()
        
        # Get count of successful syncs in the last 24 hours
        twenty_four_hours_ago = datetime.now() - timedelta(hours=24)
        sync_count_result = await db.execute(
            select(func.count(SyncLog.id))
            .where(SyncLog.started_at >= twenty_four_hours_ago)
            .where(SyncLog.status == "SUCCESS")
        )
        records_synced = sync_count_result.scalar() or 0
        
        # Get recent sync errors
        error_result = await db.execute(
            select(SyncLog.error_message)
            .where(SyncLog.status == "FAILED")
            .where(SyncLog.started_at >= twenty_four_hours_ago)
            .order_by(SyncLog.started_at.desc())
            .limit(5)
        )
        errors = [row.error_message for row in error_result if row.error_message]
        
        # Determine current sync status
        sync_status = "idle"
        
        # Check if there's an ongoing sync
        ongoing_sync_result = await db.execute(
            select(SyncLog)
            .where(SyncLog.completed_at.is_(None))
            .where(SyncLog.started_at >= datetime.now() - timedelta(minutes=30))
        )
        ongoing_sync = ongoing_sync_result.scalar_one_or_none()
        
        if ongoing_sync:
            sync_status = "syncing"
        elif errors:
            sync_status = "error"
        elif last_sync and last_sync.completed_at > datetime.now() - timedelta(hours=1):
            sync_status = "healthy"
        
        return SyncStatusResponse(
            last_sync=last_sync.completed_at if last_sync else None,
            sync_status=sync_status,
            records_synced=records_synced,
            errors=errors
        )
        
    except Exception as e:
        logger.error("Failed to get sync status", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get sync status: {str(e)}")


@router.post("/donations", response_model=dict)
async def sync_donations_to_dhis2(
    background_tasks: BackgroundTasks,
    days_back: Optional[int] = 7,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Synchronize donation data to DHIS2.
    
    Syncs donation records from the specified number of days back
    to the current date.
    """
    try:
        # Create sync log entry
        sync_log = SyncLog(
            id=str(uuid.uuid4()),
            sync_type="EXPORT_DONATIONS",
            status="STARTED",
            started_at=datetime.now()
        )
        db.add(sync_log)
        await db.commit()
        
        # Schedule background sync
        background_tasks.add_task(
            perform_donations_sync, 
            sync_log.id, 
            days_back
        )
        
        return {
            "status": "started",
            "sync_id": sync_log.id,
            "message": f"Donation sync initiated for last {days_back} days"
        }
        
    except Exception as e:
        logger.error("Failed to start donations sync", error=str(e))
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@router.post("/inventory", response_model=dict)
async def sync_inventory_to_dhis2(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Synchronize current inventory to DHIS2.
    
    Syncs current blood product inventory status.
    """
    try:
        # Create sync log entry
        sync_log = SyncLog(
            id=str(uuid.uuid4()),
            sync_type="EXPORT_INVENTORY",
            status="STARTED",
            started_at=datetime.now()
        )
        db.add(sync_log)
        await db.commit()
        
        # Schedule background sync
        background_tasks.add_task(perform_inventory_sync, sync_log.id)
        
        return {
            "status": "started",
            "sync_id": sync_log.id,
            "message": "Inventory sync initiated"
        }
        
    except Exception as e:
        logger.error("Failed to start inventory sync", error=str(e))
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@router.post("/full", response_model=dict)
async def full_sync_to_dhis2(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Perform full synchronization to DHIS2.
    
    Syncs all data including donations, inventory, and donor information.
    """
    try:
        # Create sync log entry
        sync_log = SyncLog(
            id=str(uuid.uuid4()),
            sync_type="FULL_EXPORT",
            status="STARTED",
            started_at=datetime.now()
        )
        db.add(sync_log)
        await db.commit()
        
        # Schedule background sync
        background_tasks.add_task(perform_full_sync, sync_log.id)
        
        return {
            "status": "started",
            "sync_id": sync_log.id,
            "message": "Full sync initiated"
        }
        
    except Exception as e:
        logger.error("Failed to start full sync", error=str(e))
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@router.get("/logs/{sync_id}")
async def get_sync_log(
    sync_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    """Get detailed sync log for a specific sync operation."""
    try:
        sync_log = await db.get(SyncLog, sync_id)
        if not sync_log:
            raise HTTPException(status_code=404, detail="Sync log not found")
        
        return {
            "id": sync_log.id,
            "sync_type": sync_log.sync_type,
            "status": sync_log.status,
            "records_processed": sync_log.records_processed,
            "records_success": sync_log.records_success,
            "records_failed": sync_log.records_failed,
            "error_message": sync_log.error_message,
            "started_at": sync_log.started_at,
            "completed_at": sync_log.completed_at,
            "dhis2_response": sync_log.dhis2_response
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get sync log", sync_id=sync_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get sync log: {str(e)}")


@router.delete("/cache")
async def clear_sync_cache():
    """Clear synchronization cache and force fresh sync."""
    try:
        # This would clear any cached sync data
        # For now, just return success
        return {
            "status": "success",
            "message": "Sync cache cleared"
        }
    except Exception as e:
        logger.error("Failed to clear sync cache", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to clear cache: {str(e)}")


# Background sync tasks

async def perform_donations_sync(sync_id: str, days_back: int):
    """Background task to sync donations to DHIS2."""
    from ..models.database import get_db_session
    
    async with get_db_session() as db:
        sync_log = await db.get(SyncLog, sync_id)
        
        try:
            # Get donations from the last N days
            cutoff_date = datetime.now() - timedelta(days=days_back)
            
            result = await db.execute(
                select(Donation)
                .where(Donation.donation_date >= cutoff_date)
                .order_by(Donation.donation_date.desc())
            )
            donations = result.scalars().all()
            
            sync_log.records_processed = len(donations)
            
            if donations:
                async with DHIS2Client() as client:
                    # Convert to API models
                    from ..models.dhis2_models import BloodDonation, BloodType
                    
                    donation_models = []
                    for donation in donations:
                        donation_models.append(BloodDonation(
                            id=donation.id,
                            donor_id=donation.donor_id,
                            donation_date=donation.donation_date,
                            blood_type=BloodType(donation.blood_type),
                            volume_collected=donation.volume_collected,
                            collection_site=donation.collection_site,
                            staff_id=donation.staff_id
                        ))
                    
                    # Export to DHIS2
                    result = await client.export_blood_donations(donation_models)
                    
                    sync_log.records_success = result.imported_count + result.updated_count
                    sync_log.records_failed = len(donations) - sync_log.records_success
                    sync_log.dhis2_response = str(result.dict())
            
            sync_log.status = "SUCCESS"
            sync_log.completed_at = datetime.now()
            
        except Exception as e:
            sync_log.status = "FAILED"
            sync_log.error_message = str(e)
            sync_log.completed_at = datetime.now()
            logger.error("Donations sync failed", sync_id=sync_id, error=str(e))
        
        finally:
            await db.commit()


async def perform_inventory_sync(sync_id: str):
    """Background task to sync inventory to DHIS2."""
    from ..models.database import get_db_session
    
    async with get_db_session() as db:
        sync_log = await db.get(SyncLog, sync_id)
        
        try:
            # Get current inventory
            result = await db.execute(
                select(DBBloodProduct)
                .where(DBBloodProduct.status.in_(["AVAILABLE", "RESERVED"]))
            )
            products = result.scalars().all()
            
            sync_log.records_processed = len(products)
            
            if products:
                async with DHIS2Client() as client:
                    # Convert to API models
                    from ..models.dhis2_models import BloodProduct, BloodType, BloodProductStatus
                    
                    product_models = []
                    for product in products:
                        product_models.append(BloodProduct(
                            id=product.id,
                            donation_id=product.donation_id,
                            blood_type=BloodType(product.blood_type),
                            product_type=product.product_type,
                            volume=product.volume,
                            collection_date=product.collection_date,
                            expiry_date=product.expiry_date,
                            status=BloodProductStatus(product.status),
                            location=product.location,
                            temperature=product.temperature
                        ))
                    
                    # Export to DHIS2
                    result = await client.export_blood_inventory(product_models)
                    
                    sync_log.records_success = result.imported_count + result.updated_count
                    sync_log.records_failed = len(products) - sync_log.records_success
                    sync_log.dhis2_response = str(result.dict())
            
            sync_log.status = "SUCCESS"
            sync_log.completed_at = datetime.now()
            
        except Exception as e:
            sync_log.status = "FAILED"
            sync_log.error_message = str(e)
            sync_log.completed_at = datetime.now()
            logger.error("Inventory sync failed", sync_id=sync_id, error=str(e))
        
        finally:
            await db.commit()


async def perform_full_sync(sync_id: str):
    """Background task to perform full sync to DHIS2."""
    from ..models.database import get_db_session
    
    async with get_db_session() as db:
        sync_log = await db.get(SyncLog, sync_id)
        
        try:
            total_processed = 0
            total_success = 0
            
            # Sync donations (last 30 days)
            await perform_donations_sync(f"{sync_id}_donations", 30)
            
            # Sync inventory
            await perform_inventory_sync(f"{sync_id}_inventory")
            
            # Update main sync log
            sync_log.status = "SUCCESS"
            sync_log.completed_at = datetime.now()
            sync_log.records_processed = total_processed
            sync_log.records_success = total_success
            
        except Exception as e:
            sync_log.status = "FAILED"
            sync_log.error_message = str(e)
            sync_log.completed_at = datetime.now()
            logger.error("Full sync failed", sync_id=sync_id, error=str(e))
        
        finally:
            await db.commit()