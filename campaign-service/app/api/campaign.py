from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from app.database.database import get_db
from app.services.campaign import CampaignService
from app.schemas.campaign import CreateCampaignRequest, UpdateCampaignRequest, CampaignResponse, CampaignListResponse
import structlog

router = APIRouter(prefix="/campaigns", tags=["campaigns"])
logger = structlog.get_logger(__name__)


@router.post("", response_model=CampaignResponse, status_code=201)
async def create_campaign(
    campaign_data: CreateCampaignRequest,
    db: Session = Depends(get_db)
):
    """Create a new campaign"""
    try:
        campaign = await CampaignService.create_campaign(db=db, campaign_data=campaign_data)
        return campaign
    except Exception as e:
        logger.error("Failed to create campaign", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: int,
    db: Session = Depends(get_db)
):
    """Get a campaign by ID"""
    try:
        campaign = await CampaignService.get_campaign(db=db, campaign_id=campaign_id)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        return campaign
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get campaign", error=str(e), campaign_id=campaign_id)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("", response_model=CampaignListResponse)
async def get_all_campaigns(
    skip: int = Query(0, ge=0, description="Number of campaigns to skip"),
    limit: int = Query(100, ge=1, le=100, description="Number of campaigns to return"),
    db: Session = Depends(get_db)
):
    """Get all campaigns with pagination"""
    try:
        campaigns = await CampaignService.get_all_campaigns(db=db, skip=skip, limit=limit)
        
        return CampaignListResponse(
            campaigns=campaigns,
            total=len(campaigns)
        )
    except Exception as e:
        logger.error("Failed to get campaigns", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    campaign_id: int,
    campaign_data: UpdateCampaignRequest,
    db: Session = Depends(get_db)
):
    """Update an existing campaign"""
    try:
        campaign = await CampaignService.update_campaign(db=db, campaign_id=campaign_id, campaign_data=campaign_data)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        return campaign
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update campaign", error=str(e), campaign_id=campaign_id)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{campaign_id}", status_code=204)
async def delete_campaign(
    campaign_id: int,
    db: Session = Depends(get_db)
):
    """Delete a campaign by ID"""
    try:
        success = await CampaignService.delete_campaign(db=db, campaign_id=campaign_id)
        if not success:
            raise HTTPException(status_code=404, detail="Campaign not found")
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete campaign", error=str(e), campaign_id=campaign_id)
        raise HTTPException(status_code=500, detail="Internal server error")