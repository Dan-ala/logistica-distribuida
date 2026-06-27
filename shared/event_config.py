EXCHANGE = "location.exchange"
EXCHANGE_TYPE = "topic"
ROUTING_KEY_LOCATION_UPDATED = "location.updated"
ROUTING_KEY_LOCATION_FAILED = "location.failed"

NOTIFICATION_QUEUE = "notification.service.queue"
ROUTE_QUEUE = "route.service.queue"

DLX = "dlx.exchange"
DLQ = "failed.events.queue"
RETRY_EXCHANGE = "retry.exchange"
RETRY_QUEUE_SUFFIX = ".retry"
RETRY_TTL_MS = 5000

MAX_RETRIES = 3
RETRY_HEADER = "x-retry-count"

EVENT_TYPE_LOCATION_UPDATED = "LOCATION_UPDATED"
EVENT_TYPE_LOCATION_FAILED = "LOCATION_FAILED"
