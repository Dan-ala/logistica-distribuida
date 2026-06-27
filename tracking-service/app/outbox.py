import json
import logging
import threading
import time
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import config
from app.models import Outbox, Location
from app.publisher import EventPublisher
from shared.event_config import ROUTING_KEY_LOCATION_UPDATED, EVENT_TYPE_LOCATION_UPDATED

logger = logging.getLogger(config.SERVICE_NAME)


class OutboxPoller:
    def __init__(self):
        self._running = False
        self._thread = None
        self._publisher = EventPublisher()
        self._engine = create_engine(config.DATABASE_URL)
        self._Session = sessionmaker(bind=self._engine)

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True, name="outbox-poller")
        self._thread.start()
        logger.info("Outbox poller started")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        self._publisher.close()

    def _poll_loop(self):
        while self._running:
            try:
                self._publish_pending()
            except Exception as e:
                logger.error("Outbox poll error: %s", e)
            time.sleep(config.OUTBOX_POLL_INTERVAL)

    def _publish_pending(self):
        db = self._Session()
        try:
            pending = (
                db.query(Outbox)
                .filter(Outbox.status == "PENDING")
                .order_by(Outbox.created_at.asc())
                .limit(config.OUTBOX_MAX_PUBLISH_BATCH)
                .all()
            )

            for entry in pending:
                event = json.loads(entry.body)
                success = self._publisher.publish(event, routing_key=entry.routing_key)
                if success:
                    entry.status = "PUBLISHED"
                    entry.published_at = datetime.now(timezone.utc)
                    logger.info("Outbox event %s published", entry.event_id)
                else:
                    entry.retry_count += 1
                    if entry.retry_count >= 5:
                        entry.status = "FAILED"
                        logger.error("Outbox event %s permanently failed", entry.event_id)
                    else:
                        logger.warning("Outbox event %s retry %d", entry.event_id, entry.retry_count)

            db.commit()
        except Exception as e:
            db.rollback()
            logger.error("Outbox publish error: %s", e)
        finally:
            db.close()

    def get_pending_count(self) -> int:
        db = self._Session()
        try:
            return db.query(Outbox).filter(Outbox.status == "PENDING").count()
        finally:
            db.close()
