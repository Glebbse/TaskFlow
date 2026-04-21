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
