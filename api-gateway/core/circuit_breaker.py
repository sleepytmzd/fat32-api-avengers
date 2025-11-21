"""
Circuit Breaker Module
Implements circuit breaker pattern for fault tolerance
"""
import time
import logging
from typing import Dict
from enum import Enum

from core.config import settings

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Blocking requests
    HALF_OPEN = "half_open"  # Testing if service recovered

class CircuitBreaker:
    """Circuit breaker implementation for service resilience"""
    
    def __init__(self):
        self.enabled = settings.CIRCUIT_BREAKER_ENABLED
        self.failure_threshold = settings.CIRCUIT_BREAKER_THRESHOLD
        self.timeout = settings.CIRCUIT_BREAKER_TIMEOUT
        
        # Store circuit state per service
        self.circuits: Dict[str, Dict] = {}
    
    def _get_circuit(self, service_name: str) -> Dict:
        """Get or create circuit for service"""
        if service_name not in self.circuits:
            self.circuits[service_name] = {
                "state": CircuitState.CLOSED,
                "failure_count": 0,
                "success_count": 0,
                "last_failure_time": None,
                "last_state_change": time.time()
            }
        
        return self.circuits[service_name]
    
    def is_open(self, service_name: str) -> bool:
        """Check if circuit is open (blocking requests)"""
        if not self.enabled:
            return False
        
        circuit = self._get_circuit(service_name)
        
        # If circuit is open, check if timeout has elapsed
        if circuit["state"] == CircuitState.OPEN:
            if circuit["last_failure_time"]:
                time_since_failure = time.time() - circuit["last_failure_time"]
                
                # Move to half-open state after timeout
                if time_since_failure >= self.timeout:
                    self._transition_to_half_open(service_name)
                    return False
            
            return True
        
        return False
    
    def record_success(self, service_name: str):
        """Record a successful request"""
        if not self.enabled:
            return
        
        circuit = self._get_circuit(service_name)
        circuit["success_count"] += 1
        
        # Reset failure count on success
        if circuit["state"] == CircuitState.HALF_OPEN:
            # Close circuit after successful test
            self._transition_to_closed(service_name)
            logger.info(f"Circuit closed for service: {service_name}")
        
        elif circuit["state"] == CircuitState.CLOSED:
            # Reset failure count
            circuit["failure_count"] = 0
    
    def record_failure(self, service_name: str):
        """Record a failed request"""
        if not self.enabled:
            return
        
        circuit = self._get_circuit(service_name)
        circuit["failure_count"] += 1
        circuit["last_failure_time"] = time.time()
        
        # Open circuit if threshold exceeded
        if circuit["state"] == CircuitState.CLOSED:
            if circuit["failure_count"] >= self.failure_threshold:
                self._transition_to_open(service_name)
                logger.warning(
                    f"Circuit opened for service: {service_name} "
                    f"(failures: {circuit['failure_count']})"
                )
        
        elif circuit["state"] == CircuitState.HALF_OPEN:
            # Reopen circuit on failure during test
            self._transition_to_open(service_name)
            logger.warning(f"Circuit reopened for service: {service_name}")
    
    def _transition_to_open(self, service_name: str):
        """Transition circuit to open state"""
        circuit = self._get_circuit(service_name)
        circuit["state"] = CircuitState.OPEN
        circuit["last_state_change"] = time.time()
    
    def _transition_to_half_open(self, service_name: str):
        """Transition circuit to half-open state"""
        circuit = self._get_circuit(service_name)
        circuit["state"] = CircuitState.HALF_OPEN
        circuit["failure_count"] = 0
        circuit["last_state_change"] = time.time()
        logger.info(f"Circuit half-open for service: {service_name}")
    
    def _transition_to_closed(self, service_name: str):
        """Transition circuit to closed state"""
        circuit = self._get_circuit(service_name)
        circuit["state"] = CircuitState.CLOSED
        circuit["failure_count"] = 0
        circuit["success_count"] = 0
        circuit["last_state_change"] = time.time()
    
    def get_state(self, service_name: str) -> str:
        """Get current circuit state"""
        circuit = self._get_circuit(service_name)
        return circuit["state"].value
    
    def get_stats(self, service_name: str) -> Dict:
        """Get circuit statistics"""
        circuit = self._get_circuit(service_name)
        
        return {
            "service": service_name,
            "state": circuit["state"].value,
            "failure_count": circuit["failure_count"],
            "success_count": circuit["success_count"],
            "last_failure_time": circuit["last_failure_time"],
            "last_state_change": circuit["last_state_change"]
        }
    
    def reset(self, service_name: str):
        """Manually reset circuit to closed state"""
        circuit = self._get_circuit(service_name)
        self._transition_to_closed(service_name)
        logger.info(f"Circuit manually reset for service: {service_name}")
    
    def get_all_stats(self) -> Dict[str, Dict]:
        """Get statistics for all circuits"""
        return {
            service_name: self.get_stats(service_name)
            for service_name in self.circuits.keys()
        }