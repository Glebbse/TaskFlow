from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt


from app.core.config import settings
from app.core.db import SessionLocal
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repos.db_users import get_db_user_by_id
from app.services.user_service import UserNotFoundError

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
        user = await get_db_user_by_id(session, user_id)

    except UserNotFoundError:
        raise credentials_error

    return user

