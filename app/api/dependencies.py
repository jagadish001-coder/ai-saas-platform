import uuid
from typing import Annotated
from fastapi import Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User, UserRole
from app.services.user_service import UserService

security = HTTPBearer()


# ─── DB dependency alias ──────────────────────────────────────────────────────

DBSession = Annotated[AsyncSession, Depends(get_db)]


# ─── Token → User ────────────────────────────────────────────────────────────

async def get_current_user(
    db: DBSession,
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> User:
    """Decode JWT, check blacklist, look up the user, return them."""
    from app.utils.token_blacklist import is_token_blacklisted

    try:
        payload = decode_token(credentials.credentials)
        if payload.get("type") != "access":
            raise UnauthorizedException("Invalid token type")
        user_id = payload.get("sub")
        if not user_id:
            raise UnauthorizedException("Token missing subject")
    except JWTError:
        raise UnauthorizedException("Token is invalid or expired")

    # Check if token has been blacklisted (logged out)
    if await is_token_blacklisted(credentials.credentials):
        raise UnauthorizedException("Token has been revoked — please login again")

    service = UserService(db)
    user = await service.get_by_id(uuid.UUID(user_id))

    if not user:
        raise UnauthorizedException("User account not found")
    if not user.is_active:
        raise UnauthorizedException("Account is deactivated")

    return user


# ─── Convenient type aliases ──────────────────────────────────────────────────

CurrentUser = Annotated[User, Depends(get_current_user)]


# ─── RBAC helpers ─────────────────────────────────────────────────────────────

def require_role(*roles: UserRole):
    """Factory that creates a dependency requiring specific roles."""
    async def _check(current_user: CurrentUser) -> User:
        if current_user.role not in roles:
            raise ForbiddenException(
                f"This action requires one of: {[r.value for r in roles]}"
            )
        return current_user
    return _check


# Role-specific dependencies (use as FastAPI Depends)
AdminOnly = Annotated[User, Depends(require_role(UserRole.ADMIN))]
AdminOrUser = Annotated[User, Depends(require_role(UserRole.ADMIN, UserRole.USER))]
