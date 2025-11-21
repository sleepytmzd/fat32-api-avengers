from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
import sys
from app.database.database import get_db
from app.services.donation import DonationService
from app.services.grpc_client import CampaignGRPCClient
from app.schemas.donation import CreateDonationRequest, UpdateDonationRequest, DonationResponse, DonationListResponse
from app.kafka.producer import get_kafka_producer, KafkaProducer
import structlog

router = APIRouter(prefix="/donations", tags=["donations"])
logger = structlog.get_logger(__name__)


@router.post("", response_model=DonationResponse, status_code=201)
async def create_donation(
    donation_data: CreateDonationRequest,
    db: Session = Depends(get_db),
    kafka_producer: KafkaProducer = Depends(get_kafka_producer)
):
    """
    Create a new donation with gRPC campaign validation
    Flow:
    1. Check campaign is active via gRPC
    2. Create donation in database with INITIATED status
    3. Return donation response (payment processing will be handled separately)
    """
    try:
        print(f"\n[API] 📥 POST /donations - user: {donation_data.user_id}, campaign: {donation_data.campaign_id}, amount: {donation_data.amount}")
        sys.stdout.flush()
        
        logger.info(
            "Creating donation",
            user_id=donation_data.user_id,
            campaign_id=donation_data.campaign_id,
            amount=donation_data.amount
        )
        
        # Step 1: Check campaign is active via gRPC
        print(f"[API] 🔍 Validating campaign {donation_data.campaign_id} via gRPC...")
        sys.stdout.flush()
        
        async with CampaignGRPCClient() as grpc_client:
            campaign_status = await grpc_client.check_campaign_active(donation_data.campaign_id)
            
            if not campaign_status["is_active"]:
                logger.warning(
                    "Campaign not active",
                    campaign_id=donation_data.campaign_id,
                    message=campaign_status["message"]
                )
                print(f"[API] ❌ Campaign {donation_data.campaign_id} validation failed: {campaign_status['message']}")
                sys.stdout.flush()
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "Campaign not available for donations",
                        "message": campaign_status["message"],
                        "campaign_id": donation_data.campaign_id
                    }
                )
            
            logger.info(
                "Campaign validation successful",
                campaign_id=donation_data.campaign_id,
                message=campaign_status["message"]
            )
            print(f"[API] ✅ Campaign {donation_data.campaign_id} is active")
            sys.stdout.flush()
        
        # Step 2: Create donation in database with INITIATED status
        print(f"[API] 💾 Creating donation in database...")
        sys.stdout.flush()
        
        donation, db_donation = DonationService.create_donation(
            db=db, 
            donation_data=donation_data
        )
        
        # Step 3: Publish donation_created event to Kafka
        print(f"[API] 📤 Publishing donation_created event to Kafka...")
        sys.stdout.flush()
        
        await kafka_producer.publish_donation_created({
            "id": donation.id,
            "user_id": donation.user_id,
            "campaign_id": donation.campaign_id,
            "amount": donation.amount,
            "status": donation.status.value,
            "payment_method": donation.payment_method,
            "is_anonymous": donation.is_anonymous,
            "message": donation.message,
            "created_at": donation.created_at.isoformat()
        })
        
        logger.info(
            "Donation created successfully",
            donation_id=donation.id,
            user_id=donation_data.user_id,
            campaign_id=donation_data.campaign_id,
            amount=donation_data.amount,
            status=donation.status
        )
        print(f"[API] ✅ Donation flow complete - ID: {donation.id}, Status: {donation.status}\n")
        sys.stdout.flush()
        
        return donation
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to create donation", 
            error=str(e),
            user_id=donation_data.user_id,
            campaign_id=donation_data.campaign_id
        )
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{donation_id}", response_model=DonationResponse)
def get_donation(
    donation_id: int,
    db: Session = Depends(get_db)
):
    """Get a donation by ID"""
    try:
        donation = DonationService.get_donation(db=db, donation_id=donation_id)
        if not donation:
            raise HTTPException(status_code=404, detail="Donation not found")
        return donation
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get donation", error=str(e), donation_id=donation_id)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/user/{user_id}", response_model=DonationListResponse)
def get_donations_by_user(
    user_id: str,
    skip: int = Query(0, ge=0, description="Number of donations to skip"),
    limit: int = Query(100, ge=1, le=100, description="Number of donations to return"),
    db: Session = Depends(get_db)
):
    """Get donations by user ID with pagination"""
    try:
        donations = DonationService.get_donations_by_user(db=db, user_id=user_id, skip=skip, limit=limit)
        
        return DonationListResponse(
            donations=donations,
            total=len(donations)
        )
    except Exception as e:
        logger.error("Failed to get donations by user", error=str(e), user_id=user_id)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("", response_model=DonationListResponse)
def get_all_donations(
    skip: int = Query(0, ge=0, description="Number of donations to skip"),
    limit: int = Query(100, ge=1, le=100, description="Number of donations to return"),
    db: Session = Depends(get_db)
):
    """Get all donations with pagination"""
    try:
        donations = DonationService.get_all_donations(db=db, skip=skip, limit=limit)
        
        return DonationListResponse(
            donations=donations,
            total=len(donations)
        )
    except Exception as e:
        logger.error("Failed to get all donations", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")