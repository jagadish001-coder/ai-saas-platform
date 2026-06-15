"""
Integration tests for the /auth endpoints.

These use an in-memory SQLite database so they can run
without a real Postgres instance (e.g. in GitHub Actions).
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.db.session import Base, get_db
from app.main import app

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def db_session():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    async with SessionLocal() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# ─── Register ────────────────────────────────────────────────────────────────

class TestRegister:
    @pytest.mark.asyncio
    async def test_successful_registration(self, client):
        res = await client.post("/api/v1/auth/register", json={
            "email": "test@example.com",
            "full_name": "Test User",
            "password": "SecurePass1",
        })
        assert res.status_code == 201
        data = res.json()
        assert data["email"] == "test@example.com"
        assert "hashed_password" not in data

    @pytest.mark.asyncio
    async def test_duplicate_email_rejected(self, client):
        payload = {"email": "dupe@example.com", "full_name": "User", "password": "SecurePass1"}
        await client.post("/api/v1/auth/register", json=payload)
        res = await client.post("/api/v1/auth/register", json=payload)
        assert res.status_code == 409

    @pytest.mark.asyncio
    async def test_weak_password_rejected(self, client):
        res = await client.post("/api/v1/auth/register", json={
            "email": "weak@example.com",
            "full_name": "Weak",
            "password": "weak",
        })
        assert res.status_code == 422


# ─── Login ───────────────────────────────────────────────────────────────────

class TestLogin:
    @pytest.mark.asyncio
    async def test_successful_login_returns_tokens(self, client):
        await client.post("/api/v1/auth/register", json={
            "email": "login@example.com",
            "full_name": "Login User",
            "password": "SecurePass1",
        })
        res = await client.post("/api/v1/auth/login", json={
            "email": "login@example.com",
            "password": "SecurePass1",
        })
        assert res.status_code == 200
        data = res.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_wrong_password_returns_401(self, client):
        await client.post("/api/v1/auth/register", json={
            "email": "auth@example.com",
            "full_name": "Auth User",
            "password": "SecurePass1",
        })
        res = await client.post("/api/v1/auth/login", json={
            "email": "auth@example.com",
            "password": "WrongPassword1",
        })
        assert res.status_code == 401

    @pytest.mark.asyncio
    async def test_nonexistent_user_returns_401(self, client):
        res = await client.post("/api/v1/auth/login", json={
            "email": "ghost@example.com",
            "password": "SecurePass1",
        })
        assert res.status_code == 401


# ─── Protected route ─────────────────────────────────────────────────────────

class TestProtectedRoutes:
    @pytest.mark.asyncio
    async def test_me_requires_auth(self, client):
        res = await client.get("/api/v1/auth/me")
        assert res.status_code == 403  # HTTPBearer returns 403 when no token

    @pytest.mark.asyncio
    async def test_me_returns_user_with_valid_token(self, client):
        await client.post("/api/v1/auth/register", json={
            "email": "me@example.com",
            "full_name": "Me User",
            "password": "SecurePass1",
        })
        login = await client.post("/api/v1/auth/login", json={
            "email": "me@example.com", "password": "SecurePass1"
        })
        token = login.json()["access_token"]

        res = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert res.status_code == 200
        assert res.json()["email"] == "me@example.com"
