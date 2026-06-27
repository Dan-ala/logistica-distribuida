import json
import logging
import time
import threading

import pika

from app.config import config
from app.database import init_db, SessionLocal
from app.services import process_location_event
from shared.event_config import (
    EXCHANGE, EXCHANGE_TYPE, NOTIFICATION_QUEUE, ROUTING_KEY_LOCATION_UPDATED,
    DLX, DLQ, RETRY_EXCHANGE, RETRY_TTL_MS, MAX_RETRIES, RETRY_HEADER,
    EVENT_TYPE_LOCATION_UPDATED, EVENT_TYPE_LOCATION_FAILED,
    ROUTING_KEY_LOCATION_FAILED,
)
from shared.circuit_breaker import CircuitBreaker, CircuitState
from shared.metrics import events_consumed_total, events_failed_total, circuit_breaker_state
from shared.logging_config import setup_logging

logger = setup_logging(config.SERVICE_NAME)

RETRY_QUEUE = NOTIFICATION_QUEUE + ".retry"


def publish_compensation(event_data: dict, original_event_id: str):
    try:
        params = pika.URLParameters(config.RABBITMQ_URL)
        params.connection_attempts = 1
        params.heartbeat = config.RABBITMQ_HEARTBEAT
        conn = pika.BlockingConnection(params)
        ch = conn.channel()
        ch.exchange_declare(exchange=EXCHANGE, exchange_type=EXCHANGE_TYPE, durable=True)
        failed_event = {
            "event_id": original_event_id + "_failed",
            "event_type": EVENT_TYPE_LOCATION_FAILED,
            "timestamp": __import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            ).isoformat(),
            "data": event_data,
            "original_event_id": original_event_id,
            "reason": "max_retries_exceeded",
        }
        ch.basic_publish(
            exchange=EXCHANGE,
            routing_key=ROUTING_KEY_LOCATION_FAILED,
            body=json.dumps(failed_event, default=str),
            properties=pika.BasicProperties(delivery_mode=2, content_type="application/json"),
        )
        conn.close()
        logger.info("Published compensation event for %s", original_event_id)
    except Exception as e:
        logger.error("Failed to publish compensation event: %s", e)


def callback(ch, method, properties, body):
    retries = 0
    if properties.headers and RETRY_HEADER in properties.headers:
        retries = properties.headers[RETRY_HEADER]

    try:
        event = json.loads(body)
        event_id = event.get("event_id", "unknown")
        logger.info("Received event %s (retry %d)", event_id, retries)

        if retries >= MAX_RETRIES:
            logger.error("Max retries exceeded for event %s, sending to DLQ", event_id)
            events_failed_total.labels(
                service=config.SERVICE_NAME, queue=NOTIFICATION_QUEUE
            ).inc()
            publish_compensation(event.get("data", {}), event_id)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            return

        db = SessionLocal()
        try:
            process_location_event(event["data"], event_id, db)
        finally:
            db.close()

        ch.basic_ack(delivery_tag=method.delivery_tag)
        events_consumed_total.labels(
            service=config.SERVICE_NAME, queue=NOTIFICATION_QUEUE, status="success"
        ).inc()
        logger.info("Event %s processed successfully", event_id)

    except Exception as e:
        logger.error("Error processing event: %s", e)
        events_consumed_total.labels(
            service=config.SERVICE_NAME, queue=NOTIFICATION_QUEUE, status="failed"
        ).inc()

        if retries >= MAX_RETRIES - 1:
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        else:
            headers = properties.headers or {}
            headers[RETRY_HEADER] = retries + 1
            properties.headers = headers
            ch.basic_publish(
                exchange=RETRY_EXCHANGE,
                routing_key=NOTIFICATION_QUEUE,
                body=body,
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    headers=headers,
                ),
            )
            ch.basic_ack(delivery_tag=method.delivery_tag)


def start_consumer():
    init_db()
    logger.info("Database initialized")

    while True:
        try:
            params = pika.URLParameters(config.RABBITMQ_URL)
            params.connection_attempts = 1
            params.heartbeat = config.RABBITMQ_HEARTBEAT
            connection = pika.BlockingConnection(params)
            channel = connection.channel()

            channel.exchange_declare(exchange=EXCHANGE, exchange_type=EXCHANGE_TYPE, durable=True)
            channel.exchange_declare(exchange=DLX, exchange_type="fanout", durable=True)
            channel.exchange_declare(exchange=RETRY_EXCHANGE, exchange_type="direct", durable=True)

            channel.queue_declare(queue=DLQ, durable=True)
            channel.queue_bind(queue=DLQ, exchange=DLX, routing_key="")

            channel.queue_declare(queue=RETRY_QUEUE, durable=True, arguments={
                "x-message-ttl": RETRY_TTL_MS,
                "x-dead-letter-exchange": EXCHANGE,
                "x-dead-letter-routing-key": ROUTING_KEY_LOCATION_UPDATED,
            })
            channel.queue_bind(queue=RETRY_QUEUE, exchange=RETRY_EXCHANGE, routing_key=NOTIFICATION_QUEUE)

            channel.queue_declare(queue=NOTIFICATION_QUEUE, durable=True, arguments={
                "x-dead-letter-exchange": DLX,
            })
            channel.queue_bind(queue=NOTIFICATION_QUEUE, exchange=EXCHANGE, routing_key=ROUTING_KEY_LOCATION_UPDATED)

            channel.basic_consume(queue=NOTIFICATION_QUEUE, on_message_callback=callback, auto_ack=False)
            logger.info("Consumer started. Waiting for events...")
            channel.start_consuming()

        except pika.exceptions.AMQPConnectionError:
            logger.warning("RabbitMQ not available. Retrying in 5 seconds...")
            time.sleep(5)
        except KeyboardInterrupt:
            logger.info("Consumer stopped")
            break


if __name__ == "__main__":
    start_consumer()
