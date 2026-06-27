import os


class Config:
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://logistica:logistica123@localhost:5432/tracking_db",
    )
    DATABASE_REPLICA_URL: str = os.getenv(
        "DATABASE_REPLICA_URL", "",
    )
    RABBITMQ_URL: str = os.getenv(
        "RABBITMQ_URL",
        "amqp://logistica:logistica123@localhost:5672/",
    )
    SERVICE_NAME: str = os.getenv("SERVICE_NAME", "tracking-service")
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "10"))
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "20"))
    DB_POOL_TIMEOUT: int = int(os.getenv("DB_POOL_TIMEOUT", "30"))
    DB_POOL_RECYCLE: int = int(os.getenv("DB_POOL_RECYCLE", "1800"))
    RABBITMQ_CONNECTION_TIMEOUT: int = int(os.getenv("RABBITMQ_CONNECTION_TIMEOUT", "10"))
    RABBITMQ_HEARTBEAT: int = int(os.getenv("RABBITMQ_HEARTBEAT", "60"))
    RABBITMQ_MAX_RETRIES: int = int(os.getenv("RABBITMQ_MAX_RETRIES", "5"))
    HTTP_TIMEOUT_SECONDS: int = int(os.getenv("HTTP_TIMEOUT_SECONDS", "30"))
    OUTBOX_POLL_INTERVAL: float = float(os.getenv("OUTBOX_POLL_INTERVAL", "2.0"))
    OUTBOX_MAX_PUBLISH_BATCH: int = int(os.getenv("OUTBOX_MAX_PUBLISH_BATCH", "50"))
    PROMETHEUS_PORT: int = int(os.getenv("PROMETHEUS_PORT", "8001"))


config = Config()
