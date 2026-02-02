import time

import redis.asyncio as redis

from app.config import settings
from app.ratelimit.rules import get_limits

_redis: redis.Redis | None = None


async def get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.from_url(settings.redis_url)
    return _redis


async def _check_window(r: redis.Redis, key: str, max_requests: int, window: int) -> tuple[bool, int]:
    """Returns (allowed, retry_after_seconds)."""
    now = time.time()
    pipe = r.pipeline()
    pipe.zremrangebyscore(key, 0, now - window)
    pipe.zadd(key, {str(now): now})
    pipe.zcard(key)
    pipe.expire(key, window)
    pipe.zrange(key, 0, 0, withscores=True)
    results = await pipe.execute()
    count = results[2]
    if count <= max_requests:
        return True, 0
    oldest = results[4]
    if oldest:
        retry_after = int((oldest[0][1] + window) - now) + 1
    else:
        retry_after = window
    return False, max(retry_after, 1)


async def check_rate_limit(agent_id: str, endpoint: str, trust_level: int) -> tuple[bool, int]:
    """Check all rate limit windows. Returns (allowed, retry_after_seconds)."""
    limits = get_limits(endpoint, trust_level)
    r = await get_redis()
    for max_requests, window in limits:
        key = f"rl:{agent_id}:{endpoint}:{window}"
        allowed, retry_after = await _check_window(r, key, max_requests, window)
        if not allowed:
            return False, retry_after
    return True, 0


async def check_ip_rate_limit(ip: str, endpoint: str, max_requests: int, window: int) -> bool:
    """Per-IP sliding window rate limit."""
    r = await get_redis()
    key = f"rl:ip:{ip}:{endpoint}"
    allowed, _ = await _check_window(r, key, max_requests, window)
    return allowed
