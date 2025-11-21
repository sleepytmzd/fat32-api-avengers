from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.donation import Donation, DonationStatus
from app.schemas.donation import CreateDonationRequest, UpdateDonationRequest, DonationResponse
import structlog

logger = structlog.get_logger(__name__)


class DonationService:
    """Business logic for donation operations"""

    @staticmethod
    def create_donation(db: Session, donation_data: CreateDonationRequest) -> tuple[DonationResponse, Donation]:
        """Create a new donation with INITIATED status"""
        try:
            # Create new donation instance
            db_donation = Donation(
                user_id=donation_data.user_id,
                campaign_id=donation_data.campaign_id,
                amount=donation_data.amount,
                payment_method=donation_data.payment_method,
                donor_name=donation_data.donor_name,
                donor_email=donation_data.donor_email,
                message=donation_data.message,
                is_anonymous=donation_data.is_anonymous,
                status=DonationStatus.INITIATED
            )
            
            # Add to database
            db.add(db_donation)
            db.commit()
            db.refresh(db_donation)
            
            logger.info("Donation created successfully", 
                       donation_id=db_donation.id, 
                       user_id=db_donation.user_id, 
                       campaign_id=db_donation.campaign_id,
                       amount=db_donation.amount)
            
            response = DonationResponse(
                id=db_donation.id,
                user_id=db_donation.user_id,
                campaign_id=db_donation.campaign_id,
                amount=db_donation.amount,
                status=db_donation.status.value,
                payment_method=db_donation.payment_method,
                payment_id=db_donation.payment_id,
                donor_name=db_donation.donor_name,
                donor_email=db_donation.donor_email,
                message=db_donation.message,
                is_anonymous=db_donation.is_anonymous,
                created_at=db_donation.created_at,
                updated_at=db_donation.updated_at
            )
            
            return response, db_donation  # Return both response and db_donation for Kafka publishing
            
        except Exception as e:
            db.rollback()
            logger.error("Failed to create donation", error=str(e), donation_data=donation_data.dict())
            raise Exception(f"Failed to create donation: {str(e)}")

    @staticmethod
    def get_donation(db: Session, donation_id: int) -> Optional[DonationResponse]:
        """Get a donation by ID"""
        try:
            db_donation = db.query(Donation).filter(Donation.id == donation_id).first()
            
            if not db_donation:
                logger.warning("Donation not found", donation_id=donation_id)
                return None
            
            logger.info("Donation retrieved successfully", donation_id=donation_id)
            
            return DonationResponse(
                id=db_donation.id,
                user_id=db_donation.user_id,
                campaign_id=db_donation.campaign_id,
                amount=db_donation.amount,
                status=db_donation.status.value,
                payment_method=db_donation.payment_method,
                payment_id=db_donation.payment_id,
                donor_name=db_donation.donor_name,
                donor_email=db_donation.donor_email,
                message=db_donation.message,
                is_anonymous=db_donation.is_anonymous,
                created_at=db_donation.created_at,
                updated_at=db_donation.updated_at
            )
            
        except Exception as e:
            logger.error("Failed to get donation", error=str(e), donation_id=donation_id)
            raise Exception(f"Failed to get donation: {str(e)}")

    @staticmethod
    def get_donations_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[DonationResponse]:
        """Get donations by user ID with pagination"""
        try:
            db_donations = db.query(Donation).filter(Donation.user_id == user_id).offset(skip).limit(limit).all()
            
            donations = [
                DonationResponse(
                    id=donation.id,
                    user_id=donation.user_id,
                    campaign_id=donation.campaign_id,
                    amount=donation.amount,
                    status=donation.status.value,
                    payment_method=donation.payment_method,
                    payment_id=donation.payment_id,
                    donor_name=donation.donor_name,
                    donor_email=donation.donor_email,
                    message=donation.message,
                    is_anonymous=donation.is_anonymous,
                    created_at=donation.created_at,
                    updated_at=donation.updated_at
                )
                for donation in db_donations
            ]
            
            logger.info("Donations retrieved successfully", user_id=user_id, count=len(donations))
            
            return donations
            
        except Exception as e:
            logger.error("Failed to get donations", error=str(e), user_id=user_id)
            raise Exception(f"Failed to get donations: {str(e)}")

    @staticmethod
    def get_all_donations(db: Session, skip: int = 0, limit: int = 100) -> List[DonationResponse]:
        """Get all donations with pagination"""
        try:
            db_donations = db.query(Donation).offset(skip).limit(limit).all()
            
            donations = [
                DonationResponse(
                    id=donation.id,
                    user_id=donation.user_id,
                    campaign_id=donation.campaign_id,
                    amount=donation.amount,
                    status=donation.status.value,
                    payment_method=donation.payment_method,
                    payment_id=donation.payment_id,
                    donor_name=donation.donor_name,
                    donor_email=donation.donor_email,
                    message=donation.message,
                    is_anonymous=donation.is_anonymous,
                    created_at=donation.created_at,
                    updated_at=donation.updated_at
                )
                for donation in db_donations
            ]
            
            logger.info("All donations retrieved successfully", count=len(donations))
            
            return donations
            
        except Exception as e:
            logger.error("Failed to get all donations", error=str(e))
            raise Exception(f"Failed to get all donations: {str(e)}")

    @staticmethod
    def update_donation_status(db: Session, donation_id: int, update_data: UpdateDonationRequest) -> Optional[DonationResponse]:
        """Update donation status and payment info"""
        try:
            db_donation = db.query(Donation).filter(Donation.id == donation_id).first()
            
            if not db_donation:
                logger.warning("Donation not found for status update", donation_id=donation_id)
                return None
            
            # Update fields if provided
            if update_data.status:
                db_donation.status = DonationStatus(update_data.status)
            if update_data.payment_id:
                db_donation.payment_id = update_data.payment_id
            
            db.commit()
            db.refresh(db_donation)
            
            logger.info("Donation updated successfully", 
                       donation_id=donation_id, 
                       new_status=db_donation.status.value if update_data.status else None)
            
            return DonationResponse(
                id=db_donation.id,
                user_id=db_donation.user_id,
                campaign_id=db_donation.campaign_id,
                amount=db_donation.amount,
                status=db_donation.status.value,
                payment_method=db_donation.payment_method,
                payment_id=db_donation.payment_id,
                donor_name=db_donation.donor_name,
                donor_email=db_donation.donor_email,
                message=db_donation.message,
                is_anonymous=db_donation.is_anonymous,
                created_at=db_donation.created_at,
                updated_at=db_donation.updated_at
            )
            
        except Exception as e:
            db.rollback()
            logger.error("Failed to update donation", error=str(e), donation_id=donation_id)
            raise Exception(f"Failed to update donation: {str(e)}")
