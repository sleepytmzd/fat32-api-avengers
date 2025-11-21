"""
Load Balancer Module
Implements various load balancing strategies
"""
import random
import logging
from typing import Optional, Dict
from enum import Enum

from core.service_registry import ServiceRegistry

logger = logging.getLogger(__name__)

class LoadBalancingStrategy(Enum):
    """Load balancing strategies"""
    ROUND_ROBIN = "round_robin"
    RANDOM = "random"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"

class LoadBalancer:
    """Load balancer with multiple strategies"""
    
    def __init__(self, service_registry: ServiceRegistry, strategy: LoadBalancingStrategy = LoadBalancingStrategy.ROUND_ROBIN):
        self.strategy = strategy
        self.service_registry = service_registry
        self.round_robin_counters: Dict[str, int] = {}
        self.connection_counts: Dict[str, int] = {}
    
    async def get_instance(self, service_name: str) -> Optional[str]:
        """
        Get a service instance URL using the configured load balancing strategy
        """
        instances = self.service_registry.get_healthy_instances(service_name)
        
        if not instances:
            logger.error(f"No healthy instances available for service: {service_name}")
            return None
        
        if len(instances) == 1:
            return instances[0]["url"]
        
        # Apply load balancing strategy
        if self.strategy == LoadBalancingStrategy.ROUND_ROBIN:
            return self._round_robin(service_name, instances)
        
        elif self.strategy == LoadBalancingStrategy.RANDOM:
            return self._random(instances)
        
        elif self.strategy == LoadBalancingStrategy.LEAST_CONNECTIONS:
            return self._least_connections(instances)
        
        elif self.strategy == LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN:
            return self._weighted_round_robin(service_name, instances)
        
        else:
            return self._round_robin(service_name, instances)
    
    def _round_robin(self, service_name: str, instances: list) -> str:
        """Round-robin load balancing"""
        if service_name not in self.round_robin_counters:
            self.round_robin_counters[service_name] = 0
        
        index = self.round_robin_counters[service_name] % len(instances)
        self.round_robin_counters[service_name] += 1
        
        return instances[index]["url"]
    
    def _random(self, instances: list) -> str:
        """Random load balancing"""
        instance = random.choice(instances)
        return instance["url"]
    
    def _least_connections(self, instances: list) -> str:
        """Least connections load balancing"""
        # Find instance with least connections
        min_connections = float('inf')
        selected_instance = None
        
        for instance in instances:
            url = instance["url"]
            connections = self.connection_counts.get(url, 0)
            
            if connections < min_connections:
                min_connections = connections
                selected_instance = instance
        
        if selected_instance:
            # Increment connection count
            url = selected_instance["url"]
            self.connection_counts[url] = self.connection_counts.get(url, 0) + 1
            return url
        
        return instances[0]["url"]
    
    def _weighted_round_robin(self, service_name: str, instances: list) -> str:
        """Weighted round-robin (based on instance health/performance)"""
        # Use failure_count as inverse weight
        weights = []
        
        for instance in instances:
            # Lower failure count = higher weight
            weight = max(1, 10 - instance.get("failure_count", 0))
            weights.append(weight)
        
        # Weighted random selection
        total_weight = sum(weights)
        
        if total_weight == 0:
            return self._round_robin(service_name, instances)
        
        r = random.uniform(0, total_weight)
        cumulative = 0
        
        for i, weight in enumerate(weights):
            cumulative += weight
            if r <= cumulative:
                return instances[i]["url"]
        
        return instances[-1]["url"]
    
    def release_connection(self, instance_url: str):
        """Release a connection (for least connections strategy)"""
        if instance_url in self.connection_counts:
            self.connection_counts[instance_url] = max(
                0,
                self.connection_counts[instance_url] - 1
            )
    
    def get_connection_count(self, instance_url: str) -> int:
        """Get current connection count for an instance"""
        return self.connection_counts.get(instance_url, 0)
    
    def get_stats(self, service_name: str) -> Dict:
        """Get load balancing statistics"""
        instances = self.service_registry.get_instances(service_name)
        
        return {
            "service": service_name,
            "strategy": self.strategy.value,
            "total_instances": len(instances),
            "healthy_instances": len([i for i in instances if i["healthy"]]),
            "round_robin_counter": self.round_robin_counters.get(service_name, 0),
            "connection_counts": {
                inst["url"]: self.connection_counts.get(inst["url"], 0)
                for inst in instances
            }
        }
    
    def set_strategy(self, strategy: LoadBalancingStrategy):
        """Change load balancing strategy"""
        self.strategy = strategy
        logger.info(f"Load balancing strategy changed to: {strategy.value}")