from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import timedelta
import sys
from app.models.campaign import Campaign
from app.schemas.campaign import CreateCampaignRequest, UpdateCampaignRequest, CampaignResponse
from app.cache.redis import redis_cache
from app.core.circuit_breaker import db_circuit_breaker, CircuitBreakerError
import structlog
import json

logger = structlog.get_logger(__name__)


class CampaignService:
    """Business logic for campaign operations"""

    @staticmethod
    async def create_campaign(db: Session, campaign_data: CreateCampaignRequest) -> CampaignResponse:
        """Create a new campaign with circuit breaker protection"""
        try:
            print(f"[CAMPAIGN SERVICE] 🔄 Creating campaign: {campaign_data.title}")
            sys.stdout.flush()
            
            # Create with circuit breaker protection
            def db_create():
                print(f"[CAMPAIGN SERVICE] 💾 Saving to database...")
                sys.stdout.flush()
                
                db_campaign = Campaign(
                    title=campaign_data.title,
                    name=campaign_data.name,
                    description=campaign_data.description,
                    start_date=campaign_data.start_date,
                    end_date=campaign_data.end_date,
                    is_active=campaign_data.is_active
                )
                
                db.add(db_campaign)
                db.commit()
                db.refresh(db_campaign)
                return db_campaign
            
            try:
                db_campaign = await db_circuit_breaker.call(db_create)
            except CircuitBreakerError:
                logger.warning("Circuit breaker open, service temporarily unavailable")
                print(f"[CAMPAIGN SERVICE] ⚠️  Circuit breaker open")
                sys.stdout.flush()
                raise Exception("Service temporarily unavailable")
            
            logger.info("Campaign created successfully", campaign_id=db_campaign.id, title=db_campaign.title)
            print(f"[CAMPAIGN SERVICE] ✅ Created campaign ID: {db_campaign.id}")
            sys.stdout.flush()
            
            return CampaignResponse(
                id=db_campaign.id,
                title=db_campaign.title,
                name=db_campaign.name,
                description=db_campaign.description,
                start_date=db_campaign.start_date,
                end_date=db_campaign.end_date,
                is_active=db_campaign.is_active,
                created_at=db_campaign.created_at,
                updated_at=db_campaign.updated_at
            )
            
        except Exception as e:
            db.rollback()
            logger.error("Failed to create campaign", error=str(e), campaign_data=campaign_data.dict())
            raise Exception(f"Failed to create campaign: {str(e)}")

    @staticmethod
    async def get_campaign(db: Session, campaign_id: int) -> Optional[CampaignResponse]:
        """Get a campaign by ID with circuit breaker"""
        try:
            print(f"[CAMPAIGN SERVICE] 🔍 Fetching campaign ID: {campaign_id}")
            sys.stdout.flush()
            
            # Get from database with circuit breaker protection
            def db_query():
                return db.query(Campaign).filter(Campaign.id == campaign_id).first()
            
            try:
                db_campaign = await db_circuit_breaker.call(db_query)
            except CircuitBreakerError:
                logger.warning("Circuit breaker open, service temporarily unavailable", campaign_id=campaign_id)
                print(f"[CAMPAIGN SERVICE] ⚠️  Circuit breaker open for campaign {campaign_id}")
                sys.stdout.flush()
                raise Exception("Service temporarily unavailable")
            
            if not db_campaign:
                logger.warning("Campaign not found", campaign_id=campaign_id)
                print(f"[CAMPAIGN SERVICE] ⚠️  Campaign {campaign_id} not found")
                sys.stdout.flush()
                return None
            
            # Create response object
            campaign_response = CampaignResponse(
                id=db_campaign.id,
                title=db_campaign.title,
                name=db_campaign.name,
                description=db_campaign.description,
                start_date=db_campaign.start_date,
                end_date=db_campaign.end_date,
                is_active=db_campaign.is_active,
                created_at=db_campaign.created_at,
                updated_at=db_campaign.updated_at
            )
            
            logger.info("Campaign retrieved successfully from database", campaign_id=campaign_id)
            print(f"[CAMPAIGN SERVICE] ✅ Retrieved campaign {campaign_id}: {db_campaign.title} (active: {db_campaign.is_active})")
            sys.stdout.flush()
            return campaign_response
            
        except Exception as e:
            logger.error("Failed to get campaign", error=str(e), campaign_id=campaign_id)
            raise Exception(f"Failed to get campaign: {str(e)}")

    @staticmethod
    async def get_all_campaigns(db: Session, skip: int = 0, limit: int = 100) -> List[CampaignResponse]:
        """Get all campaigns with pagination and circuit breaker protection"""
        try:
            # Get from database with circuit breaker protection
            def db_query():
                return db.query(Campaign).offset(skip).limit(limit).all()
            
            try:
                db_campaigns = await db_circuit_breaker.call(db_query)
            except CircuitBreakerError:
                logger.warning("Circuit breaker open, service temporarily unavailable")
                raise Exception("Service temporarily unavailable")
            
            campaigns = [
                CampaignResponse(
                    id=campaign.id,
                    title=campaign.title,
                    name=campaign.name,
                    description=campaign.description,
                    start_date=campaign.start_date,
                    end_date=campaign.end_date,
                    is_active=campaign.is_active,
                    created_at=campaign.created_at,
                    updated_at=campaign.updated_at
                )
                for campaign in db_campaigns
            ]
            
            logger.info("Campaigns retrieved successfully", count=len(campaigns))
            return campaigns
            
        except Exception as e:
            logger.error("Failed to get campaigns", error=str(e))
            raise Exception(f"Failed to get campaigns: {str(e)}")

    @staticmethod
    async def update_campaign(db: Session, campaign_id: int, campaign_data: UpdateCampaignRequest) -> Optional[CampaignResponse]:
        """Update an existing campaign with circuit breaker"""
        try:
            # Update with circuit breaker protection
            def db_update():
                db_campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
                
                if not db_campaign:
                    return None
                
                # Update fields if provided
                if campaign_data.title is not None:
                    db_campaign.title = campaign_data.title
                if campaign_data.name is not None:
                    db_campaign.name = campaign_data.name
                if campaign_data.description is not None:
                    db_campaign.description = campaign_data.description
                if campaign_data.start_date is not None:
                    db_campaign.start_date = campaign_data.start_date
                if campaign_data.end_date is not None:
                    db_campaign.end_date = campaign_data.end_date
                if campaign_data.is_active is not None:
                    db_campaign.is_active = campaign_data.is_active
                
                db.commit()
                db.refresh(db_campaign)
                return db_campaign
            
            try:
                db_campaign = await db_circuit_breaker.call(db_update)
            except CircuitBreakerError:
                logger.warning("Circuit breaker open, service temporarily unavailable", campaign_id=campaign_id)
                raise Exception("Service temporarily unavailable")
            
            if not db_campaign:
                logger.warning("Campaign not found for update", campaign_id=campaign_id)
                return None
            
            logger.info("Campaign updated successfully", campaign_id=campaign_id)
            
            return CampaignResponse(
                id=db_campaign.id,
                campaign_id=db_campaign.campaign_id,
                title=db_campaign.title,
                name=db_campaign.name,
                description=db_campaign.description,
                start_date=db_campaign.start_date,
                end_date=db_campaign.end_date,
                is_active=db_campaign.is_active,
                created_at=db_campaign.created_at,
                updated_at=db_campaign.updated_at
            )
            
        except Exception as e:
            db.rollback()
            logger.error("Failed to update campaign", error=str(e), campaign_id=campaign_id)
            raise Exception(f"Failed to update campaign: {str(e)}")

    @staticmethod
    async def delete_campaign(db: Session, campaign_id: int) -> bool:
        """Delete a campaign by ID with circuit breaker"""
        try:
            # Delete with circuit breaker protection
            def db_delete():
                db_campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
                
                if not db_campaign:
                    return False
                
                db.delete(db_campaign)
                db.commit()
                return True
            
            try:
                result = await db_circuit_breaker.call(db_delete)
            except CircuitBreakerError:
                logger.warning("Circuit breaker open, service temporarily unavailable", campaign_id=campaign_id)
                raise Exception("Service temporarily unavailable")
            
            if not result:
                logger.warning("Campaign not found for deletion", campaign_id=campaign_id)
                return False
            
            logger.info("Campaign deleted successfully", campaign_id=campaign_id)
            return True
            
        except Exception as e:
            db.rollback()
            logger.error("Failed to delete campaign", error=str(e), campaign_id=campaign_id)
            raise Exception(f"Failed to delete campaign: {str(e)}")