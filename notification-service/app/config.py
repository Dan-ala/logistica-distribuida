import os


class Config:
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://logistica:logistica123@localhost:5432/notification_db",
    )
    RABBITMQ_URL: str = os.getenv(
        "RABBITMQ_URL",
        "amqp://logistica:logistica123@localhost:5672/",
    )
    SERVICE_NAME: str = os.getenv("SERVICE_NAME", "notification-service")
    MAX_RETRIES: int = 3


config = Config()
