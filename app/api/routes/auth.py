from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.util import await_only

from app.api.deps import get_session, get_current_user
from app.core.security import create_access_token
from app.models.user import User
from app.schemas.auth import Token, AccessToken, RefreshTokenRequest
from app.schemas.user import UserRegister, UserRead, UserLogin, MessageResponse
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=UserRead)
async def register_user(user_in: UserRegister, session: AsyncSession = Depends(get_session)):
    return await auth_service.register_user(session, user_in)

@router.post("/login", response_model=Token)
async def login(user_in: UserLogin, session: AsyncSession = Depends(get_session)):
    return await auth_service.login_user(session, user_in)

@router.post("/refresh", response_model=Token)
async def refresh_access_token(payload: RefreshTokenRequest, session: AsyncSession = Depends(get_session)):
    return await auth_service.refresh_access_token_service(session, payload)

@router.post("/logout", response_model=MessageResponse)
async def logout(payload: RefreshTokenRequest, session: AsyncSession = Depends(get_session)):
    return await auth_service.logout_service(session, payload)

@router.post("/logout-all", response_model=MessageResponse)
async def logout_all(current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    return await auth_service.logout_all_service(session, current_user)
