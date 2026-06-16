from app.core.redis import redis_client
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


async def blacklist_token(token: str) -> None:
    """
    Add a token to the blacklist in Redis.
    Expires automatically after ACCESS_TOKEN_EXPIRE_MINUTES.
    """
    key = f"blacklist:{token}"
    expire_seconds = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60

    await redis_client.setex(key, expire_seconds, "blacklisted")
    logger.info("token_blacklisted")


async def is_token_blacklisted(token: str) -> bool:
    """Check if a token has been blacklisted."""
    key = f"blacklist:{token}"
    result = await redis_client.get(key)
    return result is not None