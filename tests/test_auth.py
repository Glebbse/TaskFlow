import pytest


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
async def test_login_returns_access_token(client):
    payload = {"username": "gleb", "password": "gleb123"}

    reg_response = await client.post("/auth/register", json=payload)
    assert reg_response.status_code == 200

    login_response = await client.post("/auth/login", json=payload)
    assert login_response.status_code == 200

    data = login_response.json()
    assert "access_token" in data
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

