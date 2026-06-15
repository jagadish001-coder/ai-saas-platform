import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ConflictException,
    NotFoundException,
    UnauthorizedException,
)
from app.core.logging import get_logger
from app.core.security import hash_password, verify_password
from app.models.user import User, UserRole
from app.schemas.user import RegisterRequest, UserUpdate

logger = get_logger(__name__)


class UserService:

    def __init__(self, db: AsyncSession):
        self.db = db

    # ─── Create ───────────────────────────────────────────────────────────

    async def create_user(self, data: RegisterRequest) -> User:
        """Register a new user. Raises ConflictException if email exists."""
        existing = await self.get_by_email(data.email)
        if existing:
            raise ConflictException("An account with this email already exists")

        user = User(
            email=data.email.lower().strip(),
            full_name=data.full_name.strip(),
            hashed_password=hash_password(data.password),
            role=UserRole.USER,
        )
        self.db.add(user)
        await self.db.flush()   # get the UUID before commit

        logger.info("user_registered", user_id=str(user.id), email=user.email)
        return user

    # ─── Read ─────────────────────────────────────────────────────────────

    async def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        result = await self.db.execute(
            select(User).where(User.email == email.lower().strip())
        )
        return result.scalar_one_or_none()

    async def get_by_id_or_404(self, user_id: uuid.UUID) -> User:
        user = await self.get_by_id(user_id)
        if not user:
            raise NotFoundException("User")
        return user

    # ─── Auth ─────────────────────────────────────────────────────────────

    async def authenticate(self, email: str, password: str) -> User:
        """Verify credentials. Raises UnauthorizedException on failure."""
        user = await self.get_by_email(email)

        # Use same error for both cases — prevents email enumeration
        if not user or not verify_password(password, user.hashed_password):
            raise UnauthorizedException("Invalid email or password")

        if not user.is_active:
            raise UnauthorizedException("Account is deactivated")

        # Update last login timestamp
        user.last_login_at = datetime.now(timezone.utc)
        await self.db.flush()

        logger.info("user_login", user_id=str(user.id))
        return user

    # ─── Update ───────────────────────────────────────────────────────────

    async def update_user(self, user_id: uuid.UUID, data: UserUpdate) -> User:
        user = await self.get_by_id_or_404(user_id)

        if data.full_name is not None:
            user.full_name = data.full_name.strip()

        if data.email is not None:
            existing = await self.get_by_email(data.email)
            if existing and existing.id != user_id:
                raise ConflictException("Email already in use")
            user.email = data.email.lower().strip()

        await self.db.flush()
        logger.info("user_updated", user_id=str(user_id))
        return user

    # ─── Admin ────────────────────────────────────────────────────────────

    async def deactivate_user(self, user_id: uuid.UUID) -> User:
        user = await self.get_by_id_or_404(user_id)
        user.is_active = False
        await self.db.flush()
        logger.info("user_deactivated", user_id=str(user_id))
        return user
