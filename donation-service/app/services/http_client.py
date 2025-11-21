"""
HTTP client for Product Service communication
"""
import httpx
import structlog
from typing import Dict, Any
from fastapi import HTTPException

from app.core.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class ProductHTTPClient:
    """HTTP client for Product Service communication"""
    
    def __init__(self):
        # HTTP service URL
        self.base_url = getattr(settings, 'product_service_url', 'http://product-service:8002')
        self.timeout = httpx.Timeout(10.0, connect=5.0)
        
    async def reduce_stock(self, product_id: int, quantity: int) -> Dict[str, Any]:
        """
        Reduce product stock via HTTP API
        
        Args:
            product_id: Product ID
            quantity: Quantity to reduce
            
        Returns:
            Response data with new stock level
        """
        try:
            logger.info(
                "Reducing product stock via HTTP",
                product_id=product_id,
                quantity=quantity,
                url=self.base_url
            )
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.patch(
                    f"{self.base_url}/api/v1/products/{product_id}/reduce-stock",
                    json={"quantity": quantity}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    logger.info(
                        "Product stock reduced successfully",
                        product_id=product_id,
                        quantity_reduced=quantity,
                        new_stock=data.get("stock", "unknown")
                    )
                    return data
                elif response.status_code == 404:
                    logger.error(
                        "Product not found when reducing stock",
                        product_id=product_id,
                        status_code=response.status_code
                    )
                    raise HTTPException(
                        status_code=404,
                        detail=f"Product {product_id} not found"
                    )
                elif response.status_code == 400:
                    error_detail = response.json().get("detail", "Bad request")
                    logger.error(
                        "Bad request when reducing stock",
                        product_id=product_id,
                        error=error_detail,
                        status_code=response.status_code
                    )
                    raise HTTPException(
                        status_code=400,
                        detail=error_detail
                    )
                else:
                    logger.error(
                        "Failed to reduce product stock",
                        product_id=product_id,
                        status_code=response.status_code,
                        response=response.text
                    )
                    raise HTTPException(
                        status_code=response.status_code,
                        detail="Failed to reduce product stock"
                    )
                    
        except httpx.TimeoutException:
            logger.error(
                "Timeout while reducing product stock",
                product_id=product_id,
                url=self.base_url
            )
            raise HTTPException(
                status_code=504,
                detail="Product service timeout"
            )
        except httpx.ConnectError:
            logger.error(
                "Connection error to product service",
                product_id=product_id,
                url=self.base_url
            )
            raise HTTPException(
                status_code=503,
                detail="Product service unavailable"
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                "Unexpected error reducing product stock",
                product_id=product_id,
                error=str(e)
            )
            raise HTTPException(
                status_code=500,
                detail="Internal server error"
            )


async def get_product_http_client() -> ProductHTTPClient:
    """Dependency to get HTTP client"""
    return ProductHTTPClient()
