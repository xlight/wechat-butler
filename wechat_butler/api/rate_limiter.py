import asyncio
import logging
import time
from collections import deque
from contextlib import asynccontextmanager
from typing import AsyncIterator

from wechat_butler.config import RateLimitingConfig
from wechat_butler.openai_compat.errors import (
    ErrorCode,
    ErrorType,
    error_response,
)

logger = logging.getLogger(__name__)


class RateLimiter:
    def __init__(self, config: RateLimitingConfig):
        self._config = config
        self._global_sem = asyncio.Semaphore(config.max_concurrent)
        self._tier_sems = {
            "mention": asyncio.Semaphore(config.mention.max_concurrent),
            "user_actions": asyncio.Semaphore(config.user_actions.max_concurrent),
            "observer": asyncio.Semaphore(config.observer.max_concurrent),
        }
        self._global_timestamps: deque[float] = deque()
        self._global_lock = asyncio.Lock()
        self._session_timestamps: dict[str, deque[float]] = {}
        self._session_lock = asyncio.Lock()

    def tier_for(self, x_mode: str | None) -> str:
        if x_mode == "mention":
            return "mention"
        if x_mode == "observer":
            return "observer"
        return "user_actions"

    @asynccontextmanager
    async def acquire(
        self, *, x_mode: str | None, x_session_id: str | None
    ) -> AsyncIterator[None]:
        tier = self.tier_for(x_mode)
        tier_sem = self._tier_sems[tier]

        try:
            await asyncio.wait_for(
                asyncio.gather(
                    self._acquire_global_rate(),
                    self._acquire_session_rate(x_session_id),
                    tier_sem.acquire(),
                    self._global_sem.acquire(),
                ),
                timeout=self._config.queue_timeout_seconds,
            )
        except asyncio.TimeoutError as e:
            raise _QueueTimeout() from e

        try:
            yield
        finally:
            self._global_sem.release()
            tier_sem.release()

    async def _acquire_global_rate(self) -> None:
        async with self._global_lock:
            now = time.monotonic()
            self._evict_old_global(now)
            if len(self._global_timestamps) >= self._config.max_requests_per_minute:
                raise _GlobalRateExceeded()
            self._global_timestamps.append(now)

    def _evict_old_global(self, now: float) -> None:
        window_start = now - 60.0
        while self._global_timestamps and self._global_timestamps[0] < window_start:
            self._global_timestamps.popleft()

    async def _acquire_session_rate(self, x_session_id: str | None) -> None:
        if not x_session_id:
            return
        async with self._session_lock:
            now = time.monotonic()
            bucket = self._session_timestamps.setdefault(x_session_id, deque())
            window_start = now - 60.0
            while bucket and bucket[0] < window_start:
                bucket.popleft()
            if len(bucket) >= self._config.per_session_max_per_minute:
                raise _SessionRateExceeded()
            bucket.append(now)


class _QueueTimeout(Exception):
    pass


class _GlobalRateExceeded(Exception):
    pass


class _SessionRateExceeded(Exception):
    pass


def rate_limit_error_response(exc: Exception):
    if isinstance(exc, _QueueTimeout):
        return error_response(
            status_code=429,
            message="Queue timeout: waited too long for an available slot",
            error_type=ErrorType.RATE_LIMIT,
            code=ErrorCode.QUEUE_TIMEOUT,
        )
    if isinstance(exc, _GlobalRateExceeded):
        return error_response(
            status_code=429,
            message="Global rate limit exceeded",
            error_type=ErrorType.RATE_LIMIT,
            code=ErrorCode.RATE_LIMIT_EXCEEDED,
        )
    if isinstance(exc, _SessionRateExceeded):
        return error_response(
            status_code=429,
            message="Per-session rate limit exceeded",
            error_type=ErrorType.RATE_LIMIT,
            code=ErrorCode.SESSION_RATE_LIMIT,
        )
    return error_response(
        status_code=429,
        message="Rate limit exceeded",
        error_type=ErrorType.RATE_LIMIT,
        code=ErrorCode.RATE_LIMIT_EXCEEDED,
    )
