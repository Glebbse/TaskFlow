from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.refresh_token import RefreshToken


async def create_db_refresh_token(session: AsyncSession, user_id: int, token_hash: str,
                                  expires_at: datetime) -> RefreshToken:
    refresh_token = RefreshToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at
    )
    session.add(refresh_token)
    await session.flush()
    return refresh_token

async def get_db_refresh_token_by_hash(session: AsyncSession, token_hash: str) -> RefreshToken | None:
    refresh_token = await session.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    return refresh_token.scalar_one_or_none()

async def revoke_all_refresh_tokens_for_user(session: AsyncSession, user_id: int, revoked_at: datetime) -> None:
    await session.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id)
        .where(RefreshToken.revoked_at.is_(None))
        .values(revoked_at=revoked_at))

