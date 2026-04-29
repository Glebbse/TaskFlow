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
