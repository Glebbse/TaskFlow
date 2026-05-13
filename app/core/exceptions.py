from fastapi import FastAPI
from fastapi.responses import JSONResponse
from starlette.requests import Request

class AppError(Exception):
    status_code = 500
    default_msg: str = "Internal server error"

    def __init__(self, msg: str | None = None):
        super().__init__(msg or self.default_msg)


class UserNotFoundError(AppError):
    status_code = 404
    default_msg = "User not found"

    @classmethod
    def by_id(cls, user_id: int) -> "UserNotFoundError":
        return cls(f"User with id {user_id} not found")

    @classmethod
    def by_username(cls, username: str) -> "UserNotFoundError":
        return cls(f"User with username {username} not found")


class TaskNotFoundError(AppError):
    status_code = 404

    def __init__(self, task_id: int):
        super().__init__(f"Task with id {task_id} not found")


class TaskForbiddenError(AppError):
    status_code = 403
    default_msg = "Forbidden"


class UsernameAlreadyExistError(AppError):
    status_code = 409

    def __init__(self, username: str):
        super().__init__(f"Username {username} already exists")


class InvalidCredentialsError(AppError):
    status_code = 401
    default_msg = "Invalid username or password"


class BadRequestError(AppError):
    status_code = 400

class EmailAlreadyExistError(AppError):
    status_code = 409

    def __init__(self, email: str):
        super().__init__(f"Email {email} already exists")


def register_exception_handlers(app: FastAPI):
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": str(exc)}
        )
