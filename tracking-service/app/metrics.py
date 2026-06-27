from shared.metrics import (
    http_requests_total,
    http_request_duration_seconds,
    events_published_total,
    events_failed_total,
    db_operations_total,
    circuit_breaker_state,
    outbox_size,
    active_connections,
    track_http_request,
)
from shared.metrics import PROMETHEUS_AVAILABLE

if PROMETHEUS_AVAILABLE:
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    from fastapi import Response


    def metrics_endpoint():
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
else:
    from fastapi import Response


    def metrics_endpoint():
        return Response(content="# Metrics disabled: prometheus_client not installed", media_type="text/plain")
