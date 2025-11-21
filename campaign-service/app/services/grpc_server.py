"""
gRPC Campaign Service Server Implementation
Based on: https://ssojet.com/grpc/use-grpc-in-fastapi/
"""

import grpc
import structlog
from concurrent import futures
from sqlalchemy.orm import Session
from datetime import datetime, timezone

# Import generated gRPC classes
from app.grpc.campaign import campaign_pb2, campaign_pb2_grpc
from app.database.database import get_db
from app.core.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()

class CampaignServiceImpl(campaign_pb2_grpc.CampaignServiceServicer):
    """gRPC Campaign Service Implementation"""
    
    def __init__(self):
        # Get database session generator
        self.get_db = get_db
    
    def GetCampaign(self, request, context):
        """
        Get campaign details by ID (synchronous)
        """
        try:
            logger.info("gRPC GetCampaign called", campaign_id=request.campaign_id)
            
            # Get database session
            db_gen = self.get_db()
            db: Session = next(db_gen)
            
            try:
                # Get campaign from database - use sync query directly
                from app.models.campaign import Campaign
                db_campaign = db.query(Campaign).filter(Campaign.id == request.campaign_id).first()
                
                if not db_campaign:
                    logger.warning("Campaign not found", campaign_id=request.campaign_id)
                    context.set_code(grpc.StatusCode.NOT_FOUND)
                    context.set_details(f"Campaign with ID {request.campaign_id} not found")
                    return campaign_pb2.GetCampaignResponse()
                
                # Create gRPC response
                response = campaign_pb2.GetCampaignResponse(
                    id=db_campaign.id,
                    title=db_campaign.title,
                    name=db_campaign.name,
                    description=db_campaign.description or "",
                    start_date=db_campaign.start_date.isoformat() if db_campaign.start_date else "",
                    end_date=db_campaign.end_date.isoformat() if db_campaign.end_date else "",
                    is_active=db_campaign.is_active,
                    created_at=db_campaign.created_at.isoformat() if db_campaign.created_at else "",
                    updated_at=db_campaign.updated_at.isoformat() if db_campaign.updated_at else ""
                )
                
                logger.info(
                    "gRPC GetCampaign successful",
                    campaign_id=request.campaign_id,
                    campaign_title=db_campaign.title,
                    is_active=db_campaign.is_active
                )
                
                return response
                
            finally:
                # Always close the database session
                try:
                    next(db_gen)
                except StopIteration:
                    pass  # Generator exhausted, session closed
                
        except Exception as e:
            logger.error(
                "gRPC GetCampaign failed", 
                campaign_id=request.campaign_id,
                error=str(e)
            )
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal server error: {str(e)}")
            return campaign_pb2.GetCampaignResponse()
    
    def CheckCampaignActive(self, request, context):
        """
        Check if campaign is active and accepting donations (synchronous)
        """
        try:
            logger.info(
                "gRPC CheckCampaignActive called",
                campaign_id=request.campaign_id
            )
            
            # Get database session
            db_gen = self.get_db()
            db: Session = next(db_gen)
            
            try:
                # Get campaign from database - use sync query
                from app.models.campaign import Campaign
                db_campaign = db.query(Campaign).filter(Campaign.id == request.campaign_id).first()
                
                if not db_campaign:
                    logger.warning("Campaign not found", campaign_id=request.campaign_id)
                    response = campaign_pb2.CheckCampaignActiveResponse(
                        is_active=False,
                        message="Campaign not found",
                        end_date=""
                    )
                    return response
                
                # Check if campaign is active
                is_active = db_campaign.is_active
                message = "Campaign is active" if is_active else "Campaign is not active"
                
                response = campaign_pb2.CheckCampaignActiveResponse(
                    is_active=is_active,
                    message=message,
                    end_date=db_campaign.end_date.isoformat() if db_campaign.end_date else ""
                )
                
                logger.info(
                    "gRPC CheckCampaignActive successful",
                    campaign_id=request.campaign_id,
                    is_active=is_active,
                    message=message
                )
                
                return response
                
            finally:
                # Always close the database session
                try:
                    next(db_gen)
                except StopIteration:
                    pass  # Generator exhausted, session closed
                
        except Exception as e:
            logger.error(
                "gRPC CheckCampaignActive failed",
                campaign_id=request.campaign_id,
                error=str(e)
            )
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Failed to check campaign status! {str(e)}")
            return campaign_pb2.CheckCampaignActiveResponse(is_active=False, message="Internal error", end_date="")

def serve_grpc_sync():
    """Start gRPC server (synchronous version)"""
    try:
        logger.info("Initializing gRPC server...")
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        
        # Add CampaignService to server
        campaign_pb2_grpc.add_CampaignServiceServicer_to_server(
            CampaignServiceImpl(), 
            server
        )
        
        # Configure server address
        listen_addr = "[::]:50051"  # Listen on all interfaces, port 50051
        server.add_insecure_port(listen_addr)
        
        logger.info(f"Starting gRPC server on {listen_addr}")
        
        # Start server
        server.start()
        logger.info("gRPC server started successfully and accepting connections")
        
        try:
            server.wait_for_termination()
        except KeyboardInterrupt:
            logger.info("gRPC server shutdown requested")
            server.stop(5)
    except Exception as e:
        logger.error("Failed to start gRPC server", error=str(e), error_type=type(e).__name__)
        import traceback
        logger.error("gRPC server traceback", traceback=traceback.format_exc())
        raise

if __name__ == "__main__":
    # Run gRPC server standalone (synchronous version)
    serve_grpc_sync()