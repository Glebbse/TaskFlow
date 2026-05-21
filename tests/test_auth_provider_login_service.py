import pytest
from sqlalchemy import select, func

from app.core.exceptions import InvalidCredentialsError
from app.models.auth_accounts import AuthAccount
from app.models.refresh_token import RefreshToken
from app.models.user import User
from tests.conftest import TestSessionLocal
from app.services.auth_service import login_with_verified_provider_identity


@pytest.mark.asyncio
async def test_existing_user_gets_linked_to_auth_account(client):
    payload = {"username": "gleb", "password": "gleb321", "email": "gleb@test.com"}
    first_response = await client.post("/auth/register", json=payload)
    assert first_response.status_code == 200

    async with TestSessionLocal() as session:
        token, refresh_token = await login_with_verified_provider_identity(
            session, "google", "google_sub_123",
            "gleb@test.com", True
        )
        assert token.access_token
        assert refresh_token

        user_res = await session.execute(select(func.count()).select_from(User))
        assert user_res.scalar_one() == 1

        auth_account_res = await session.execute(select(func.count()).select_from(AuthAccount))
        assert auth_account_res.scalar_one() == 1

@pytest.mark.asyncio
async def test_google_verified_identity_creates_user_auth_account_and_tokens():
    async with TestSessionLocal() as s:
        token, refresh_token = await login_with_verified_provider_identity(
            session=s, provider="google", provider_user_id="google_sub_123",
            email="gleb@test.com", email_verified=True
        )
        assert token.access_token
        assert token.token_type == "bearer"
        assert refresh_token

    async with TestSessionLocal() as s:
        user_res = await s.execute(select(User).where(User.email == "gleb@test.com"))
        user = user_res.scalar_one()
        assert user.username == "gleb"
        assert user.email == "gleb@test.com"
        assert user.hashed_password != ""

        auth_account_res = await s.execute(select(AuthAccount).where(AuthAccount.user_id == user.id))
        auth_account = auth_account_res.scalar_one()
        assert auth_account.provider == "google"
        assert auth_account.provider_user_id == "google_sub_123"
        assert auth_account.email == "gleb@test.com"
        assert auth_account.user_id == user.id

        refresh_token_res = await s.execute(select(RefreshToken))
        refresh_token = refresh_token_res.scalar_one()
        assert refresh_token.user_id == user.id

@pytest.mark.asyncio
async def test_username_conflict_gets_suffix(client):
    payload = {"username": "gleb", "password": "gleb321", "email": "gleb@test.com"}
    response = await client.post("/auth/register", json=payload)
    assert response.status_code == 200

    async with TestSessionLocal() as session:
        await login_with_verified_provider_identity(
            session=session,
            provider="google",
            provider_user_id="google_sub_123",
            email="gleb@service.com",
            email_verified=True
        )

        user_res = await session.execute(select(User).where(User.email == "gleb@service.com"))
        user = user_res.scalar_one()
        assert user.username == "gleb2"

@pytest.mark.asyncio
async def test_unverified_email_is_rejected():
    async with TestSessionLocal() as session:
        with pytest.raises(InvalidCredentialsError) as exc_info:
            await login_with_verified_provider_identity(
                session, "google", "google_sub_123",
                "gleb@service.com", False
            )
        assert str(exc_info.value) == "Verified email required"
        user_count = await session.scalar(select(func.count()).select_from(User))
        auth_account_count = await session.scalar(select(func.count()).select_from(AuthAccount))
        refresh_token_count = await session.scalar(select(func.count()).select_from(RefreshToken))

        assert user_count == 0
        assert auth_account_count == 0
        assert refresh_token_count == 0
