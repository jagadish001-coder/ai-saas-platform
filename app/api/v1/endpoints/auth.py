from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials
from app.api.dependencies import CurrentUser, DBSession,security
from app.core.config import settings
from app.core.exceptions import UnauthorizedException
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.schemas.user import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    SuccessResponse,
    TokenResponse,
    UserResponse,
)
from app.services.user_service import UserService
from jose import JWTError

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(body: RegisterRequest, db: DBSession):
    """
    Create a new user account.
    - Email must be unique
    - Password: min 8 chars, 1 uppercase, 1 digit
    """
    service = UserService(db)
    user = await service.create_user(body)
    return user


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: DBSession):
    """
    Authenticate and receive access + refresh tokens.
    - Access token expires in 30 minutes
    - Refresh token expires in 7 days
    """
    service = UserService(db)
    user = await service.authenticate(body.email, body.password)

    access_token = create_access_token(
        subject=str(user.id),
        role=user.role.value,
    )
    refresh_token = create_refresh_token(subject=str(user.id))

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(body: RefreshRequest, db: DBSession):
    """
    Exchange a valid refresh token for new access + refresh tokens.
    Implements token rotation — old refresh token is invalidated.
    """
    try:
        payload = decode_token(body.refresh_token)
        if payload.get("type") != "refresh":
            raise UnauthorizedException("Invalid token type")
        user_id = payload.get("sub")
    except JWTError:
        raise UnauthorizedException("Refresh token is invalid or expired")

    service = UserService(db)
    user = await service.get_by_id_or_404(user_id)

    if not user.is_active:
        raise UnauthorizedException("Account is deactivated")

    new_access = create_access_token(subject=str(user.id), role=user.role.value)
    new_refresh = create_refresh_token(subject=str(user.id))

    return TokenResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: CurrentUser):
    """Return the currently authenticated user's profile."""
    return current_user


@router.post("/logout", response_model=SuccessResponse)
async def logout(
    current_user: CurrentUser,
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """
    Logout endpoint. Blacklists the token in Redis so it
    cannot be used again even if it has not expired yet.
    """
    from app.utils.token_blacklist import blacklist_token
    await blacklist_token(credentials.credentials)
    return SuccessResponse(message="Logged out successfully")
