import os


class Config:
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://logistica:logistica123@localhost:5432/tracking_db",
    )
    RABBITMQ_URL: str = os.getenv(
        "RABBITMQ_URL",
        "amqp://logistica:logistica123@localhost:5672/",
    )
    SERVICE_NAME: str = os.getenv("SERVICE_NAME", "tracking-service")


config = Config()
