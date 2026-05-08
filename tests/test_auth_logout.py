import pytest
from sqlalchemy import select

from app.core.security import hash_refresh_token
from app.models.refresh_token import RefreshToken
from tests.conftest import client, TestSessionLocal


@pytest.mark.asyncio
async def test_logout_idempotency(client, create_user):
    user = await create_user({"username": "gleb", "password": "gleb123"})

    logout_response = await client.post("/auth/logout", json={"refresh_token": user["refresh_token"]})
    assert logout_response.status_code == 200
    assert logout_response.json()["detail"] == "Logged out"

    refresh_token = user["refresh_token"]

    async with TestSessionLocal() as session:
        token_hash = hash_refresh_token(refresh_token)
        res = await session.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
        refresh_token_db = res.scalar_one_or_none()

        assert refresh_token_db is not None
        assert refresh_token_db.revoked_at is not None

    refresh_response = await client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_response.status_code == 401
    assert refresh_response.json()["detail"] == "Invalid refresh token"

    second_logout_response = await client.post(
        "/auth/logout",
        json={"refresh_token": refresh_token},
    )
    assert second_logout_response.status_code == 200
    assert second_logout_response.json()["detail"] == "Logged out"

    third_logout_response =  await client.post(
        "/auth/logout",
        json={"refresh_token": "not-a-real-token"},
    )
    assert third_logout_response.status_code == 200
    assert third_logout_response.json()["detail"] == "Logged out"



@pytest.mark.asyncio
async def test_logout_all(client, create_user):
    payload = {"username": "gleb", "password": "gleb123"}
    user = await create_user(payload)
    refresh_token_1 = user["refresh_token"]

    second_login = await client.post("/auth/login", json=payload)
    assert second_login.status_code == 200
    refresh_token_2 = second_login.json()["refresh_token"]

    logout_all_response = await client.post("/auth/logout-all", headers=user["headers"])
    assert logout_all_response.status_code == 200
    assert logout_all_response.json()["detail"] == "Logged out from all devices"

    async with TestSessionLocal() as session:
        res = await session.execute(select(RefreshToken).where(RefreshToken.user_id == user["user_data"]["id"]))
        refresh_tokens = list(res.scalars())

    assert all(token.revoked_at is not None for token in refresh_tokens)
    assert len(refresh_tokens) == 2


    refresh_response_1 = await client.post("/auth/refresh", json={"refresh_token": refresh_token_1})
    assert refresh_response_1.status_code == 401
    assert refresh_response_1.json()["detail"] == "Invalid refresh token"

    refresh_response_2 = await client.post("/auth/refresh", json={"refresh_token": refresh_token_2})
    assert refresh_response_2.status_code == 401
    assert refresh_response_2.json()["detail"] == "Invalid refresh token"



@pytest.mark.asyncio
async def test_logout_all_not_revoke_already_revoked_tokens(client, create_user):
    payload = {"username": "gleb", "password": "gleb123"}
    user = await create_user(payload)
    refresh_token_1 = user["refresh_token"]
    refresh_token_1_hash = hash_refresh_token(refresh_token_1)

    second_login = await client.post("/auth/login", json=payload)
    assert second_login.status_code == 200
    refresh_token_2 = second_login.json()["refresh_token"]
    refresh_token_2_hash = hash_refresh_token(refresh_token_2)

    logout_response = await client.post("/auth/logout", json={"refresh_token": refresh_token_1})
    assert logout_response.status_code == 200
    assert logout_response.json()["detail"] == "Logged out"

    async with TestSessionLocal() as session:
        res = await session.execute(select(RefreshToken)
                                    .where(RefreshToken.token_hash == refresh_token_1_hash))
        refresh_token_db_1 = res.scalar_one()
        assert refresh_token_db_1.revoked_at is not None
        first_revoked_at = refresh_token_db_1.revoked_at

    logout_all_response = await client.post("/auth/logout-all", headers=user["headers"])
    assert logout_all_response.status_code == 200
    assert logout_all_response.json()["detail"] == "Logged out from all devices"

    async with TestSessionLocal() as session:
        res = await session.execute(select(RefreshToken)
                                    .where(RefreshToken.token_hash == refresh_token_2_hash))
        refresh_token_2_after_logout_all = res.scalar_one()
        assert refresh_token_2_after_logout_all.revoked_at is not None

        res_ = await session.execute(select(RefreshToken)
                                    .where(RefreshToken.token_hash == refresh_token_1_hash))

        refresh_token_1_after_logout_all = res_.scalar_one()

    assert refresh_token_1_after_logout_all.revoked_at == first_revoked_at
    assert refresh_token_2_after_logout_all.revoked_at is not None

