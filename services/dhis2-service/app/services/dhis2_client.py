from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import structlog

from ..models.database import (
    Donation, 
    BloodProduct as DBBloodProduct, 
    Donor,
    ScreeningResult
)
from ..models.dhis2_models import (
    BloodDonation,
    BloodProduct,
    DonorDemographics,
    BloodType
)

logger = structlog.get_logger()


class DataProcessor:
    """Data processing service for blood bank operations."""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
    
    async def validate_donation_data(self, donations: List[BloodDonation]) -> Tuple[List[BloodDonation], List[str]]:
        """
        Validate donation data before processing.
        
        Args:
            donations: List of donation records to validate
            
        Returns:
            Tuple[List[BloodDonation], List[str]]: Valid donations and error messages
        """
        valid_donations = []
        errors = []
        
        for donation in donations:
            try:
                # Check if donor exists
                donor_result = await self.db.execute(
                    select(Donor).where(Donor.id == donation.donor_id)
                )
                donor = donor_result.scalar_one_or_none()
                
                if not donor:
                    errors.append(f"Donation {donation.id}: Donor {donation.donor_id} not found")
                    continue
                
                # Validate donation date (not in future, not too old)
                if donation.donation_date > datetime.now():
                    errors.append(f"Donation {donation.id}: Future donation date not allowed")
                    continue
                
                if donation.donation_date < datetime.now() - timedelta(days=365):
                    errors.append(f"Donation {donation.id}: Donation date too old (>1 year)")
                    continue
                
                # Validate volume (typical range 300-500ml)
                if not 300 <= donation.volume_collected <= 500:
                    errors.append(f"Donation {donation.id}: Invalid volume {donation.volume_collected}ml")
                    continue
                
                # Check for duplicate donations (same donor, same day)
                existing_result = await self.db.execute(
                    select(Donation).where(
                        Donation.donor_id == donation.donor_id,
                        func.date(Donation.donation_date) == donation.donation_date.date()
                    )
                )
                existing_donation = existing_result.scalar_one_or_none()
                
                if existing_donation and existing_donation.id != donation.id:
                    errors.append(f"Donation {donation.id}: Duplicate donation for donor {donation.donor_id} on {donation.donation_date.date()}")
                    continue
                
                valid_donations.append(donation)
                
            except Exception as e:
                errors.append(f"Donation {donation.id}: Validation error - {str(e)}")
                logger.error("Donation validation error", donation_id=donation.id, error=str(e))
        
        return valid_donations, errors
    
    async def validate_blood_product_data(self, products: List[BloodProduct]) -> Tuple[List[BloodProduct], List[str]]:
        """
        Validate blood product data before processing.
        
        Args:
            products: List of blood product records to validate
            
        Returns:
            Tuple[List[BloodProduct], List[str]]: Valid products and error messages
        """
        valid_products = []
        errors = []
        
        for product in products:
            try:
                # Check if source donation exists
                donation_result = await self.db.execute(
                    select(Donation).where(Donation.id == product.donation_id)
                )
                donation = donation_result.scalar_one_or_none()
                
                if not donation:
                    errors.append(f"Product {product.id}: Source donation {product.donation_id} not found")
                    continue
                
                # Validate expiry date
                if product.expiry_date <= product.collection_date:
                    errors.append(f"Product {product.id}: Expiry date must be after collection date")
                    continue
                
                # Validate blood type consistency
                if product.blood_type != BloodType(donation.blood_type):
                    errors.append(f"Product {product.id}: Blood type mismatch with source donation")
                    continue
                
                # Validate volume (should not exceed donation volume)
                if product.volume > donation.volume_collected:
                    errors.append(f"Product {product.id}: Volume exceeds source donation volume")
                    continue
                
                # Validate temperature for refrigerated products
                if product.temperature is not None:
                    if product.product_type.lower() in ["whole blood", "red blood cells"]:
                        if not 2 <= product.temperature <= 6:
                            errors.append(f"Product {product.id}: Invalid temperature {product.temperature}°C for {product.product_type}")
                            continue
                    elif product.product_type.lower() == "plasma":
                        if product.temperature > -18:
                            errors.append(f"Product {product.id}: Plasma must be stored below -18°C")
                            continue
                
                valid_products.append(product)
                
            except Exception as e:
                errors.append(f"Product {product.id}: Validation error - {str(e)}")
                logger.error("Product validation error", product_id=product.id, error=str(e))
        
        return valid_products, errors
    
    async def get_inventory_analytics(self, days_back: int = 30) -> Dict[str, Any]:
        """
        Generate inventory analytics for the dashboard.
        
        Args:
            days_back: Number of days to look back for analytics
            
        Returns:
            Dict[str, Any]: Analytics data
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days_back)
            
            # Blood type distribution
            blood_type_result = await self.db.execute(
                select(
                    DBBloodProduct.blood_type,
                    func.count(DBBloodProduct.id).label('count')
                ).where(
                    DBBloodProduct.status == 'AVAILABLE'
                ).group_by(DBBloodProduct.blood_type)
            )
            
            blood_type_distribution = {
                row.blood_type: row.count 
                for row in blood_type_result
            }
            
            # Expiring products (next 7 days)
            expiring_result = await self.db.execute(
                select(func.count(DBBloodProduct.id)).where(
                    DBBloodProduct.status == 'AVAILABLE',
                    DBBloodProduct.expiry_date <= datetime.now() + timedelta(days=7)
                )
            )
            expiring_count = expiring_result.scalar() or 0
            
            # Recent donations
            recent_donations_result = await self.db.execute(
                select(func.count(Donation.id)).where(
                    Donation.donation_date >= cutoff_date
                )
            )
            recent_donations = recent_donations_result.scalar() or 0
            
            # Average donation volume
            avg_volume_result = await self.db.execute(
                select(func.avg(Donation.volume_collected)).where(
                    Donation.donation_date >= cutoff_date
                )
            )
            avg_volume = avg_volume_result.scalar() or 0
            
            # Products by status
            status_result = await self.db.execute(
                select(
                    DBBloodProduct.status,
                    func.count(DBBloodProduct.id).label('count')
                ).group_by(DBBloodProduct.status)
            )
            
            status_distribution = {
                row.status: row.count 
                for row in status_result
            }
            
            return {
                "blood_type_distribution": blood_type_distribution,
                "status_distribution": status_distribution,
                "expiring_products": expiring_count,
                "recent_donations": recent_donations,
                "average_donation_volume": float(avg_volume),
                "analysis_period_days": days_back,
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error("Failed to generate inventory analytics", error=str(e))
            return {
                "error": "Failed to generate analytics",
                "generated_at": datetime.now().isoformat()
            }
    
    async def detect_anomalies(self) -> Dict[str, Any]:
        """
        Detect anomalies in blood bank data.
        
        Returns:
            Dict[str, Any]: Detected anomalies
        """
        anomalies = {
            "expired_products": [],
            "low_stock_types": [],
            "unusual_donations": [],
            "temperature_violations": []
        }
        
        try:
            # Find expired products still marked as available
            expired_result = await self.db.execute(
                select(DBBloodProduct).where(
                    DBBloodProduct.status == 'AVAILABLE',
                    DBBloodProduct.expiry_date < datetime.now()
                )
            )
            
            for product in expired_result.scalars():
                anomalies["expired_products"].append({
                    "product_id": product.id,
                    "blood_type": product.blood_type,
                    "expiry_date": product.expiry_date.isoformat(),
                    "days_expired": (datetime.now() - product.expiry_date).days
                })
            
            # Find blood types with low stock (< 5 units)
            stock_result = await self.db.execute(
                select(
                    DBBloodProduct.blood_type,
                    func.count(DBBloodProduct.id).label('count')
                ).where(
                    DBBloodProduct.status == 'AVAILABLE'
                ).group_by(DBBloodProduct.blood_type)
                .having(func.count(DBBloodProduct.id) < 5)
            )
            
            for row in stock_result:
                anomalies["low_stock_types"].append({
                    "blood_type": row.blood_type,
                    "available_count": row.count
                })
            
            # Find unusual donation volumes (outside 2 standard deviations)
            recent_donations_result = await self.db.execute(
                select(Donation.volume_collected).where(
                    Donation.donation_date >= datetime.now() - timedelta(days=30)
                )
            )
            
            volumes = [row[0] for row in recent_donations_result]
            if volumes:
                mean_volume = np.mean(volumes)
                std_volume = np.std(volumes)
                
                unusual_result = await self.db.execute(
                    select(Donation).where(
                        Donation.donation_date >= datetime.now() - timedelta(days=30),
                        (Donation.volume_collected < mean_volume - 2 * std_volume) |
                        (Donation.volume_collected > mean_volume + 2 * std_volume)
                    )
                )
                
                for donation in unusual_result.scalars():
                    anomalies["unusual_donations"].append({
                        "donation_id": donation.id,
                        "donor_id": donation.donor_id,
                        "volume": donation.volume_collected,
                        "date": donation.donation_date.isoformat(),
                        "deviation": abs(donation.volume_collected - mean_volume) / std_volume
                    })
            
            # Find temperature violations
            temp_violations_result = await self.db.execute(
                select(DBBloodProduct).where(
                    DBBloodProduct.temperature.isnot(None),
                    (
                        (DBBloodProduct.product_type.in_(["Whole Blood", "Red Blood Cells"]) & 
                         ((DBBloodProduct.temperature < 2) | (DBBloodProduct.temperature > 6))) |
                        (DBBloodProduct.product_type == "Plasma" & 
                         (DBBloodProduct.temperature > -18))
                    )
                )
            )
            
            for product in temp_violations_result.scalars():
                anomalies["temperature_violations"].append({
                    "product_id": product.id,
                    "product_type": product.product_type,
                    "current_temperature": product.temperature,
                    "location": product.location
                })
            
        except Exception as e:
            logger.error("Failed to detect anomalies", error=str(e))
            anomalies["error"] = str(e)
        
        return anomalies
    
    async def generate_quality_report(self) -> Dict[str, Any]:
        """
        Generate a data quality report.
        
        Returns:
            Dict[str, Any]: Quality report
        """
        report = {
            "data_completeness": {},
            "data_consistency": {},
            "data_accuracy": {},
            "generated_at": datetime.now().isoformat()
        }
        
        try:
            # Data completeness checks
            total_donors_result = await self.db.execute(select(func.count(Donor.id)))
            total_donors = total_donors_result.scalar()
            
            donors_with_contact_result = await self.db.execute(
                select(func.count(Donor.id)).where(Donor.contact_info.isnot(None))
            )
            donors_with_contact = donors_with_contact_result.scalar()
            
            report["data_completeness"]["donor_contact_info"] = {
                "total": total_donors,
                "complete": donors_with_contact,
                "percentage": (donors_with_contact / total_donors * 100) if total_donors > 0 else 0
            }
            
            # Blood products with temperature data
            total_products_result = await self.db.execute(select(func.count(DBBloodProduct.id)))
            total_products = total_products_result.scalar()
            
            products_with_temp_result = await self.db.execute(
                select(func.count(DBBloodProduct.id)).where(DBBloodProduct.temperature.isnot(None))
            )
            products_with_temp = products_with_temp_result.scalar()
            
            report["data_completeness"]["product_temperature"] = {
                "total": total_products,
                "complete": products_with_temp,
                "percentage": (products_with_temp / total_products * 100) if total_products > 0 else 0
            }
            
            # Data consistency checks
            inconsistent_blood_types_result = await self.db.execute(
                select(func.count(DBBloodProduct.id))
                .select_from(
                    DBBloodProduct.__table__.join(Donation.__table__)
                )
                .where(DBBloodProduct.blood_type != Donation.blood_type)
            )
            inconsistent_blood_types = inconsistent_blood_types_result.scalar()
            
            report["data_consistency"]["blood_type_consistency"] = {
                "total_products": total_products,
                "inconsistent": inconsistent_blood_types,
                "percentage": (inconsistent_blood_types / total_products * 100) if total_products > 0 else 0
            }
            
        except Exception as e:
            logger.error("Failed to generate quality report", error=str(e))
            report["error"] = str(e)
        
        return report