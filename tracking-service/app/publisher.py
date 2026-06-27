import json
import logging
import time
from typing import Any, Optional

import pika

from app.config import config
from shared.event_config import EXCHANGE, EXCHANGE_TYPE, ROUTING_KEY_LOCATION_UPDATED
from shared.circuit_breaker import CircuitBreaker, CircuitState
from shared.metrics import events_published_total, circuit_breaker_state

logger = logging.getLogger(config.SERVICE_NAME)


class EventPublisher:
    def __init__(self):
        self._connection: Optional[pika.BlockConnection] = None
        self._channel: Optional[pika.channel.Channel] = None
        self._circuit_breaker = CircuitBreaker(
            name="rabbitmq-publisher",
            failure_threshold=3,
            recovery_timeout=30.0,
        )
        self._connect()

    def _connect(self):
        max_retries = config.RABBITMQ_MAX_RETRIES
        for attempt in range(1, max_retries + 1):
            try:
                params = pika.URLParameters(config.RABBITMQ_URL)
                params.connection_attempts = 1
                params.heartbeat = config.RABBITMQ_HEARTBEAT
                self._connection = pika.BlockingConnection(params)
                self._channel = self._connection.channel()
                self._channel.exchange_declare(
                    exchange=EXCHANGE,
                    exchange_type=EXCHANGE_TYPE,
                    durable=True,
                )
                self._channel.confirm_delivery()
                logger.info("Connected to RabbitMQ")
                return
            except Exception as e:
                logger.warning(
                    "RabbitMQ connection attempt %d/%d failed: %s",
                    attempt, max_retries, e,
                )
                if attempt < max_retries:
                    time.sleep(2 ** attempt)
        raise RuntimeError("Could not connect to RabbitMQ after retries")

    def _ensure_connection(self):
        if not self._connection or self._connection.is_closed:
            self._connect()

    def publish(self, event: dict[str, Any], routing_key: str = ROUTING_KEY_LOCATION_UPDATED) -> bool:
        self._ensure_connection()
        body = json.dumps(event, default=str)

        def _do_publish():
            return self._channel.basic_publish(
                exchange=EXCHANGE,
                routing_key=routing_key,
                body=body,
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    content_type="application/json",
                    headers={"event_type": event.get("event_type", "")},
                ),
                mandatory=True,
            )

        try:
            result = self._circuit_breaker.call(_do_publish)
            events_published_total.labels(
                service=config.SERVICE_NAME, exchange=EXCHANGE, status="success"
            ).inc()
            circuit_breaker_state.labels(
                service=config.SERVICE_NAME, name=self._circuit_breaker.name
            ).set(
                0 if self._circuit_breaker.state == CircuitState.CLOSED
                else 1 if self._circuit_breaker.state == CircuitState.HALF_OPEN
                else 2
            )
            logger.info("Published event %s", event.get("event_id"))
            return True
        except pika.exceptions.UnroutableError:
            logger.error("Event %s could not be routed", event.get("event_id"))
            events_published_total.labels(
                service=config.SERVICE_NAME, exchange=EXCHANGE, status="failed"
            ).inc()
            return False
        except Exception as e:
            logger.error("Failed to publish event: %s", e)
            events_published_total.labels(
                service=config.SERVICE_NAME, exchange=EXCHANGE, status="failed"
            ).inc()
            return False

    def close(self):
        if self._connection and not self._connection.is_closed:
            self._connection.close()
