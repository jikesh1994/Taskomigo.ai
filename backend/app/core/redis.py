"""Redis client factory (broker, rate limiting, locks, pub/sub)."""

from __future__ import annotations

from redis.asyncio import Redis


def create_redis(url: str) -> Redis:
    return Redis.from_url(url, decode_responses=True, health_check_interval=30)
