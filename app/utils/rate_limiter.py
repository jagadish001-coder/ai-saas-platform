from fastapi import Request
from app.core.exceptions import AppException
from app.core.redis import redis_client
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


async def check_rate_limit(request: Request) -> None:
    """
    Sliding window rate limiter using Redis.
    Limits each IP to RATE_LIMIT_PER_MINUTE requests per minute.
    Raises 429 if limit exceeded.
    """
    # Get client IP address
    client_ip = request.client.host
    key = f"rate_limit:{client_ip}"

    # Increment counter for this IP
    current = await redis_client.incr(key)

    # Set expiry on first request only
    if current == 1:
        await redis_client.expire(key, 60)  # 60 seconds window

    if current > settings.RATE_LIMIT_PER_MINUTE:
        logger.warning(
            "rate_limit_exceeded",
            ip=client_ip,
            count=current,
            limit=settings.RATE_LIMIT_PER_MINUTE,
        )
        raise AppException(
            status_code=429,
            code="RATE_LIMIT_EXCEEDED",
            message=f"Too many requests. Maximum {settings.RATE_LIMIT_PER_MINUTE} requests per minute.",
        )