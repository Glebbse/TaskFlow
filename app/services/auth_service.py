from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token, \
    hash_refresh_token, get_refresh_token_expires_at
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.repos import db_users, db_refresh_tokens
from app.schemas.auth import Token
from app.schemas.user import UserRegister, UserLogin
from app.core.exceptions import InvalidCredentialsError, UsernameAlreadyExistError

def _ensure_utc_(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

def _ensure_refresh_token_not_expired_(token: RefreshToken) -> None:
    if _ensure_utc_(token.expires_at) <= datetime.now(timezone.utc):
        raise InvalidCredentialsError("Invalid refresh token")

async def register_user(session: AsyncSession, payload: UserRegister) -> User:
    existing_user = await db_users.get_db_user_by_username(session, payload.username)
    if existing_user:
        raise UsernameAlreadyExistError(payload.username)

    hashed_password = hash_password(payload.password)
    user = await db_users.create_db_user(session, payload.username, hashed_password)
    await session.commit()
    await session.refresh(user)
    return user


async def authenticate_user(session: AsyncSession, payload: UserLogin) -> User:
    user = await db_users.get_db_user_by_username(session, payload.username)
    if not user:
        raise InvalidCredentialsError()
    if not verify_password(payload.password, user.hashed_password):
        raise InvalidCredentialsError()
    return user


async def _issue_token_pair_(session: AsyncSession, user_id: int, refresh_expires_at: datetime | None = None) -> tuple[Token, str]:
    access_token = create_access_token({"sub": str(user_id)})
    refresh_token = create_refresh_token()
    refresh_token_hash = hash_refresh_token(refresh_token)
    await db_refresh_tokens.create_db_refresh_token(session, user_id, refresh_token_hash, refresh_expires_at)
    await session.commit()
    return Token(access_token=access_token, token_type="bearer"), refresh_token


async def login_user(session: AsyncSession, payload: UserLogin) -> tuple[Token, str]:
    user = await authenticate_user(session, payload)
    return await _issue_token_pair_(session, user.id, get_refresh_token_expires_at())

async def refresh_access_token_service(session: AsyncSession, refresh_token: str) -> tuple[Token, str]:
    token_hash = hash_refresh_token(refresh_token)
    token_in_db = await db_refresh_tokens.get_db_refresh_token_by_hash(session, token_hash)

    if token_in_db is None:
        raise InvalidCredentialsError("Invalid refresh token")

    if token_in_db.revoked_at is not None:
        await db_refresh_tokens.revoke_all_refresh_tokens_for_user(session, token_in_db.user_id, datetime.now(timezone.utc))
        await session.commit()
        raise InvalidCredentialsError("Invalid refresh token")

    _ensure_refresh_token_not_expired_(token_in_db)

    token_in_db.revoked_at = datetime.now(timezone.utc)
    return await _issue_token_pair_(session, token_in_db.user_id, token_in_db.expires_at)

async def logout(session: AsyncSession, refresh_token: str | None) -> dict:
    if refresh_token is None:
        return {"detail": "Logged out"}

    token_hash = hash_refresh_token(refresh_token)
    token_in_db = await db_refresh_tokens.get_db_refresh_token_by_hash(session, token_hash)

    if token_in_db is not None and token_in_db.revoked_at is None:
        token_in_db.revoked_at = datetime.now(timezone.utc)
        await session.commit()

    return {"detail": "Logged out"}

async def logout_all(session: AsyncSession, user: User) -> dict:
    await db_refresh_tokens.revoke_all_refresh_tokens_for_user(session, user.id, datetime.now(timezone.utc))
    await session.commit()

    return {"detail": "Logged out from all devices"}
