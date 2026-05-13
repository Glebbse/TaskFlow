# Repo layer for users
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


async def create_db_user(session: AsyncSession, username: str, hashed_password: str, email: str | None = None) -> User:
    user = User(username=username, hashed_password=hashed_password, email=email)
    session.add(user)
    await session.flush()
    return user

async def get_db_user_by_id(session: AsyncSession, user_id: int) -> User | None:
    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()

async def get_db_user_by_username(session: AsyncSession, username: str) -> User | None:
    result = await session.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()

async def get_all_db_users(session: AsyncSession,
                       limit: int,
                       offset: int,
                       search: str | None,
                       sort_by: str = "id",
                       order: str = "asc") -> tuple[list[User], int]:
    query = select(User)
    count_query = select(func.count()).select_from(User)
    if search is not None:
        query = query.where(User.username.ilike(f"%{search}%"))
        count_query = count_query.where(User.username.ilike(f"%{search}%"))

    allowed_fields = {
        "id": User.id,
        "username": User.username
    }
    sorting_cond = allowed_fields.get(sort_by, User.id)
    if order == "desc":
        query = query.order_by(sorting_cond.desc())
    else:
        query = query.order_by(sorting_cond.asc())
    query = query.limit(limit).offset(offset)
    result = await session.execute(query)
    total_result = await session.execute(count_query)
    items = list(result.scalars())
    total = total_result.scalar_one()
    return items, total

async def delete_db_user(session: AsyncSession, user: User) -> dict:
    await session.delete(user)
    return {"deleted": user}

async def get_db_user_by_email(session: AsyncSession, email: str) -> User | None:
    query = await session.execute(select(User).where(User.email == email))
    return query.scalar_one_or_none()
