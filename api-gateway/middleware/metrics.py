"""
Metrics Collection Middleware
Prometheus-compatible metrics
"""
import time
from typing import Dict
from collections import defaultdict
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import logging

logger = logging.getLogger(__name__)

# Metrics storage
class MetricsCollector:
    """Collect and store metrics"""
    
    def __init__(self):
        self.request_count = defaultdict(int)
        self.request_duration = defaultdict(list)
        self.status_codes = defaultdict(int)
        self.service_calls = defaultdict(int)
        self.cache_hits = 0
        self.cache_misses = 0
        self.rate_limit_hits = 0
        self.circuit_breaker_opens = 0
    
    def record_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration: float
    ):
        """Record request metrics"""
        key = f"{method}:{path}"
        self.request_count[key] += 1
        self.request_duration[key].append(duration)
        self.status_codes[status_code] += 1
    
    def record_service_call(self, service_name: str):
        """Record service call"""
        self.service_calls[service_name] += 1
    
    def record_cache_hit(self):
        """Record cache hit"""
        self.cache_hits += 1
    
    def record_cache_miss(self):
        """Record cache miss"""
        self.cache_misses += 1
    
    def record_rate_limit(self):
        """Record rate limit hit"""
        self.rate_limit_hits += 1
    
    def record_circuit_breaker_open(self):
        """Record circuit breaker open"""
        self.circuit_breaker_opens += 1
    
    def get_metrics(self) -> Dict:
        """Get all metrics"""
        metrics = {
            "requests": dict(self.request_count),
            "status_codes": dict(self.status_codes),
            "service_calls": dict(self.service_calls),
            "cache": {
                "hits": self.cache_hits,
                "misses": self.cache_misses,
                "hit_rate": (
                    self.cache_hits / (self.cache_hits + self.cache_misses)
                    if (self.cache_hits + self.cache_misses) > 0
                    else 0
                )
            },
            "rate_limits": self.rate_limit_hits,
            "circuit_breakers": self.circuit_breaker_opens
        }
        
        # Calculate average durations
        avg_durations = {}
        for key, durations in self.request_duration.items():
            if durations:
                avg_durations[key] = sum(durations) / len(durations)
        
        metrics["avg_duration_ms"] = avg_durations
        
        return metrics
    
    def get_prometheus_metrics(self) -> str:
        """Get metrics in Prometheus format"""
        lines = []
        
        # Request count
        lines.append("# HELP api_gateway_requests_total Total number of requests")
        lines.append("# TYPE api_gateway_requests_total counter")
        for key, count in self.request_count.items():
            method, path = key.split(":", 1)
            lines.append(
                f'api_gateway_requests_total{{method="{method}",path="{path}"}} {count}'
            )
        
        # Status codes
        lines.append("# HELP api_gateway_status_codes HTTP status codes")
        lines.append("# TYPE api_gateway_status_codes counter")
        for code, count in self.status_codes.items():
            lines.append(f'api_gateway_status_codes{{code="{code}"}} {count}')
        
        # Duration
        lines.append("# HELP api_gateway_request_duration_seconds Request duration")
        lines.append("# TYPE api_gateway_request_duration_seconds gauge")
        for key, durations in self.request_duration.items():
            if durations:
                method, path = key.split(":", 1)
                avg = sum(durations) / len(durations)
                lines.append(
                    f'api_gateway_request_duration_seconds{{method="{method}",path="{path}"}} {avg:.4f}'
                )
        
        # Cache metrics
        lines.append("# HELP api_gateway_cache_hits Cache hits")
        lines.append("# TYPE api_gateway_cache_hits counter")
        lines.append(f"api_gateway_cache_hits {self.cache_hits}")
        
        lines.append("# HELP api_gateway_cache_misses Cache misses")
        lines.append("# TYPE api_gateway_cache_misses counter")
        lines.append(f"api_gateway_cache_misses {self.cache_misses}")
        
        # Rate limits
        lines.append("# HELP api_gateway_rate_limits Rate limit hits")
        lines.append("# TYPE api_gateway_rate_limits counter")
        lines.append(f"api_gateway_rate_limits {self.rate_limit_hits}")
        
        # Circuit breakers
        lines.append("# HELP api_gateway_circuit_breaker_opens Circuit breaker opens")
        lines.append("# TYPE api_gateway_circuit_breaker_opens counter")
        lines.append(f"api_gateway_circuit_breaker_opens {self.circuit_breaker_opens}")
        
        return "\n".join(lines) + "\n"

# Global metrics collector
metrics_collector = MetricsCollector()

class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to collect request metrics"""
    
    async def dispatch(self, request: Request, call_next):
        # Skip metrics endpoint itself
        if request.url.path == "/metrics":
            return await call_next(request)
        
        start_time = time.time()
        
        try:
            response = await call_next(request)
            duration = time.time() - start_time
            
            # Record metrics
            metrics_collector.record_request(
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration=duration
            )
            
            return response
        
        except Exception as e:
            duration = time.time() - start_time
            
            # Record error
            metrics_collector.record_request(
                method=request.method,
                path=request.url.path,
                status_code=500,
                duration=duration
            )
            
            raise

def get_metrics() -> str:
    """Get metrics in Prometheus format"""
    return metrics_collector.get_prometheus_metrics()

def get_metrics_json() -> Dict:
    """Get metrics in JSON format"""
    return metrics_collector.get_metrics()