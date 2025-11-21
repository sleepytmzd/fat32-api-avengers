import asyncio
import time
from enum import Enum
from typing import Callable, Any, Optional
from datetime import datetime, timedelta
import structlog

logger = structlog.get_logger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open" 
    HALF_OPEN = "half_open"


class CircuitBreakerError(Exception):
    """Circuit breaker specific error"""
    pass


class CircuitBreaker:
    """Circuit breaker implementation for database operations"""
    
    def __init__(self, 
                 failure_threshold: int = 5,
                 recovery_timeout: timedelta = timedelta(seconds=30),
                 expected_exception: type = Exception):
        """
        Initialize circuit breaker
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Time to wait before trying half-open state
            expected_exception: Exception type to count as failure
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = CircuitState.CLOSED
        
    def _should_attempt_reset(self) -> bool:
        """Check if we should attempt to reset from OPEN to HALF_OPEN"""
        if self.state != CircuitState.OPEN:
            return False
            
        if not self.last_failure_time:
            return False
            
        return datetime.now() - self.last_failure_time >= self.recovery_timeout
    
    def _on_success(self):
        """Handle successful operation"""
        self.failure_count = 0
        self.last_failure_time = None
        
        if self.state != CircuitState.CLOSED:
            logger.info("Circuit breaker closed after successful operation")
            self.state = CircuitState.CLOSED
    
    def _on_failure(self, exception: Exception):
        """Handle failed operation"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            if self.state != CircuitState.OPEN:
                logger.warning("Circuit breaker opened due to failures",
                             failure_count=self.failure_count,
                             threshold=self.failure_threshold)
                self.state = CircuitState.OPEN
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        
        # Check if we should attempt reset
        if self._should_attempt_reset():
            logger.info("Circuit breaker attempting half-open state")
            self.state = CircuitState.HALF_OPEN
        
        # If circuit is open, fail fast
        if self.state == CircuitState.OPEN:
            raise CircuitBreakerError("Circuit breaker is OPEN - service temporarily unavailable")
        
        try:
            # Execute the function
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
                
            self._on_success()
            return result
            
        except self.expected_exception as e:
            self._on_failure(e)
            raise
        except Exception as e:
            # Don't count unexpected exceptions as failures
            logger.error("Unexpected exception in circuit breaker", error=str(e))
            raise
    
    def get_state(self) -> dict:
        """Get current circuit breaker state"""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "failure_threshold": self.failure_threshold,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "recovery_timeout_seconds": self.recovery_timeout.total_seconds()
        }


# Global circuit breaker instance for database operations
db_circuit_breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=timedelta(seconds=30),
    expected_exception=Exception
)