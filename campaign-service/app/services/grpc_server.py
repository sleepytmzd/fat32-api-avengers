"""
gRPC Product Service Server Implementation
Based on: https://ssojet.com/grpc/use-grpc-in-fastapi/
"""

import grpc
import structlog
from concurrent import futures
from sqlalchemy.orm import Session

# Import generated gRPC classes
from app.grpc.product import product_pb2, product_pb2_grpc
from app.database.database import get_db
from app.core.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()

class ProductServiceImpl(product_pb2_grpc.ProductServiceServicer):
    """gRPC Product Service Implementation"""
    
    def __init__(self):
        # Get database session generator
        self.get_db = get_db
    
    def GetProduct(self, request, context):
        """
        Get product details by ID (synchronous)
        """
        try:
            logger.info("gRPC GetProduct called", product_id=request.product_id)
            
            # Get database session
            db_gen = self.get_db()
            db: Session = next(db_gen)
            
            try:
                # Get product from database - use sync query directly
                from app.models.product import Product
                db_product = db.query(Product).filter(Product.id == request.product_id).first()
                
                if not db_product:
                    logger.warning("Product not found", product_id=request.product_id)
                    context.set_code(grpc.StatusCode.NOT_FOUND)
                    context.set_details(f"Product with ID {request.product_id} not found")
                    return product_pb2.GetProductResponse()
                
                # Create gRPC response
                response = product_pb2.GetProductResponse(
                    id=db_product.id,
                    name=db_product.name,
                    price=float(db_product.price),
                    stock=db_product.stock
                )
                
                logger.info(
                    "gRPC GetProduct successful",
                    product_id=request.product_id,
                    product_name=db_product.name,
                    price=db_product.price,
                    stock=db_product.stock
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
                "gRPC GetProduct failed", 
                product_id=request.product_id,
                error=str(e)
            )
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal server error: {str(e)}")
            return product_pb2.GetProductResponse()
    
    def CheckAvailability(self, request, context):
        """
        Check if product is available in requested quantity (synchronous)
        """
        try:
            logger.info(
                "gRPC CheckAvailability called",
                product_id=request.product_id,
                quantity=request.quantity
            )
            
            # Get database session
            db_gen = self.get_db()
            db: Session = next(db_gen)
            
            try:
                # Get product from database - use sync query
                from app.models.product import Product
                db_product = db.query(Product).filter(Product.id == request.product_id).first()
                
                if not db_product:
                    logger.warning("Product not found", product_id=request.product_id)
                    # Return not available with 0 stock
                    response = product_pb2.CheckAvailabilityResponse(
                        available=False,
                        stock=0
                    )
                    return response
                
                # Check if requested quantity is available
                available = db_product.stock >= request.quantity
                
                response = product_pb2.CheckAvailabilityResponse(
                    available=available,
                    stock=db_product.stock
                )
                
                logger.info(
                    "gRPC CheckAvailability successful",
                    product_id=request.product_id,
                    requested_quantity=request.quantity,
                    available_stock=db_product.stock,
                    available=available
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
                "gRPC CheckAvailability failed",
                product_id=request.product_id,
                quantity=request.quantity,
                error=str(e)
            )
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Failed to serialize response! {str(e)}")
            return product_pb2.CheckAvailabilityResponse(available=False, stock=0)

def serve_grpc_sync():
    """Start gRPC server (synchronous version)"""
    try:
        logger.info("Initializing gRPC server...")
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        
        # Add ProductService to server
        product_pb2_grpc.add_ProductServiceServicer_to_server(
            ProductServiceImpl(), 
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