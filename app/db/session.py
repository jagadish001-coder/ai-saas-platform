from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings


# ─── Engine ──────────────────────────────────────────────────────────────────

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,          # logs SQL queries in dev
    pool_pre_ping=True,           # reconnects on stale connections
    pool_size=10,
    max_overflow=20,
)

# ─── Session factory ─────────────────────────────────────────────────────────

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,       # avoid lazy-load errors after commit
    autocommit=False,
    autoflush=False,
)


# ─── Declarative base ────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    pass


# ─── Dependency ──────────────────────────────────────────────────────────────

async def get_db() -> AsyncSession:
    """FastAPI dependency — yields an async DB session per request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
