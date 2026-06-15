from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from jose import JWTError
from app.core.logging import get_logger

logger = get_logger(__name__)


# ─── Custom Exceptions ───────────────────────────────────────────────────────

class AppException(Exception):
    """Base exception for all application errors."""
    def __init__(self, status_code: int, code: str, message: str):
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(message)


class NotFoundException(AppException):
    def __init__(self, resource: str):
        super().__init__(404, "NOT_FOUND", f"{resource} not found")


class UnauthorizedException(AppException):
    def __init__(self, message: str = "Not authenticated"):
        super().__init__(401, "UNAUTHORIZED", message)


class ForbiddenException(AppException):
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(403, "FORBIDDEN", message)


class ConflictException(AppException):
    def __init__(self, message: str):
        super().__init__(409, "CONFLICT", message)


class BadRequestException(AppException):
    def __init__(self, message: str):
        super().__init__(400, "BAD_REQUEST", message)


# ─── Error Response Builder ──────────────────────────────────────────────────

def error_response(status_code: int, code: str, message: str, details=None):
    content = {"success": False, "error": {"code": code, "message": message}}
    if details:
        content["error"]["details"] = details
    return JSONResponse(status_code=status_code, content=content)


# ─── Register Handlers ───────────────────────────────────────────────────────

def register_exception_handlers(app: FastAPI) -> None:

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        logger.warning(
            "app_exception",
            path=request.url.path,
            code=exc.code,
            message=exc.message,
        )
        return error_response(exc.status_code, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        logger.warning("validation_error", path=request.url.path, errors=exc.errors())
        return error_response(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "VALIDATION_ERROR",
            "Request validation failed",
            details=exc.errors(),
        )

    @app.exception_handler(JWTError)
    async def jwt_exception_handler(request: Request, exc: JWTError):
        return error_response(401, "INVALID_TOKEN", "Token is invalid or expired")

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.error(
            "unhandled_exception",
            path=request.url.path,
            error=str(exc),
            exc_info=True,
        )
        return error_response(500, "INTERNAL_ERROR", "An unexpected error occurred")
