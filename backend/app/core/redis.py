"""
Redis client — singleton connection used for rate limiting, caching, and deduplication.
Falls back gracefully (logs warning) if Redis is not available, so dev without
Docker still works.
"""
from __future__ import annotations
import redis.asyncio as aioredis
from app.core.config import settings
from app.core.logging import logger

_redis: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis | None:
    """Return a connected Redis client or None if unavailable."""
    global _redis
    if _redis is not None:
        return _redis
    try:
        client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=1,
            socket_timeout=1,
        )
        await client.ping()
        _redis = client
        logger.info(f"Redis connected: {settings.REDIS_URL}")
        return _redis
    except Exception as e:
        logger.warning(f"Redis unavailable — rate limiting disabled: {e}")
        return None


async def close_redis() -> None:
    global _redis
    if _redis:
        await _redis.aclose()
        _redis = None


# ── Rate limiter ──────────────────────────────────────────────────────────────

async def check_rate_limit(
    key: str,
    max_calls: int | None = None,
    window_seconds: int | None = None,
) -> tuple[bool, int]:
    """
    Sliding-window counter rate limiter using Redis INCR + EXPIRE.

    Returns (allowed: bool, current_count: int).
    If Redis is unavailable, always allows the request (fail open).
    """
    max_calls = max_calls or settings.RATE_LIMIT_CALLS_PER_MINUTE
    window_seconds = window_seconds or settings.RATE_LIMIT_WINDOW_SECONDS

    redis = await get_redis()
    if redis is None:
        return True, 0  # fail open — Redis down, don't block calls

    try:
        pipe = redis.pipeline()
        await pipe.incr(key)
        await pipe.expire(key, window_seconds)
        results = await pipe.execute()
        count = results[0]
        allowed = count <= max_calls
        if not allowed:
            logger.warning(
                f"Rate limit hit | key={key} count={count} max={max_calls}"
            )
        return allowed, count
    except Exception as e:
        logger.warning(f"Rate limit check failed: {e}")
        return True, 0  # fail open