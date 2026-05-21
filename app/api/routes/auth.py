import secrets
from urllib.parse import urlencode

from fastapi import APIRouter, Cookie, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.responses import RedirectResponse

from app.api.deps import get_session, get_current_user
from app.core.exceptions import InvalidCredentialsError
from app.models.user import User
from app.schemas.auth import Token
from app.schemas.user import UserRegister, UserRead, UserLogin, MessageResponse
from app.services import auth_service
from app.services.oauth_google import get_google_identity_from_code, build_google_authorization_url

router = APIRouter(prefix="/auth", tags=["auth"])
REFRESH_COOKIE_NAME = "taskflow_refresh_token"
REFRESH_COOKIE_MAX_AGE = 60 * 60 * 24 * 30
GOOGLE_STATE_COOKIE_NAME = "taskflow_google_oauth_state"
GOOGLE_STATE_COOKIE_MAX_AGE = 60 * 10

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

@router.get("/google/callback")
async def google_callback(
        code: str,
        state: str,
        oauth_state: str | None = Cookie(default=None, alias=GOOGLE_STATE_COOKIE_NAME),
        session: AsyncSession = Depends(get_session)):

    if oauth_state is None or oauth_state != state:
        raise InvalidCredentialsError("Invalid OAuth state")

    identity = await get_google_identity_from_code(code)
    tokens, refresh_token = await auth_service.login_with_verified_provider_identity(
        session=session,
        provider="google",
        provider_user_id=identity.provider_user_id,
        email=identity.email,
        email_verified=identity.email_verified
    )

    fragment = urlencode({
        "access_token": tokens.access_token,
        "token_type": tokens.token_type,
    })
    redirect_response = RedirectResponse(f"/ui/#{fragment}")
    set_refresh_cookie(redirect_response, refresh_token)

    redirect_response.delete_cookie(
        key=GOOGLE_STATE_COOKIE_NAME,
        path="/auth",
        samesite="lax",
    )

    return redirect_response

@router.get("/google/login")
async def google_login():
    state = secrets.token_urlsafe(32)
    auth_url = build_google_authorization_url(state)
    response = RedirectResponse(auth_url)
    response.set_cookie(
        key=GOOGLE_STATE_COOKIE_NAME,
        value=state,
        max_age=GOOGLE_STATE_COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        path="/auth",
    )
    return response
