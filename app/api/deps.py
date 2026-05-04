from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt


from app.core.config import settings
from app.core.db import SessionLocal
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.user_service import get_user_by_id_service
from app.core.exceptions import UserNotFoundError

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise

def decode_access_token(token: str):
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

async def get_current_user(token: str = Depends(oauth2_scheme),
                           session: AsyncSession = Depends(get_session)) -> User:
    credentials_error = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_error
        user_id = int(user_id)
    except (JWTError, ValueError):
        raise credentials_error

    try:
        user = await get_user_by_id_service(session, user_id)

    except UserNotFoundError:
        raise credentials_error

    return user

async def get_current_admin(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    return current_user
