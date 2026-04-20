from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.repos import db_users
from app.schemas.user import UserRegister, UserLogin
from app.services.user_service import UsernameAlreadyExistError


class InvalidCredentialsError(Exception):
    pass


async def register_user(session: AsyncSession, payload: UserRegister) -> User:
    existing_user = await db_users.get_db_user_by_username(session, payload.username)
    if existing_user:
        raise UsernameAlreadyExistError(f"Username {payload.username} already exists")

    hashed_password = hash_password(payload.password)
    user = await db_users.create_db_user(session, payload.username, hashed_password)
    await session.commit()
    await session.refresh(user)
    return user


async def authenticate_user(session: AsyncSession, payload: UserLogin) -> User:
    user = await db_users.get_db_user_by_username(session, payload.username)
    if not user:
        raise InvalidCredentialsError("Invalid username or password")
    if not verify_password(payload.password, user.hashed_password):
        raise InvalidCredentialsError("Invalid username or password")
    return user
