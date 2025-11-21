"""
gRPC Campaign Service Client
Based on: https://ssojet.com/grpc/use-grpc-in-fastapi/
"""

import grpc
import structlog
from typing import Dict, Any
from fastapi import HTTPException

# Import generated gRPC classes
from app.grpc.campaign import campaign_pb2, campaign_pb2_grpc
from app.core.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()

class CampaignGRPCClient:
    """gRPC client for Campaign Service communication"""
    
    def __init__(self):
        # gRPC server address (campaign service)
        self.server_address = getattr(settings, 'campaign_grpc_url', 'campaign-service:50051')
        self.channel = None
        self.stub = None
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.channel = grpc.aio.insecure_channel(self.server_address)
        self.stub = campaign_pb2_grpc.CampaignServiceStub(self.channel)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.channel:
            await self.channel.close()
    
    async def check_campaign_active(self, campaign_id: int) -> Dict[str, Any]:
        """
        Check if campaign is active and accepting donations
        Returns: dict with is_active (bool), message (str), end_date (str)
        """
        try:
            logger.info(
                "Checking campaign active status via gRPC",
                campaign_id=campaign_id,
                server=self.server_address
            )
            
            # Create gRPC request
            request = campaign_pb2.CheckCampaignActiveRequest(
                campaign_id=campaign_id
            )
            
            # Make gRPC call
            response = await self.stub.CheckCampaignActive(request)
            
            logger.info(
                "Campaign active status checked",
                campaign_id=campaign_id,
                is_active=response.is_active,
                message=response.message
            )
            
            return {
                "is_active": response.is_active,
                "message": response.message,
                "end_date": response.end_date
            }
            
        except grpc.RpcError as e:
            logger.error(
                "gRPC call failed - CheckCampaignActive",
                campaign_id=campaign_id,
                error_code=e.code().name,
                error_details=e.details(),
                server=self.server_address
            )
            
            if e.code() == grpc.StatusCode.UNAVAILABLE:
                raise HTTPException(
                    status_code=503,
                    detail="Campaign service unavailable"
                )
            elif e.code() == grpc.StatusCode.NOT_FOUND:
                raise HTTPException(
                    status_code=404,
                    detail="Campaign not found"
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"Campaign service error: {e.details()}"
                )
        except Exception as e:
            logger.error(
                "Unexpected error in gRPC call",
                campaign_id=campaign_id,
                error=str(e)
            )
            raise HTTPException(
                status_code=500,
                detail="Internal server error"
            )
    
    async def get_campaign(self, campaign_id: int) -> Dict[str, Any]:
        """
        Get campaign details
        Returns: campaign data dictionary
        """
        try:
            logger.info(
                "Getting campaign details via gRPC",
                campaign_id=campaign_id,
                server=self.server_address
            )
            
            # Create gRPC request
            request = campaign_pb2.GetCampaignRequest(campaign_id=campaign_id)
            
            # Make gRPC call
            response = await self.stub.GetCampaign(request)
            
            # Convert gRPC response to dictionary
            campaign_data = {
                "id": response.id,
                "campaign_id": response.campaign_id,
                "title": response.title,
                "name": response.name,
                "description": response.description,
                "start_date": response.start_date,
                "end_date": response.end_date,
                "is_active": response.is_active,
                "created_at": response.created_at,
                "updated_at": response.updated_at
            }
            
            logger.info(
                "Campaign details retrieved via gRPC",
                campaign_id=campaign_id,
                campaign_title=response.title,
                is_active=response.is_active
            )
            
            return campaign_data
            
        except grpc.RpcError as e:
            logger.error(
                "gRPC call failed - GetCampaign",
                campaign_id=campaign_id,
                error_code=e.code().name,
                error_details=e.details(),
                server=self.server_address
            )
            
            if e.code() == grpc.StatusCode.UNAVAILABLE:
                raise HTTPException(
                    status_code=503,
                    detail="Campaign service unavailable"
                )
            elif e.code() == grpc.StatusCode.NOT_FOUND:
                raise HTTPException(
                    status_code=404,
                    detail="Campaign not found"
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"Campaign service error: {e.details()}"
                )
        except Exception as e:
            logger.error(
                "Unexpected error in gRPC call",
                campaign_id=campaign_id,
                error=str(e)
            )
            raise HTTPException(
                status_code=500,
                detail="Internal server error"
            )

# Synchronous version for non-async contexts
class CampaignGRPCClientSync:
    """Synchronous gRPC client for Campaign Service"""
    
    def __init__(self):
        self.server_address = getattr(settings, 'campaign_grpc_url', 'campaign-service:50051')
        self.channel = None
        self.stub = None
    
    def __enter__(self):
        """Context manager entry"""
        self.channel = grpc.insecure_channel(self.server_address)
        self.stub = campaign_pb2_grpc.CampaignServiceStub(self.channel)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self.channel:
            self.channel.close()
    
    def check_campaign_active(self, campaign_id: int) -> Dict[str, Any]:
        """Synchronous version of check_campaign_active"""
        try:
            request = campaign_pb2.CheckCampaignActiveRequest(
                campaign_id=campaign_id
            )
            
            response = self.stub.CheckCampaignActive(request)
            return {
                "is_active": response.is_active,
                "message": response.message,
                "end_date": response.end_date
            }
            
        except grpc.RpcError as e:
            logger.error(
                "gRPC call failed - CheckCampaignActive (sync)",
                campaign_id=campaign_id,
                error=str(e)
            )
            if e.code() == grpc.StatusCode.UNAVAILABLE:
                raise HTTPException(status_code=503, detail="Campaign service unavailable")
            elif e.code() == grpc.StatusCode.NOT_FOUND:
                raise HTTPException(status_code=404, detail="Campaign not found")
            else:
                raise HTTPException(status_code=500, detail="Campaign service error")
    
    def get_campaign(self, campaign_id: int) -> Dict[str, Any]:
        """Synchronous version of get_campaign"""
        try:
            request = campaign_pb2.GetCampaignRequest(campaign_id=campaign_id)
            response = self.stub.GetCampaign(request)
            
            return {
                "id": response.id,
                "campaign_id": response.campaign_id,
                "title": response.title,
                "name": response.name,
                "description": response.description,
                "start_date": response.start_date,
                "end_date": response.end_date,
                "is_active": response.is_active,
                "created_at": response.created_at,
                "updated_at": response.updated_at
            }
            
        except grpc.RpcError as e:
            logger.error(
                "gRPC call failed - GetCampaign (sync)",
                campaign_id=campaign_id,
                error=str(e)
            )
            if e.code() == grpc.StatusCode.UNAVAILABLE:
                raise HTTPException(status_code=503, detail="Campaign service unavailable")
            elif e.code() == grpc.StatusCode.NOT_FOUND:
                raise HTTPException(status_code=404, detail="Campaign not found")
            else:
                raise HTTPException(status_code=500, detail="Campaign service error")

# Helper functions for easy usage
async def get_campaign_grpc_client() -> CampaignGRPCClient:
    """Dependency to get async gRPC client"""
    return CampaignGRPCClient()

def get_campaign_grpc_client_sync() -> CampaignGRPCClientSync:
    """Dependency to get sync gRPC client"""
    return CampaignGRPCClientSync()