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
async def test_valid_refresh_token_returns_access_token_and_new_refresh_token(client, create_user):
    payload = {"username": "gleb", "password": "gleb123"}
    user = await create_user(payload)
    refresh_token_1 = user["refresh_token"]
    refresh_token_1_hash = hash_refresh_token(refresh_token_1)

    refresh_response = await client.post("/auth/refresh", json={"refresh_token": refresh_token_1})
    assert refresh_response.status_code == 200
    tokens = refresh_response.json()


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
    assert "refresh_token" in tokens
    assert "access_token" in tokens
    assert hash_refresh_token(tokens["refresh_token"]) == refresh_token_2.token_hash
    assert tokens["refresh_token"] != refresh_token_1

@pytest.mark.asyncio
async def test_old_refresh_token_cannot_be_used_again(client, create_user):
    payload = {"username": "gleb", "password": "gleb123"}
    user = await create_user(payload)
    old_refresh_token = user["refresh_token"]
    old_refresh_token_hash = hash_refresh_token(old_refresh_token)

    first_refresh_response = await client.post("/auth/refresh", json={"refresh_token": old_refresh_token})
    assert first_refresh_response.status_code == 200
    new_refresh_token = first_refresh_response.json()["refresh_token"]
    assert new_refresh_token != old_refresh_token


    async with TestSessionLocal() as session:
        q = await session.execute(select(RefreshToken).where(RefreshToken.token_hash == old_refresh_token_hash))
        old_refresh_token_db = q.scalar_one()
        assert old_refresh_token_db.revoked_at is not None

    second_refresh_response_with_old_token = await client.post("/auth/refresh", json={"refresh_token": old_refresh_token})
    assert second_refresh_response_with_old_token.status_code == 401
    assert second_refresh_response_with_old_token.json()["detail"] == "Invalid refresh token"

@pytest.mark.asyncio
async def test_new_refresh_token_can_be_used(client, create_user):
    payload = {"username": "gleb", "password": "gleb123"}
    user = await create_user(payload)
    old_refresh_token = user["refresh_token"]

    first_refresh_response = await client.post("/auth/refresh", json={"refresh_token": old_refresh_token})
    assert first_refresh_response.status_code == 200
    new_refresh_token = first_refresh_response.json()["refresh_token"]
    assert new_refresh_token != old_refresh_token

    second_refresh_response = await client.post("/auth/refresh", json={"refresh_token": new_refresh_token})
    assert second_refresh_response.status_code == 200
    assert second_refresh_response.json()["refresh_token"] != new_refresh_token

@pytest.mark.asyncio
async def test_rotated_refresh_token_keeps_original_expiration(client, create_user):
    payload = {"username": "gleb", "password": "gleb123"}
    user = await create_user(payload)
    first_refresh_token = user["refresh_token"]
    first_refresh_token_hash = hash_refresh_token(first_refresh_token)

    async with TestSessionLocal() as session:
        q = await session.execute(select(RefreshToken.expires_at).where(RefreshToken.token_hash == first_refresh_token_hash))
        original_expires_at = q.scalar_one()

    refresh_response = await client.post("/auth/refresh", json={"refresh_token": first_refresh_token})
    assert refresh_response.status_code == 200
    second_refresh_token = refresh_response.json()["refresh_token"]
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

    first_refresh_response = await client.post("/auth/refresh", json={"refresh_token": first_refresh_token})
    assert first_refresh_response.status_code == 200
    second_refresh_token = first_refresh_response.json()["refresh_token"]

    reuse_response = await client.post("/auth/refresh", json={"refresh_token": first_refresh_token})
    assert reuse_response.status_code == 401
    assert reuse_response.json()["detail"] == "Invalid refresh token"

    async with TestSessionLocal() as s:
        q = await s.execute(select(RefreshToken).where(RefreshToken.user_id == user["user_data"]["id"]))
        result = list(q.scalars())

    assert len(result) == 2
    assert all(token.revoked_at is not None for token in result)

    new_response = await client.post("/auth/refresh", json={"refresh_token": second_refresh_token})
    assert new_response.status_code == 401
    assert new_response.json()["detail"] == "Invalid refresh token"



