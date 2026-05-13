from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth_accounts import AuthAccount
from app.models.user import User


async def get_db_auth_account(session: AsyncSession, provider: str, provider_user_id: str) -> AuthAccount | None:
    query = await session.execute(
        select(AuthAccount).where(
            AuthAccount.provider == provider,
            AuthAccount.provider_user_id == provider_user_id))
    return query.scalar_one_or_none()

async def create_db_auth_account(session: AsyncSession, user_id: int, provider: str, provider_user_id: str, email: str | None) -> AuthAccount:
    auth_account = AuthAccount(provider=provider, provider_user_id=provider_user_id,
                               email=email, user_id=user_id)

    session.add(auth_account)
    await session.flush()
    return auth_account



