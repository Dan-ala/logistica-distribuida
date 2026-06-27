import json
import logging
import time

import pika

from app.config import config
from app.database import init_db, SessionLocal
from app.services import process_location_event

logging.basicConfig(
    level=logging.INFO,
    format="%(name)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(config.SERVICE_NAME)

EXCHANGE = "location.exchange"
EXCHANGE_TYPE = "topic"
QUEUE = "notification.service.queue"
ROUTING_KEY = "location.updated"
DLX = "dlx.exchange"
DLQ = "failed.events.queue"
MAX_RETRIES = 3


def callback(ch, method, properties, body):
    retries = 0
    if properties.headers and "x-retry-count" in properties.headers:
        retries = properties.headers["x-retry-count"]

    try:
        event = json.loads(body)
        logger.info("Received event %s", event.get("event_id"))

        if retries >= MAX_RETRIES:
            logger.error("Max retries exceeded for event %s, sending to DLQ", event.get("event_id"))
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            return

        db = SessionLocal()
        try:
            process_location_event(event["data"], db)
        finally:
            db.close()

        ch.basic_ack(delivery_tag=method.delivery_tag)
        logger.info("Event %s processed successfully", event.get("event_id"))

    except Exception as e:
        logger.error("Error processing event: %s", e)
        headers = properties.headers or {}
        headers["x-retry-count"] = retries + 1
        properties.headers = headers

        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def start_consumer():
    init_db()
    logger.info("Database initialized")

    while True:
        try:
            params = pika.URLParameters(config.RABBITMQ_URL)
            connection = pika.BlockingConnection(params)
            channel = connection.channel()

            channel.exchange_declare(exchange=EXCHANGE, exchange_type=EXCHANGE_TYPE, durable=True)
            channel.exchange_declare(exchange=DLX, exchange_type="fanout", durable=True)

            channel.queue_declare(queue=DLQ, durable=True)

            channel.queue_declare(queue=QUEUE, durable=True, arguments={
                "x-dead-letter-exchange": DLX,
            })
            channel.queue_bind(queue=QUEUE, exchange=EXCHANGE, routing_key=ROUTING_KEY)

            channel.basic_consume(queue=QUEUE, on_message_callback=callback, auto_ack=False)
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
