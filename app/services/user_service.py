# Service layer for users

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.user import PasswordUpdate
from app.repos import db_users
from app.core.exceptions import UserNotFoundError, InvalidCredentialsError, BadRequestError
from app.core.security import verify_password, hash_password


async def get_all_users_service(session: AsyncSession,
                                limit: int,
                                offset: int,
                                search: str | None,
                                sort_by: str = "id",
                                order: str = "asc") -> dict:
    items, total = await db_users.get_all_db_users(session, limit, offset, search, sort_by, order)
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset
    }

async def get_user_by_username_service(session: AsyncSession, username: str) -> User | None:
    user = await db_users.get_db_user_by_username(session, username)
    if user is None:
        raise UserNotFoundError.by_username(username)
    return user

async def get_user_by_id_service(session: AsyncSession, user_id: int) -> User | None:
    user = await db_users.get_db_user_by_id(session, user_id)
    if user is None:
        raise UserNotFoundError.by_id(user_id)
    return user

async def delete_user_service(session: AsyncSession, user_id: int) -> dict:
    user = await db_users.get_db_user_by_id(session, user_id)
    if user is None:
        raise UserNotFoundError.by_id(user_id)
    deleted_user = await db_users.delete_db_user(session, user)
    await session.commit()
    return deleted_user

async def update_password_service(session: AsyncSession, user: User, payload: PasswordUpdate):
    if not verify_password(payload.current_password, user.hashed_password):
        raise InvalidCredentialsError("Invalid current password")
    if payload.current_password == payload.new_password:
        raise BadRequestError("New password must be different from current password")
    user.hashed_password = hash_password(payload.new_password)
    await session.commit()
    return {"detail": "Password updated"}
