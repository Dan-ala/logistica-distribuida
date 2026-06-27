import logging
import time
from enum import Enum

logger = logging.getLogger("circuit_breaker")


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_max_retries: int = 3,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_retries = half_open_max_retries

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.half_open_attempts = 0

    def _reset(self):
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.half_open_attempts = 0
        logger.info("Circuit breaker '%s' reset to CLOSED", self.name)

    def _open(self):
        self.state = CircuitState.OPEN
        self.last_failure_time = time.time()
        logger.warning("Circuit breaker '%s' OPENED", self.name)

    def call(self, fn, *args, **kwargs):
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                self.half_open_attempts = 0
                logger.info("Circuit breaker '%s' HALF_OPEN, probing...")
            else:
                raise Exception(f"Circuit breaker '{self.name}' is OPEN, call rejected")

        try:
            result = fn(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _on_success(self):
        if self.state == CircuitState.HALF_OPEN:
            self.half_open_attempts += 1
            if self.half_open_attempts >= self.half_open_max_retries:
                self._reset()
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0

    def _on_failure(self):
        self.failure_count += 1
        if self.state == CircuitState.HALF_OPEN:
            self._open()
        elif self.failure_count >= self.failure_threshold:
            self._open()

    def __call__(self, fn, *args, **kwargs):
        return self.call(fn, *args, **kwargs)
