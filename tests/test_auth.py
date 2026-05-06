from datetime import datetime, timezone

import pytest
from asyncpg.pgproto.pgproto import timedelta
from sqlalchemy import select

from app.core.security import hash_refresh_token
from app.models.refresh_token import RefreshToken
from tests.conftest import client, TestSessionLocal


@pytest.mark.asyncio
async def test_register_user(client):
    response = await client.post("/auth/register", json={
        "username": "gleb",
        "password": "gleb123"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "gleb"
    assert "id" in data
    assert "password" not in data
    assert "hashed_password" not in data

@pytest.mark.asyncio
async def test_register_duplicate_username_returns_409(client):
    payload = {"username": "gleb", "password": "gleb123"}

    first_response = await client.post("/auth/register", json=payload)
    assert first_response.status_code == 200

    second_response = await client.post("/auth/register", json=payload)
    assert second_response.status_code == 409

    data = second_response.json()

    assert "detail" in data

@pytest.mark.asyncio
async def test_login_returns_access_and_refresh_tokens(client):
    payload = {"username": "gleb", "password": "gleb123"}

    reg_response = await client.post("/auth/register", json=payload)
    assert reg_response.status_code == 200

    login_response = await client.post("/auth/login", json=payload)
    assert login_response.status_code == 200

    data = login_response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"

@pytest.mark.asyncio
async def test_login_with_invalid_credentials_returns_401(client):
    reg_payload = {"username": "gleb", "password": "gleb123"}
    wrong_pw_payload = {"username": "gleb", "password": "gleb122"}
    wrong_username_payload = {"username": "glwb", "password": "gleb123"}

    reg_response = await client.post("/auth/register", json=reg_payload)
    assert reg_response.status_code == 200

    wrong_pw_response = await client.post("/auth/login", json=wrong_pw_payload)
    assert wrong_pw_response.status_code == 401
    data1 = wrong_pw_response.json()
    assert data1["detail"] == "Invalid username or password"

    wrong_username_response = await client.post("/auth/login", json=wrong_username_payload)
    assert wrong_username_response.status_code == 401
    data2 = wrong_username_response.json()
    assert data2["detail"] == "Invalid username or password"

@pytest.mark.asyncio
async def test_user_cannot_access_another_user_data(client):
    user1 = {"username": "gleb", "password": "gleb123"}
    user1_register_response = await client.post("/auth/register", json=user1)
    assert user1_register_response.status_code == 200
    # data_user1 = user1_register_response.json()

    user2 = {"username": "tom", "password": "thomas123"}
    user2_register_response = await client.post("/auth/register", json=user2)
    assert user2_register_response.status_code == 200
    data_user2 = user2_register_response.json()

    login_user1 = await client.post("/auth/login", json=user1)
    assert login_user1.status_code == 200
    token_data_user1 = login_user1.json()
    token = token_data_user1["access_token"]
    user1_headers = {"Authorization": f"Bearer {token}"}

    user1_request = await client.get(f"/users/{data_user2["id"]}", headers=user1_headers)
    assert user1_request.status_code == 403
    request_data = user1_request.json()
    assert request_data["detail"] == "Forbidden"

@pytest.mark.asyncio
async def test_user_can_access_own_data(client):
    user = {"username": "gleb", "password": "gleb123"}

    user_register = await client.post("/auth/register", json=user)
    assert user_register.status_code == 200
    user_data = user_register.json()

    user_login = await client.post("/auth/login", json=user)
    assert user_login.status_code == 200
    user_token = user_login.json()["access_token"]

    headers = {"Authorization": f"Bearer {user_token}"}

    request = await client.get(f"/users/{user_data["id"]}", headers=headers)
    assert request.status_code == 200
    data = request.json()
    assert data["id"] == user_data["id"]
    assert data["username"] == user_data["username"]

@pytest.mark.asyncio
async def test_get_user_requires_authentication(client):
    user = {"username": "gleb", "password": "gleb123"}

    user_register = await client.post("/auth/register", json=user)
    assert user_register.status_code == 200
    user_data = user_register.json()

    request = await client.get(f"/users/{user_data["id"]}")
    assert request.status_code == 401

@pytest.mark.asyncio
async def test_register_duplicate_username_returns_409(client, create_user):
    await create_user({"username": "gleb", "password": "gleb321"})

    response = await client.post(
        "/auth/register",
        json={"username": "gleb", "password": "another321"},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Username gleb already exists"

@pytest.mark.asyncio
async def test_login_stores_hashed_refresh_token(client, create_user):
    payload = {"username": "gleb", "password": "gleb321"}
    register_response = await client.post("/auth/register", json=payload)
    assert register_response.status_code == 200

    login_response = await client.post("/auth/login", json=payload)
    assert login_response.status_code == 200
    refresh_token = login_response.json()["refresh_token"]

    async with TestSessionLocal() as session:
        result = await session.execute(select(RefreshToken))
        refresh_token_in_db = result.scalar_one()

    assert hash_refresh_token(refresh_token) == refresh_token_in_db.token_hash
    assert register_response.json()["id"] == refresh_token_in_db.user_id
    assert refresh_token != refresh_token_in_db.token_hash

@pytest.mark.asyncio
async def test_refresh_access_token_refresh_invalid_refresh_token_401(client):
    user_register = await client.post("/auth/register", json={"username": "gleb", "password": "gleb321"})
    assert user_register.status_code == 200

    refresh_response = await client.post("/auth/refresh", json={"refresh_token": "abcdefghijkl"})
    assert refresh_response.status_code == 401
    assert refresh_response.json()["detail"] == "Invalid refresh token"

@pytest.mark.asyncio
async def test_refresh_access_token_expired_401(client):
    register_response = await client.post("/auth/register", json={"username": "gleb", "password": "gleb321"})
    assert register_response.status_code == 200

    login_response = await client.post("/auth/login", json={"username": "gleb", "password": "gleb321"})
    assert login_response.status_code == 200
    refresh_token_raw = login_response.json()["refresh_token"]
    refresh_token_hash = hash_refresh_token(refresh_token_raw)

    async with TestSessionLocal() as session:
        res = await session.execute(select(RefreshToken).where(RefreshToken.token_hash == refresh_token_hash))
        refresh_token_db = res.scalar_one_or_none()
        assert refresh_token_db is not None

        refresh_token_db.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        await session.commit()

    refresh_response = await client.post("/auth/refresh", json={"refresh_token": refresh_token_raw})
    assert refresh_response.status_code == 401
    assert refresh_response.json()["detail"] == "Invalid refresh token"

@pytest.mark.asyncio
async def test_logout(client, create_user):
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

