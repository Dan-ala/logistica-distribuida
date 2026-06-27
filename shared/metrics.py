import time
from functools import wraps

try:
    from prometheus_client import Counter, Histogram, Gauge

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

    class Counter:
        def __init__(self, *args, **kwargs):
            pass
        def inc(self, *args, **kwargs):
            pass

    class Histogram:
        def __init__(self, *args, **kwargs):
            pass
        def observe(self, *args, **kwargs):
            pass
        def time(self):
            class Timer:
                def __enter__(self):
                    return self
                def __exit__(self, *args):
                    pass
            return Timer()

    class Gauge:
        def __init__(self, *args, **kwargs):
            pass
        def set(self, *args, **kwargs):
            pass
        def inc(self, *args, **kwargs):
            pass
        def dec(self, *args, **kwargs):
            pass


http_requests_total = Counter(
    "http_requests_total", "Total HTTP requests", ["service", "method", "endpoint", "status"]
)
http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["service", "method", "endpoint"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)
events_published_total = Counter(
    "events_published_total", "Total events published", ["service", "exchange", "status"]
)
events_consumed_total = Counter(
    "events_consumed_total", "Total events consumed", ["service", "queue", "status"]
)
events_failed_total = Counter(
    "events_failed_total", "Total events failed after retries", ["service", "queue"]
)
db_operations_total = Counter(
    "db_operations_total", "Total database operations", ["service", "operation", "status"]
)
circuit_breaker_state = Gauge(
    "circuit_breaker_state", "Circuit breaker state (0=closed, 1=half_open, 2=open)", ["service", "name"]
)
outbox_size = Gauge(
    "outbox_size", "Number of pending outbox events", ["service"]
)
active_connections = Gauge(
    "active_connections", "Active connections", ["service", "type"]
)


def track_http_request(service: str, method: str, endpoint: str):
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                status = result.status_code if hasattr(result, 'status_code') else 200
                return result
            except Exception as e:
                status = getattr(e, 'status_code', 500)
                raise
            finally:
                duration = time.time() - start
                http_requests_total.labels(service=service, method=method, endpoint=endpoint, status=str(status)).inc()
                http_request_duration_seconds.labels(service=service, method=method, endpoint=endpoint).observe(duration)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                status = getattr(result, 'status_code', 200) if hasattr(result, 'status_code') else 200
                return result
            except Exception as e:
                status = getattr(e, 'status_code', 500)
                raise
            finally:
                duration = time.time() - start
                http_requests_total.labels(service=service, method=method, endpoint=endpoint, status=str(status)).inc()
                http_request_duration_seconds.labels(service=service, method=method, endpoint=endpoint).observe(duration)

        if __import__('inspect').iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator
