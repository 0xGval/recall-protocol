import time

import redis.asyncio as redis

from app.config import settings
from app.ratelimit.rules import get_limit

_redis: redis.Redis | None = None


async def get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.from_url(settings.redis_url)
    return _redis


async def check_rate_limit(agent_id: str, endpoint: str, trust_level: int) -> bool:
    """Returns True if request is allowed, False if rate-limited."""
    max_requests, window = get_limit(endpoint, trust_level)
    r = await get_redis()
    key = f"rl:{agent_id}:{endpoint}"
    now = time.time()

    pipe = r.pipeline()
    pipe.zremrangebyscore(key, 0, now - window)
    pipe.zadd(key, {str(now): now})
    pipe.zcard(key)
    pipe.expire(key, window)
    results = await pipe.execute()

    count = results[2]
    return count <= max_requests
