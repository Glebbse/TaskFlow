# Service layer for users

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.user import UserRegister
from app.repos import db_users


class UserNotFoundError(Exception):
    pass


class UsernameAlreadyExistError(Exception):
    pass


async def register_user_service(session: AsyncSession, payload: UserRegister) -> User | None:
    existing_username = await db_users.get_db_user_by_username(session, payload.username)
    if existing_username:
        raise UsernameAlreadyExistError(f"Username {payload.username} already exists")
    user = await db_users.create_db_user(session, payload.username, payload.password)
    await session.commit()
    await session.refresh(user)
    return user

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
        raise UserNotFoundError(f"User with username {username} not found")
    return user

async def get_user_by_id_service(session: AsyncSession, user_id: int) -> User | None:
    user = await db_users.get_db_user_by_id(session, user_id)
    if user is None:
        raise UserNotFoundError(f"User with id {user_id} not found")
    return user

async def delete_user_service(session: AsyncSession, user_id: int) -> dict:
    user = await db_users.get_db_user_by_id(session, user_id)
    if user is None:
        raise UserNotFoundError(f"User with id {user_id} not found")
    deleted_user = await db_users.delete_db_user(session, user)
    await session.commit()
    return deleted_user

