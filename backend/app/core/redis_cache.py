import json
import logging
import os
from typing import Any

import redis
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)
redis_client = redis.from_url(
    os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    decode_responses=True,
    socket_connect_timeout=2,
    socket_timeout=2,
    health_check_interval=30,
)


def get_cache(key: str) -> Any | None:
    """Return cached JSON data, treating Redis as an optional optimization."""
    try:
        cache_data = redis_client.get(key)
    except redis.RedisError:
        logger.warning("Redis cache read failed; continuing without a cache.")
        return None

    if cache_data is None:
        return None

    try:
        return json.loads(cache_data)
    except json.JSONDecodeError:
        try:
            redis_client.delete(key)
        except redis.RedisError:
            pass
        logger.warning("Discarded malformed Redis cache data.")
        return None


def set_cache(key: str, value: Any, expire: int = 180) -> bool:
    """Store JSON data with a TTL without making Redis availability mandatory."""
    try:
        redis_client.set(key, json.dumps(value), ex=expire)
        return True
    except (TypeError, ValueError, redis.RedisError):
        logger.warning("Redis cache write failed; continuing without a cache.")
        return False
