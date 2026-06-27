import json
import logging
import time
from typing import Any

import pika

from app.config import config

logger = logging.getLogger(config.SERVICE_NAME)

EXCHANGE = "location.exchange"
EXCHANGE_TYPE = "topic"
ROUTING_KEY = "location.updated"


class EventPublisher:
    def __init__(self):
        self._connection = None
        self._channel = None
        self._connect()

    def _connect(self):
        max_retries = 5
        for attempt in range(1, max_retries + 1):
            try:
                params = pika.URLParameters(config.RABBITMQ_URL)
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

    def publish(self, event: dict[str, Any]) -> bool:
        self._ensure_connection()
        body = json.dumps(event, default=str)
        try:
            self._channel.basic_publish(
                exchange=EXCHANGE,
                routing_key=ROUTING_KEY,
                body=body,
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    content_type="application/json",
                ),
                mandatory=True,
            )
            logger.info("Published event %s", event.get("event_id"))
            return True
        except pika.exceptions.UnroutableError:
            logger.error("Event %s could not be routed", event.get("event_id"))
            return False
        except Exception as e:
            logger.error("Failed to publish event: %s", e)
            return False

    def close(self):
        if self._connection and not self._connection.is_closed:
            self._connection.close()
