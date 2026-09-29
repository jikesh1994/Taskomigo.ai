"""Redis-backed fixed-window rate limiter."""

from __future__ import annotations

import time
from dataclasses import dataclass

from redis.asyncio import Redis


@dataclass(frozen=True, slots=True)
class RateLimitResult:
    allowed: bool
    limit: int
    remaining: int
    retry_after_seconds: int


class RateLimiter:
    def __init__(self, redis: Redis, *, prefix: str = "ratelimit") -> None:
        self._redis = redis
        self._prefix = prefix

    async def hit(
        self, bucket: str, identifier: str, *, limit: int, window_seconds: int
    ) -> RateLimitResult:
        now = int(time.time())
        window_index = now // window_seconds
        # The window index is part of the key, so a key that missed its TTL can never
        # block beyond its own window.
        key = f"{self._prefix}:{bucket}:{identifier}:{window_index}"
        count = await self._redis.incr(key)
        if count == 1:
            await self._redis.expire(key, window_seconds)
        retry_after = (window_index + 1) * window_seconds - now
        return RateLimitResult(
            allowed=count <= limit,
            limit=limit,
            remaining=max(limit - count, 0),
            retry_after_seconds=max(retry_after, 1),
        )
