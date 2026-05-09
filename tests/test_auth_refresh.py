import pytest
from sqlalchemy import select

from datetime import datetime, timezone, timedelta

from app.core.security import hash_refresh_token
from app.models.refresh_token import RefreshToken
from tests.conftest import client, TestSessionLocal

@pytest.mark.asyncio
async def test_login_returns_access_and_refresh_tokens(client):
    payload = {"username": "gleb", "password": "gleb123"}

    reg_response = await client.post("/auth/register", json=payload)
    assert reg_response.status_code == 200

    login_response = await client.post("/auth/login", json=payload)
    assert login_response.status_code == 200

    data = login_response.json()
    assert "access_token" in data
    assert "refresh_token" not in data
    assert login_response.cookies.get("taskflow_refresh_token") is not None
    assert data["token_type"] == "bearer"

@pytest.mark.asyncio
async def test_refresh_access_token_refresh_invalid_refresh_token_401(client):
    user_register = await client.post("/auth/register", json={"username": "gleb", "password": "gleb321"})
    assert user_register.status_code == 200

    refresh_response = await client.post("/auth/refresh", headers={"Cookie": "taskflow_refresh_token=abcdefghijkl"})
    assert refresh_response.status_code == 401
    assert refresh_response.json()["detail"] == "Invalid refresh token"

@pytest.mark.asyncio
async def test_refresh_access_token_expired_401(client):
    register_response = await client.post("/auth/register", json={"username": "gleb", "password": "gleb321"})
    assert register_response.status_code == 200

    login_response = await client.post("/auth/login", json={"username": "gleb", "password": "gleb321"})
    assert login_response.status_code == 200
    refresh_token_raw = login_response.cookies.get("taskflow_refresh_token")
    assert refresh_token_raw is not None
    refresh_token_hash = hash_refresh_token(refresh_token_raw)

    async with TestSessionLocal() as session:
        res = await session.execute(select(RefreshToken).where(RefreshToken.token_hash == refresh_token_hash))
        refresh_token_db = res.scalar_one_or_none()
        assert refresh_token_db is not None

        refresh_token_db.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        await session.commit()

    refresh_response = await client.post("/auth/refresh", headers={"Cookie": f"taskflow_refresh_token={refresh_token_raw}"})
    assert refresh_response.status_code == 401
    assert refresh_response.json()["detail"] == "Invalid refresh token"


@pytest.mark.asyncio
async def test_valid_refresh_token_returns_access_token_and_new_refresh_token(client, create_user):
    payload = {"username": "gleb", "password": "gleb123"}
    user = await create_user(payload)
    refresh_token_1 = user["refresh_token"]
    refresh_token_1_hash = hash_refresh_token(refresh_token_1)

    refresh_response = await client.post("/auth/refresh", headers={"Cookie": f"taskflow_refresh_token={refresh_token_1}"})
    assert refresh_response.status_code == 200
    tokens = refresh_response.json()
    refresh_token_2_raw = refresh_response.cookies.get("taskflow_refresh_token")
    assert refresh_token_2_raw is not None


    async with TestSessionLocal() as session:
        q1 = await session.execute(select(RefreshToken).where(RefreshToken.user_id == user["user_data"]["id"]))
        db_tokens = list(q1.scalars())
        assert len(db_tokens) == 2

        q2 = await session.execute(select(RefreshToken).where(RefreshToken.token_hash == refresh_token_1_hash))
        revoked_token = q2.scalar_one()
        assert revoked_token.revoked_at is not None

        q3 = await session.execute(select(RefreshToken).where(RefreshToken.revoked_at.is_(None),
                                                              RefreshToken.user_id == user["user_data"]["id"]))
        refresh_token_2 = q3.scalar_one()

    assert revoked_token.expires_at == refresh_token_2.expires_at
    assert "refresh_token" not in tokens
    assert "access_token" in tokens
    assert hash_refresh_token(refresh_token_2_raw) == refresh_token_2.token_hash
    assert refresh_token_2_raw != refresh_token_1

@pytest.mark.asyncio
async def test_old_refresh_token_cannot_be_used_again(client, create_user):
    payload = {"username": "gleb", "password": "gleb123"}
    user = await create_user(payload)
    old_refresh_token = user["refresh_token"]
    old_refresh_token_hash = hash_refresh_token(old_refresh_token)

    first_refresh_response = await client.post("/auth/refresh", headers={"Cookie": f"taskflow_refresh_token={old_refresh_token}"})
    assert first_refresh_response.status_code == 200
    new_refresh_token = first_refresh_response.cookies.get("taskflow_refresh_token")
    assert new_refresh_token is not None
    assert new_refresh_token != old_refresh_token


    async with TestSessionLocal() as session:
        q = await session.execute(select(RefreshToken).where(RefreshToken.token_hash == old_refresh_token_hash))
        old_refresh_token_db = q.scalar_one()
        assert old_refresh_token_db.revoked_at is not None

    second_refresh_response_with_old_token = await client.post("/auth/refresh", headers={"Cookie": f"taskflow_refresh_token={old_refresh_token}"})
    assert second_refresh_response_with_old_token.status_code == 401
    assert second_refresh_response_with_old_token.json()["detail"] == "Invalid refresh token"



