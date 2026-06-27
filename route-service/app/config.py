import os


class Config:
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://logistica:logistica123@localhost:5432/route_db",
    )
    RABBITMQ_URL: str = os.getenv(
        "RABBITMQ_URL",
        "amqp://logistica:logistica123@localhost:5672/",
    )
    SERVICE_NAME: str = os.getenv("SERVICE_NAME", "route-service")
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "5"))
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "10"))
    DB_POOL_TIMEOUT: int = int(os.getenv("DB_POOL_TIMEOUT", "30"))
    DB_POOL_RECYCLE: int = int(os.getenv("DB_POOL_RECYCLE", "1800"))
    RABBITMQ_CONNECTION_TIMEOUT: int = int(os.getenv("RABBITMQ_CONNECTION_TIMEOUT", "10"))
    RABBITMQ_HEARTBEAT: int = int(os.getenv("RABBITMQ_HEARTBEAT", "60"))


config = Config()
