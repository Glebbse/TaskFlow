from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.core.security import create_access_token
from app.schemas.auth import Token
from app.schemas.user import UserRegister, UserRead, UserLogin
from app.services import auth_service
from app.services.auth_service import InvalidCredentialsError
from app.services.user_service import UsernameAlreadyExistError


router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=UserRead)
async def register_user(user_in: UserRegister, session: AsyncSession = Depends(get_session)):
    try:
        return await auth_service.register_user(session, user_in)
    except UsernameAlreadyExistError as e:
        raise HTTPException(status_code=409, detail=str(e))

@router.post("/login", response_model=Token)
async def login(user_in: UserLogin, session: AsyncSession = Depends(get_session)):
    try:
        user = await auth_service.authenticate_user(session, user_in)
    except InvalidCredentialsError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

    access_token = create_access_token({"sub": str(user.id)})

    return Token(access_token=access_token, token_type="bearer")