@pytest.mark.asyncio
async def test_rotated_refresh_token_keeps_original_expiration(client, create_user):
    payload = {"username": "gleb", "password": "gleb123"}
    user = await create_user(payload)
    first_refresh_token = user["refresh_token"]
    first_refresh_token_hash = hash_refresh_token(first_refresh_token)

    async with TestSessionLocal() as session:
        q = await session.execute(select(RefreshToken.expires_at).where(RefreshToken.token_hash == first_refresh_token_hash))
        original_expires_at = q.scalar_one()

    refresh_response = await client.post("/auth/refresh", headers={"Cookie": f"taskflow_refresh_token={first_refresh_token}"})
    assert refresh_response.status_code == 200
    second_refresh_token = refresh_response.cookies.get("taskflow_refresh_token")
    assert second_refresh_token is not None
    second_refresh_token_hash = hash_refresh_token(second_refresh_token)

    async with TestSessionLocal() as session:
        q = await session.execute(select(RefreshToken.expires_at).where(RefreshToken.token_hash == second_refresh_token_hash))
        second_expires_at = q.scalar_one()

    assert second_expires_at == original_expires_at

@pytest.mark.asyncio
async def test_reuse_detection_behaviour(client, create_user):
    payload = {"username": "gleb", "password": "gleb123"}
    user = await create_user(payload)
    first_refresh_token = user["refresh_token"]

    first_refresh_response = await client.post("/auth/refresh", headers={"Cookie": f"taskflow_refresh_token={first_refresh_token}"})
    assert first_refresh_response.status_code == 200
    second_refresh_token = first_refresh_response.cookies.get("taskflow_refresh_token")
    assert second_refresh_token is not None

    reuse_response = await client.post("/auth/refresh", headers={"Cookie": f"taskflow_refresh_token={first_refresh_token}"})
    assert reuse_response.status_code == 401
    assert reuse_response.json()["detail"] == "Invalid refresh token"

    async with TestSessionLocal() as s:
        q = await s.execute(select(RefreshToken).where(RefreshToken.user_id == user["user_data"]["id"]))
        result = list(q.scalars())

    assert len(result) == 2
    assert all(token.revoked_at is not None for token in result)

    new_response = await client.post("/auth/refresh", headers={"Cookie": f"taskflow_refresh_token={second_refresh_token}"})
    assert new_response.status_code == 401
    assert new_response.json()["detail"] == "Invalid refresh token"

@pytest.mark.asyncio
async def test_new_refresh_token_can_be_used(client, create_user):
    payload = {"username": "gleb", "password": "gleb123"}
    user = await create_user(payload)
    old_refresh_token = user["refresh_token"]

    first_refresh_response = await client.post("/auth/refresh", headers={"Cookie": f"taskflow_refresh_token={old_refresh_token}"})
    assert first_refresh_response.status_code == 200
    new_refresh_token = first_refresh_response.cookies.get("taskflow_refresh_token")
    assert new_refresh_token is not None
    assert new_refresh_token != old_refresh_token

    second_refresh_response = await client.post("/auth/refresh", headers={"Cookie": f"taskflow_refresh_token={new_refresh_token}"})
    assert second_refresh_response.status_code == 200
    next_refresh_token = second_refresh_response.cookies.get("taskflow_refresh_token")
    assert next_refresh_token is not None
    assert next_refresh_token != new_refresh_token

@pytest.mark.asyncio
async def test_deletion_tokens_when_user_deleted(client, create_user):
    payload = {"username": "gleb", "password": "gleb123"}
    user = await create_user(payload)

    second_login = await client.post("/auth/login", json=payload)
    assert second_login.status_code == 200

    delete_response = await client.delete(f"/users/{user['user_data']['id']}", headers=user["headers"])
    assert delete_response.status_code == 200

    async with TestSessionLocal() as session:
        query = await session.execute(select(RefreshToken).where(RefreshToken.user_id == user["user_data"]["id"]))
        result = list(query.scalars())

    assert result == []

@pytest.mark.asyncio
async def test_refresh_without_cookie_returns_401(client):
    response = await client.post("/auth/refresh")

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid refresh token"


