# AI SaaS Platform

A production-grade AI platform with full authentication, PostgreSQL, vector search (Phase 2), monitoring, CI/CD, and Docker deployment.

## Architecture

```
app/
├── api/
│   ├── dependencies.py      # JWT auth, RBAC, DB injection
│   └── v1/
│       ├── router.py
│       └── endpoints/
│           ├── auth.py      # register, login, refresh, /me
│           ├── users.py     # profile management, admin routes
│           └── health.py    # liveness + readiness probes
├── core/
│   ├── config.py            # pydantic-settings, env vars
│   ├── security.py          # JWT creation/decode, bcrypt
│   ├── exceptions.py        # custom errors + global handlers
│   └── logging.py           # structlog (JSON prod, pretty dev)
├── db/
│   └── session.py           # async SQLAlchemy engine + session
├── models/
│   └── user.py              # User SQLAlchemy model + roles
├── schemas/
│   └── user.py              # Pydantic request/response schemas
├── services/
│   └── user_service.py      # All user business logic
└── utils/
    └── middleware.py         # Request logging + request ID
```

## Quick Start

### 1. Clone and configure

```bash
git clone <your-repo>
cd ai-saas-platform
cp .env.example .env
# Edit .env — set a real SECRET_KEY (min 32 chars)
```

### 2. Run with Docker (recommended)

```bash
docker-compose up --build
```

App is live at http://localhost:8000  
API docs at http://localhost:8000/docs

### 3. Run locally

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start the server
uvicorn app.main:app --reload
```

## API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/v1/auth/register` | ❌ | Create account |
| POST | `/api/v1/auth/login` | ❌ | Get tokens |
| POST | `/api/v1/auth/refresh` | ❌ | Rotate tokens |
| GET  | `/api/v1/auth/me` | ✅ | My profile |
| POST | `/api/v1/auth/logout` | ✅ | Logout |
| GET  | `/api/v1/users/me` | ✅ | My profile |
| PATCH| `/api/v1/users/me` | ✅ | Update profile |
| GET  | `/api/v1/users` | 🔐 Admin | List all users |
| GET  | `/api/v1/health` | ❌ | Liveness check |
| GET  | `/api/v1/health/ready` | ❌ | Readiness check |

## Running Tests

```bash
pip install aiosqlite pytest-cov
pytest tests/ --cov=app --cov-report=term-missing
```

## Database Migrations

```bash
# Create a new migration after changing models
alembic revision --autogenerate -m "describe your change"

# Apply migrations
alembic upgrade head

# Roll back one step
alembic downgrade -1
```

## Roadmap

- [x] Phase 1 — Auth, PostgreSQL, REST APIs, CI/CD
- [ ] Phase 2 — Document upload, RAG pipeline, Qdrant vector DB
- [ ] Phase 3 — Rate limiting, security hardening, structured logging
- [ ] Phase 4 — Prometheus metrics, Grafana dashboards
- [ ] Phase 5 — Production deployment (Railway), custom domain
