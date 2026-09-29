"""Per-account throttling of failed sign-ins (on top of the per-IP rate limit).

The per-IP limit doesn't stop password spraying against one account from many
addresses. This counts *failed* attempts per submitted email in a fixed window and
refuses further attempts for that email until the window ends.

* It applies to any submitted email, registered or not, so it reveals nothing about
  which accounts exist.
* Keys hold a SHA-256 of the email, never the address itself.
* Trade-off: someone who knows a user's email can block that user's sign-in for one
  window by failing repeatedly. The window is short and the event is audited.
"""

from __future__ import annotations

import hashlib
import time

from redis.asyncio import Redis

from app.core.exceptions import RateLimitedError


class LoginThrottle:
    def __init__(
        self,
        redis: Redis,
        *,
        max_failures: int,
        window_seconds: int,
        prefix: str = "login-failures",
    ) -> None:
        self._redis = redis
        self._max_failures = max_failures
        self._window = window_seconds
        self._prefix = prefix

    def _key(self, email: str) -> tuple[str, int]:
        now = int(time.time())
        window_index = now // self._window
        digest = hashlib.sha256(email.encode()).hexdigest()
        retry_after = (window_index + 1) * self._window - now
        return f"{self._prefix}:{digest}:{window_index}", max(retry_after, 1)

    async def ensure_allowed(self, email: str) -> None:
        key, retry_after = self._key(email)
        failures = int(await self._redis.get(key) or 0)
        if failures >= self._max_failures:
            raise RateLimitedError(
                "Too many failed sign-in attempts. Please try again later.",
                code="login_throttled",
                headers={"Retry-After": str(retry_after)},
            )

    async def record_failure(self, email: str) -> None:
        key, _ = self._key(email)
        if await self._redis.incr(key) == 1:
            await self._redis.expire(key, self._window)

    async def reset(self, email: str) -> None:
        key, _ = self._key(email)
        await self._redis.delete(key)
