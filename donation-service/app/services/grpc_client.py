"""
gRPC Product Service Client
Based on: https://ssojet.com/grpc/use-grpc-in-fastapi/
"""

import grpc
import structlog
from typing import Tuple, Dict, Any, Optional
from fastapi import HTTPException

# Import generated gRPC classes
from app.grpc.product import product_pb2, product_pb2_grpc
from app.core.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()

class ProductGRPCClient:
    """gRPC client for Product Service communication"""
    
    def __init__(self):
        # gRPC server address (product service)
        self.server_address = getattr(settings, 'product_grpc_url', 'product-service:50051')
        self.channel = None
        self.stub = None
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.channel = grpc.aio.insecure_channel(self.server_address)
        self.stub = product_pb2_grpc.ProductServiceStub(self.channel)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.channel:
            await self.channel.close()
    
    async def check_availability(self, product_id: int, quantity: int) -> Tuple[bool, int]:
        """
        Check if product is available in requested quantity
        Returns: (available: bool, current_stock: int)
        
        Equivalent to Go code:
        available, stock, err := h.productClient.CheckAvailability(ctx, int32(req.ProductID), int32(req.Quantity))
        """
        try:
            logger.info(
                "Checking product availability via gRPC",
                product_id=product_id,
                quantity=quantity,
                server=self.server_address
            )
            
            # Create gRPC request
            request = product_pb2.CheckAvailabilityRequest(
                product_id=product_id,
                quantity=quantity
            )
            
            # Make gRPC call
            response = await self.stub.CheckAvailability(request)
            
            logger.info(
                "Product availability checked",
                product_id=product_id,
                available=response.available,
                current_stock=response.stock
            )
            
            return response.available, response.stock
            
        except grpc.RpcError as e:
            logger.error(
                "gRPC call failed - CheckAvailability",
                product_id=product_id,
                error_code=e.code().name,
                error_details=e.details(),
                server=self.server_address
            )
            
            if e.code() == grpc.StatusCode.UNAVAILABLE:
                raise HTTPException(
                    status_code=503,
                    detail="Product service unavailable"
                )
            elif e.code() == grpc.StatusCode.NOT_FOUND:
                raise HTTPException(
                    status_code=404,
                    detail="Product not found"
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"Product service error: {e.details()}"
                )
        except Exception as e:
            logger.error(
                "Unexpected error in gRPC call",
                product_id=product_id,
                error=str(e)
            )
            raise HTTPException(
                status_code=500,
                detail="Internal server error"
            )
    
    async def get_product(self, product_id: int) -> Dict[str, Any]:
        """
        Get product details including price
        Returns: product data dictionary
        
        Equivalent to Go code:
        productResp, err := h.productClient.GetProduct(ctx, int32(req.ProductID))
        """
        try:
            logger.info(
                "Getting product details via gRPC",
                product_id=product_id,
                server=self.server_address
            )
            
            # Create gRPC request
            request = product_pb2.GetProductRequest(product_id=product_id)
            
            # Make gRPC call
            response = await self.stub.GetProduct(request)
            
            # Convert gRPC response to dictionary
            product_data = {
                "id": response.id,
                "name": response.name,
                "price": response.price,
                "stock": response.stock
            }
            
            logger.info(
                "Product details retrieved via gRPC",
                product_id=product_id,
                product_name=response.name,
                price=response.price,
                stock=response.stock
            )
            
            return product_data
            
        except grpc.RpcError as e:
            logger.error(
                "gRPC call failed - GetProduct",
                product_id=product_id,
                error_code=e.code().name,
                error_details=e.details(),
                server=self.server_address
            )
            
            if e.code() == grpc.StatusCode.UNAVAILABLE:
                raise HTTPException(
                    status_code=503,
                    detail="Product service unavailable"
                )
            elif e.code() == grpc.StatusCode.NOT_FOUND:
                raise HTTPException(
                    status_code=404,
                    detail="Product not found"
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"Product service error: {e.details()}"
                )
        except Exception as e:
            logger.error(
                "Unexpected error in gRPC call",
                product_id=product_id,
                error=str(e)
            )
            raise HTTPException(
                status_code=500,
                detail="Internal server error"
            )

# Synchronous version for non-async contexts
class ProductGRPCClientSync:
    """Synchronous gRPC client for Product Service"""
    
    def __init__(self):
        self.server_address = getattr(settings, 'product_grpc_url', 'product-service:50051')
        self.channel = None
        self.stub = None
    
    def __enter__(self):
        """Context manager entry"""
        self.channel = grpc.insecure_channel(self.server_address)
        self.stub = product_pb2_grpc.ProductServiceStub(self.channel)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self.channel:
            self.channel.close()
    
    def check_availability(self, product_id: int, quantity: int) -> Tuple[bool, int]:
        """Synchronous version of check_availability"""
        try:
            request = product_pb2.CheckAvailabilityRequest(
                product_id=product_id,
                quantity=quantity
            )
            
            response = self.stub.CheckAvailability(request)
            return response.available, response.stock
            
        except grpc.RpcError as e:
            logger.error(
                "gRPC call failed - CheckAvailability (sync)",
                product_id=product_id,
                error=str(e)
            )
            if e.code() == grpc.StatusCode.UNAVAILABLE:
                raise HTTPException(status_code=503, detail="Product service unavailable")
            elif e.code() == grpc.StatusCode.NOT_FOUND:
                raise HTTPException(status_code=404, detail="Product not found")
            else:
                raise HTTPException(status_code=500, detail="Product service error")
    
    def get_product(self, product_id: int) -> Dict[str, Any]:
        """Synchronous version of get_product"""
        try:
            request = product_pb2.GetProductRequest(product_id=product_id)
            response = self.stub.GetProduct(request)
            
            return {
                "id": response.id,
                "name": response.name,
                "price": response.price,
                "stock": response.stock
            }
            
        except grpc.RpcError as e:
            logger.error(
                "gRPC call failed - GetProduct (sync)",
                product_id=product_id,
                error=str(e)
            )
            if e.code() == grpc.StatusCode.UNAVAILABLE:
                raise HTTPException(status_code=503, detail="Product service unavailable")
            elif e.code() == grpc.StatusCode.NOT_FOUND:
                raise HTTPException(status_code=404, detail="Product not found")
            else:
                raise HTTPException(status_code=500, detail="Product service error")

# Helper functions for easy usage
async def get_product_grpc_client() -> ProductGRPCClient:
    """Dependency to get async gRPC client"""
    return ProductGRPCClient()

def get_product_grpc_client_sync() -> ProductGRPCClientSync:
    """Dependency to get sync gRPC client"""
    return ProductGRPCClientSync()