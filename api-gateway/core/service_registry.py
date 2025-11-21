"""
Service Registry Module
Manages service discovery and health checking
"""
import asyncio
import logging
from typing import Dict, List, Optional
import httpx
from datetime import datetime

from core.config import settings

logger = logging.getLogger(__name__)

class ServiceRegistry:
    """Service registry with health checking"""
    
    def __init__(self):
        self.services: Dict[str, List[Dict]] = {}
        self.health_check_task: Optional[asyncio.Task] = None
        self.running = False
    
    async def initialize(self):
        """Initialize service registry with default services"""
        # Load services from environment or config
        # Example: You can load from Kubernetes service discovery, Consul, etc.
        
        # Default static services (can be overridden)
        default_services = {
            "user-service": [settings.USER_SERVICE_URL],
            "demo-service": [settings.DEMO_SERVICE_URL],
        }
        
        for service_name, instances in default_services.items():
            for instance_url in instances:
                await self.register(service_name, instance_url)
        
        logger.info(f"Service registry initialized with {len(self.services)} services")
    
    async def register(self, service_name: str, service_url: str) -> bool:
        """Register a service instance"""
        if service_name not in self.services:
            self.services[service_name] = []
        
        # Check if instance already exists
        for instance in self.services[service_name]:
            if instance["url"] == service_url:
                logger.warning(f"Service instance already registered: {service_url}")
                return False
        
        # Add new instance
        instance = {
            "url": service_url,
            "healthy": True,
            "last_check": None,
            "failure_count": 0,
            "registered_at": datetime.utcnow()
        }
        
        self.services[service_name].append(instance)
        logger.info(f"Registered service: {service_name} at {service_url}")
        
        return True
    
    async def deregister(self, service_name: str, service_url: Optional[str] = None) -> bool:
        """Deregister a service or specific instance"""
        if service_name not in self.services:
            return False
        
        if service_url:
            # Remove specific instance
            self.services[service_name] = [
                inst for inst in self.services[service_name]
                if inst["url"] != service_url
            ]
            
            # Remove service if no instances left
            if not self.services[service_name]:
                del self.services[service_name]
            
            logger.info(f"Deregistered service instance: {service_name} at {service_url}")
        else:
            # Remove entire service
            del self.services[service_name]
            logger.info(f"Deregistered service: {service_name}")
        
        return True
    
    def get_instances(self, service_name: str) -> List[Dict]:
        """Get all instances of a service"""
        return self.services.get(service_name, [])
    
    def get_healthy_instances(self, service_name: str) -> List[Dict]:
        """Get only healthy instances of a service"""
        instances = self.get_instances(service_name)
        return [inst for inst in instances if inst["healthy"]]
    
    async def check_health(self, service_name: str, instance: Dict) -> bool:
        """Check health of a specific service instance"""
        health_url = f"{instance['url']}/health"
        
        try:
            async with httpx.AsyncClient(
                timeout=settings.HEALTH_CHECK_TIMEOUT
            ) as client:
                response = await client.get(health_url)
                
                if response.status_code == 200:
                    instance["healthy"] = True
                    instance["failure_count"] = 0
                    instance["last_check"] = datetime.utcnow()
                    return True
                else:
                    instance["healthy"] = False
                    instance["failure_count"] += 1
                    instance["last_check"] = datetime.utcnow()
                    logger.warning(
                        f"Health check failed for {service_name}: "
                        f"status {response.status_code}"
                    )
                    return False
        
        except Exception as e:
            instance["healthy"] = False
            instance["failure_count"] += 1
            instance["last_check"] = datetime.utcnow()
            logger.error(f"Health check error for {service_name}: {str(e)}")
            return False
    
    async def health_check_loop(self):
        """Background task for periodic health checks"""
        logger.info("Starting health check loop")
        
        while self.running:
            try:
                # Check all service instances
                for service_name, instances in self.services.items():
                    for instance in instances:
                        await self.check_health(service_name, instance)
                
                # Wait for next check interval
                await asyncio.sleep(settings.HEALTH_CHECK_INTERVAL)
            
            except asyncio.CancelledError:
                logger.info("Health check loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in health check loop: {str(e)}", exc_info=True)
                await asyncio.sleep(5)  # Short delay before retry
    
    async def start_health_checks(self):
        """Start background health checking"""
        if self.running:
            logger.warning("Health checks already running")
            return
        
        self.running = True
        self.health_check_task = asyncio.create_task(self.health_check_loop())
        logger.info("Health checks started")
    
    async def stop_health_checks(self):
        """Stop background health checking"""
        self.running = False
        
        if self.health_check_task:
            self.health_check_task.cancel()
            try:
                await self.health_check_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Health checks stopped")
    
    def get_service_health(self, service_name: str) -> Dict:
        """Get health status of a service"""
        instances = self.get_instances(service_name)
        
        if not instances:
            return {
                "service": service_name,
                "status": "unknown",
                "healthy_instances": 0,
                "total_instances": 0
            }
        
        healthy_count = sum(1 for inst in instances if inst["healthy"])
        
        return {
            "service": service_name,
            "status": "healthy" if healthy_count > 0 else "unhealthy",
            "healthy_instances": healthy_count,
            "total_instances": len(instances),
            "instances": [
                {
                    "url": inst["url"],
                    "healthy": inst["healthy"],
                    "last_check": inst["last_check"].isoformat() if inst["last_check"] else None,
                    "failure_count": inst["failure_count"]
                }
                for inst in instances
            ]
        }
    
    async def get_all_services_health(self) -> Dict[str, Dict]:
        """Get health status of all services"""
        return {
            service_name: self.get_service_health(service_name)
            for service_name in self.services.keys()
        }
    
    def list_services(self) -> List[str]:
        """List all registered service names"""
        return list(self.services.keys())