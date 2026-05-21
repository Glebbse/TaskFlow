import re
import secrets
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token, \
    hash_refresh_token, get_refresh_token_expires_at
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.repos import db_users, db_refresh_tokens, db_auth_accounts
from app.schemas.auth import Token
from app.schemas.user import UserRegister, UserLogin
from app.core.exceptions import InvalidCredentialsError, UsernameAlreadyExistError, EmailAlreadyExistError


def _ensure_utc_(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

def _ensure_refresh_token_not_expired_(token: RefreshToken) -> None:
    if _ensure_utc_(token.expires_at) <= datetime.now(timezone.utc):
        raise InvalidCredentialsError("Invalid refresh token")

def _username_from_base_email(email: str) -> str:
    local_part = email.split("@", 1)[0].lower()
    username = re.sub(r"[^a-z0-9_]", "", local_part)
    return username or "user"

async def _generate_available_username(session: AsyncSession, email: str) -> str:
    base = _username_from_base_email(email)
    suffix = 2
    username = base
    while await db_users.get_db_user_by_username(session, username) is not None:
        username = f"{base}{suffix}"
        suffix += 1
    return username

async def register_user(session: AsyncSession, payload: UserRegister) -> User:
    existing_user = await db_users.get_db_user_by_username(session, payload.username)
    if existing_user:
        raise UsernameAlreadyExistError(payload.username)

    if payload.email is not None:
        existing_email = await db_users.get_db_user_by_email(session, str(payload.email))
        if existing_email:
            raise EmailAlreadyExistError(str(payload.email))

    hashed_password = hash_password(payload.password)
    user = await db_users.create_db_user(session, payload.username, hashed_password, str(payload.email) if payload.email is not None else None)
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

async def login_with_verified_provider_identity(session: AsyncSession,
                                                provider: str,
                                                provider_user_id: str,
                                                email: str | None, email_verified: bool) -> tuple[Token, str]:
    auth_account = await db_auth_accounts.get_db_auth_account(session, provider, provider_user_id)

    if auth_account is not None:
        return await _issue_token_pair_(session, auth_account.user_id, get_refresh_token_expires_at())

    if not email_verified or email is None:
        raise InvalidCredentialsError("Verified email required")

    user = await db_users.get_db_user_by_email(session, email)

    if user is None:

        username = await _generate_available_username(session, email)
        random_psw = secrets.token_urlsafe(32)
        hashed_psw = hash_password(random_psw)
        user = await db_users.create_db_user(session, username, hashed_psw, email)

    await db_auth_accounts.create_db_auth_account(session, user.id, provider,
                                                  provider_user_id, email)
    await session.commit()

    return await _issue_token_pair_(session, user.id, get_refresh_token_expires_at())


