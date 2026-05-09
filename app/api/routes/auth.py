from fastapi import APIRouter, Cookie, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, get_current_user
from app.core.exceptions import InvalidCredentialsError
from app.models.user import User
from app.schemas.auth import Token
from app.schemas.user import UserRegister, UserRead, UserLogin, MessageResponse
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])
REFRESH_COOKIE_NAME = "taskflow_refresh_token"
REFRESH_COOKIE_MAX_AGE = 60 * 60 * 24 * 30


def set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        max_age=REFRESH_COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        path="/auth",
    )


def clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path="/auth",
        samesite="lax",
    )

@router.post("/register", response_model=UserRead)
async def register_user(user_in: UserRegister, session: AsyncSession = Depends(get_session)):
    return await auth_service.register_user(session, user_in)

@router.post("/login", response_model=Token)
async def login(user_in: UserLogin, response: Response, session: AsyncSession = Depends(get_session)):
    tokens, refresh_token = await auth_service.login_user(session, user_in)
    set_refresh_cookie(response, refresh_token)
    return tokens

@router.post("/refresh", response_model=Token)
async def refresh_access_token(response: Response,
                               refresh_token: str | None= Cookie(default=None, alias=REFRESH_COOKIE_NAME),
                               session: AsyncSession = Depends(get_session)):
    if refresh_token is None:
        raise InvalidCredentialsError("Invalid refresh token")

    tokens, new_refresh_token = await auth_service.refresh_access_token_service(session, refresh_token)
    set_refresh_cookie(response, new_refresh_token)
    return tokens

@router.post("/logout", response_model=MessageResponse)
async def logout(response: Response,
                 refresh_token: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
                 session: AsyncSession = Depends(get_session)):
    result = await auth_service.logout(session, refresh_token)
    clear_refresh_cookie(response)
    return result

@router.post("/logout-all", response_model=MessageResponse)
async def logout_all(response: Response,
                     current_user: User = Depends(get_current_user),
                     session: AsyncSession = Depends(get_session)):
    result = await auth_service.logout_all(session, current_user)
    clear_refresh_cookie(response)
    return result
