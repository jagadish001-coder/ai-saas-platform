from fastapi import APIRouter
from sqlalchemy import text
from app.api.dependencies import DBSession
from app.core.config import settings
from app.core.redis import ping_redis

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():
    """Basic liveness check — is the app running?"""
    return {"status": "ok", "app": settings.APP_NAME, "env": settings.APP_ENV}


@router.get("/health/ready")
async def readiness_check(db: DBSession):
    """Readiness check — checks DB and Redis."""
    try:
        await db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {str(e)}"

    redis_status = "ok" if await ping_redis() else "error"

    ready = db_status == "ok" and redis_status == "ok"

    return {
        "status": "ready" if ready else "not_ready",
        "checks": {
            "database": db_status,
            "redis": redis_status,
        },
    }