import redis.asyncio as aioredis
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Single Redis client reused across all requests
redis_client = aioredis.from_url(
    settings.REDIS_URL,
    encoding="utf-8",
    decode_responses=True,
)


async def get_redis() -> aioredis.Redis:
    """Return the Redis client. Used as a FastAPI dependency."""
    return redis_client


async def ping_redis() -> bool:
    """Check if Redis is reachable. Used in health checks."""
    try:
        await redis_client.ping()
        return True
    except Exception as e:
        logger.error("redis_ping_failed", error=str(e))
        return False