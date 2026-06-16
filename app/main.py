from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Depends
from app.utils.rate_limiter import check_rate_limit

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import get_logger, setup_logging
from app.utils.middleware import RequestLoggingMiddleware

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic."""
    setup_logging()
    logger.info(
        "app_startup",
        app=settings.APP_NAME,
        env=settings.APP_ENV,
        debug=settings.DEBUG,
    )

    # Always create tables on startup if they don't exist
    from app.db.session import engine, Base
    from app.models.user import User
    from app.models.document import Document
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("database_tables_ready")

    # Initialize Qdrant collection
    from app.core.qdrant import init_collection
    await init_collection()

    yield
    logger.info("app_shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        description="Production-grade AI SaaS Platform API",
        version="1.0.0",
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        lifespan=lifespan,
        dependencies=[Depends(check_rate_limit)],  # ← add this line
    )

    # ─── Middleware (order matters — outermost runs first) ────────────────
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ─── Exception handlers ───────────────────────────────────────────────
    register_exception_handlers(app)

    # ─── Routers ──────────────────────────────────────────────────────────
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    return app


app = create_app()
