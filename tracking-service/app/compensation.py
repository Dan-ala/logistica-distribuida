import json
import logging
import time
import threading

import pika

from app.config import config
from app.database import init_db, SessionLocal
from app.models import Location
from shared.event_config import (
    EXCHANGE, EXCHANGE_TYPE, ROUTING_KEY_LOCATION_FAILED,
)
from shared.metrics import events_consumed_total
from shared.logging_config import setup_logging

logger = setup_logging(config.SERVICE_NAME + ".compensation")


class CompensationConsumer:
    def __init__(self):
        self._running = False
        self._thread = None

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True, name="compensation-consumer")
        self._thread.start()
        logger.info("Compensation consumer started")

    def stop(self):
        self._running = False

    def _run(self):
        while self._running:
            try:
                self._consume()
            except Exception as e:
                logger.error("Compensation consumer error: %s", e)
                time.sleep(5)

    def _consume(self):
        params = pika.URLParameters(config.RABBITMQ_URL)
        params.connection_attempts = 1
        params.heartbeat = config.RABBITMQ_HEARTBEAT
        connection = pika.BlockingConnection(params)
        channel = connection.channel()

        channel.exchange_declare(exchange=EXCHANGE, exchange_type=EXCHANGE_TYPE, durable=True)

        result = channel.queue_declare(queue="", exclusive=True)
        compensation_queue = result.method.queue
        channel.queue_bind(queue=compensation_queue, exchange=EXCHANGE, routing_key=ROUTING_KEY_LOCATION_FAILED)

        def callback(ch, method, properties, body):
            try:
                event = json.loads(body)
                original_event_id = event.get("original_event_id", "")
                logger.info("Received compensation event for %s", original_event_id)

                db = SessionLocal()
                try:
                    location = db.query(Location).filter(
                        Location.uuid_event_id == original_event_id
                    ).first()
                    if location:
                        location.status = "FAILED"
                        db.commit()
                        logger.info("Location %s marked as FAILED (compensation)", original_event_id)
                    else:
                        logger.warning("Location %s not found for compensation", original_event_id)
                except Exception as e:
                    db.rollback()
                    logger.error("Compensation DB error: %s", e)
                finally:
                    db.close()

                events_consumed_total.labels(
                    service=config.SERVICE_NAME, queue="compensation", status="success"
                ).inc()
                ch.basic_ack(delivery_tag=method.delivery_tag)
            except Exception as e:
                logger.error("Compensation callback error: %s", e)
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

        channel.basic_consume(queue=compensation_queue, on_message_callback=callback, auto_ack=False)
        channel.start_consuming()
