import pytest


@pytest.mark.asyncio
async def test_get_me_returns_current_user(client, create_user):
    user = await create_user({"username": "gleb", "password": "gleb321"})

    request = await client.get("/users/me", headers=user["headers"])
    assert request.status_code == 200
    user_info = request.json()

    assert user_info["id"] == user["user_data"]["id"]
    assert user_info["username"] == user["user_data"]["username"]

@pytest.mark.asyncio
async def test_get_me_requires_auth(client, create_user):
    request = await client.get("/users/me")
    assert request.status_code == 401
    auth_error = request.json()

    assert auth_error["detail"] == "Not authenticated"

@pytest.mark.asyncio
async def test_get_me_reuqires_valid_token_401(client, create_user):
    broken_token = "abc.def.ghi"
    headers = {"Authorization": f"Bearer {broken_token}"}
    request = await client.get("/users/me", headers=headers)
    assert request.status_code == 401
    invalid_token_error = request.json()
    assert invalid_token_error["detail"] == "Could not validate credentials"
