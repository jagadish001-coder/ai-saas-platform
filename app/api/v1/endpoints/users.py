import uuid
from fastapi import APIRouter
from app.api.dependencies import AdminOnly, CurrentUser, DBSession
from app.schemas.user import SuccessResponse, UserResponse, UserUpdate
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
async def get_my_profile(current_user: CurrentUser):
    """Get your own profile."""
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_my_profile(
    body: UserUpdate,
    current_user: CurrentUser,
    db: DBSession,
):
    """Update your own name or email."""
    service = UserService(db)
    return await service.update_user(current_user.id, body)


# ─── Admin-only routes ────────────────────────────────────────────────────────

@router.get("", response_model=list[UserResponse])
async def list_users(
    _: AdminOnly,   # enforces admin role
    db: DBSession,
):
    """[Admin] List all users."""
    from sqlalchemy import select
    from app.models.user import User
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    return result.scalars().all()


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: uuid.UUID,
    _: AdminOnly,
    db: DBSession,
):
    """[Admin] Get a specific user by ID."""
    service = UserService(db)
    return await service.get_by_id_or_404(user_id)


@router.delete("/{user_id}", response_model=SuccessResponse)
async def deactivate_user(
    user_id: uuid.UUID,
    _: AdminOnly,
    db: DBSession,
):
    """[Admin] Deactivate a user account."""
    service = UserService(db)
    await service.deactivate_user(user_id)
    return SuccessResponse(message="User deactivated")
