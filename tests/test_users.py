import pytest

from datetime import timedelta

from sqlalchemy import select

from app.core.security import create_access_token
from app.models.task import Task
from tests.conftest import TestSessionLocal, make_user_admin


@pytest.mark.asyncio
async def test_get_me_returns_current_user(client, create_user):
    user = await create_user({"username": "gleb", "password": "gleb321"})

    request = await client.get("/users/me", headers=user["headers"])
    assert request.status_code == 200
    user_info = request.json()

    assert user_info["id"] == user["user_data"]["id"]
    assert user_info["username"] == user["user_data"]["username"]
    assert user_info["role"] == "user"

@pytest.mark.asyncio
async def test_get_me_requires_auth(client):
    request = await client.get("/users/me")
    assert request.status_code == 401
    auth_error = request.json()

    assert auth_error["detail"] == "Not authenticated"

@pytest.mark.asyncio
async def test_get_me_requires_valid_token_401(client):
    broken_token = "abc.def.ghi"
    headers = {"Authorization": f"Bearer {broken_token}"}
    request = await client.get("/users/me", headers=headers)
    assert request.status_code == 401
    invalid_token_error = request.json()
    assert invalid_token_error["detail"] == "Could not validate credentials"

@pytest.mark.asyncio
async def test_get_all_users_requires_auth(client):
    request = await client.get("/users")
    assert request.status_code == 401
    auth_error = request.json()

    assert auth_error["detail"] == "Not authenticated"

@pytest.mark.asyncio
async def test_get_all_users_requires_admin_rights(client, create_user):
    user = await create_user({"username": "gleb", "password": "gleb321"})

    request = await client.get("/users", headers=user["headers"])
    assert request.status_code == 403
    auth_error = request.json()

    assert auth_error["detail"] == "Forbidden"


@pytest.mark.asyncio
async def test_get_all_users_200(client, create_user, make_user_admin):
    admin = await create_user({"username": "gleb", "password": "gleb321"})
    await make_user_admin(admin["user_data"]["id"])
    request = await client.get("/users", headers=admin["headers"])
    assert request.status_code == 200
    response = request.json()
    assert "items" in response
    assert "total" in response
    assert any(admin["user_data"]["id"] == item["id"]
               and item["username"] == admin["user_data"]["username"] for item in response["items"])


@pytest.mark.asyncio
async def test_get_user_by_id_user_requires_auth(client, create_user):
    user = await create_user({"username": "gleb", "password": "gleb321"})
    user_id = user["user_data"]["id"]
    request = await client.get(f"/users/{user_id}")
    assert request.status_code == 401

@pytest.mark.asyncio
async def test_get_user_by_id_user_cannot_access_another_user_id(client, create_user):
    user_a = await create_user({"username": "gleb", "password": "gleb321"})
    user_a_id = user_a["user_data"]["id"]
    user_b = await create_user({"username": "anna", "password": "anna321"})

    request = await client.get(f"/users/{user_a_id}", headers=user_b["headers"])
    assert request.status_code == 403
    assert request.json()["detail"] == "Forbidden"

@pytest.mark.asyncio
async def test_get_user_by_id_user_not_found(client, create_user, make_user_admin):
    admin = await create_user({"username": "gleb", "password": "gleb321"})
    await make_user_admin(admin["user_data"]["id"])
    fake_id = 100
    request = await client.get(f"/users/{fake_id}", headers=admin["headers"])
    assert request.status_code == 404
    assert request.json()["detail"] == f"User with id {fake_id} not found"

@pytest.mark.asyncio
async def test_get_user_by_id_200(client, create_user, make_user_admin):
    admin = await create_user({"username": "gleb", "password": "gleb321"})
    await make_user_admin(admin["user_data"]["id"])
    user = await create_user({"username": "anna", "password": "anna321"})

    user_request = await client.get(f"/users/{user['user_data']['id']}", headers=user["headers"])
    assert user_request.status_code == 200
    user_request_data = user_request.json()
    assert user["user_data"]["id"] == user_request_data["id"]

    admin_request = await client.get(f"/users/{user['user_data']['id']}", headers=admin["headers"])
    assert admin_request.status_code == 200
    admin_request_data = admin_request.json()
    assert user["user_data"]["id"] == admin_request_data["id"]

@pytest.mark.asyncio
async def test_get_me_with_expired_token_returns_401(client, create_user):
    user = await create_user({"username": "gleb", "password": "gleb321"})
    user_id = user["user_data"]["id"]

    expired_token = create_access_token({"sub": str(user_id)}, expires_delta=timedelta(minutes=-1))
    headers = {"Authorization": f"Bearer {expired_token}"}

    request = await client.get("/users/me", headers=headers)
    assert request.status_code == 401
    assert request.json()["detail"] == "Could not validate credentials"

@pytest.mark.asyncio
async def test_user_can_delete_self(client, create_user, make_user_admin):
    user_a = await create_user({"username": "gleb", "password": "gleb321"})
    admin = await create_user({"username": "admin", "password": "admin321"})
    await make_user_admin(admin["user_data"]["id"])

    for title in ["1st", "2nd"]:
        response = await client.post("/tasks",
                                     json={"title": title, "description": "description"},
                                     headers=user_a["headers"])
        assert response.status_code == 201

    delete_a_response = await client.delete(f"/users/{user_a['user_data']['id']}",
                                   headers=user_a["headers"])
    assert delete_a_response.status_code == 200
    deleted_user_a = delete_a_response.json()["deleted"]
    assert deleted_user_a["id"] == user_a["user_data"]["id"]
    assert deleted_user_a["username"] == user_a["user_data"]["username"]

    async with TestSessionLocal() as session:
        res = await session.execute(select(Task).where(Task.user_id == user_a["user_data"]["id"]))
        remaining_tasks = list(res.scalars())

    assert remaining_tasks == []

    check_user = await client.get(f"/users/{user_a['user_data']['id']}", headers=admin["headers"])
    assert check_user.status_code == 404

    check_user_ = await client.get(f"/users/me", headers=user_a["headers"])
    assert check_user_.status_code == 401
    assert check_user_.json()["detail"] == "Could not validate credentials"

@pytest.mark.asyncio
async def test_admin_delete_user(client, create_user, make_user_admin):
    user_b = await create_user({"username": "anna", "password": "anna321"})
    admin = await create_user({"username": "admin", "password": "admin321"})
    await make_user_admin(admin["user_data"]["id"])

    for title in ["1st", "2nd"]:
        response = await client.post("/tasks",
                                     json={"title": title, "description": "description"},
                                     headers=user_b["headers"])
        assert response.status_code == 201

    delete_admin_response = await client.delete(f"/users/{user_b['user_data']['id']}",
                                   headers=admin["headers"])
    assert delete_admin_response.status_code == 200
    deleted_user_b = delete_admin_response.json()["deleted"]
    assert deleted_user_b["id"] == user_b["user_data"]["id"]
    assert deleted_user_b["username"] == user_b["user_data"]["username"]

    async with TestSessionLocal() as session:
        res = await session.execute(select(Task).where(Task.user_id == user_b["user_data"]["id"]))
        remaining_tasks = list(res.scalars())

    assert remaining_tasks == []

@pytest.mark.asyncio
async def test_user_cannot_delete_other_user(client, create_user):
    user_a = await create_user({"username": "gleb", "password": "gleb321"})
    user_b = await create_user({"username": "anna", "password": "anna321"})

    created_tasks = []
    for title in ["1st", "2nd"]:
        response = await client.post("/tasks",
                                     json={"title": title, "description": "description"},
                                     headers=user_a["headers"])
        assert response.status_code == 201
        task = response.json()
        created_tasks.append(task)

    delete_403 = await client.delete(f"/users/{user_a['user_data']['id']}",
                                   headers=user_b["headers"])
    assert delete_403.status_code == 403

    user_a_tasks_response = await client.get("/tasks", headers=user_a["headers"])
    assert user_a_tasks_response.status_code == 200
    user_a_tasks = user_a_tasks_response.json()["items"]

    assert [item["id"] for item in user_a_tasks] == [task["id"] for task in created_tasks]
    assert [item["title"] for item in user_a_tasks] == ["1st", "2nd"]

@pytest.mark.asyncio
async def test_admin_delete_missing_user_returns_404(client, create_user, make_user_admin):
    admin = await create_user({"username": "admin", "password": "admin321"})
    await make_user_admin(admin["user_data"]["id"])
    missing_id = 123

    delete_404 = await client.delete(f"/users/{missing_id}", headers=admin["headers"])
    assert delete_404.status_code == 404
    assert delete_404.json()["detail"] == f"User with id {missing_id} not found"

@pytest.mark.asyncio
async def test_user_update_psw_200(client, create_user):
    user_a = await create_user({"username": "gleb", "password": "gleb321"})

    payload = {"current_password": "gleb321", "new_password": "GLEB9191"}
    update_response = await client.patch("/users/me/password", json=payload, headers=user_a["headers"])
    assert update_response.status_code == 200
    updated_data = update_response.json()
    assert updated_data["detail"] == "Password updated"

    login_response_new_psw = await client.post("/auth/login", json={"username": "gleb", "password": "GLEB9191"})
    assert login_response_new_psw.status_code == 200
    assert "access_token" in login_response_new_psw.json()

    login_response_old_psw = await client.post("/auth/login", json={"username": "gleb", "password": "gleb321"})
    assert login_response_old_psw.status_code == 401
    assert login_response_old_psw.json()["detail"] == "Invalid username or password"


@pytest.mark.asyncio
async def test_user_update_psw_wrong_psw_401(client, create_user):
    user_a = await create_user({"username": "gleb", "password": "gleb321"})

    payload = {"current_password": "gleb311", "new_password": "GLEB9191"}
    update_response = await client.patch("/users/me/password", json=payload, headers=user_a["headers"])
    assert update_response.status_code == 401
    updated_data = update_response.json()
    assert updated_data["detail"] == "Invalid current password"

@pytest.mark.asyncio
async def test_user_update_psw_requires_authentication(client, create_user):
    user_a = await create_user({"username": "gleb", "password": "gleb321"})

    payload = {"current_password": "gleb311", "new_password": "GLEB9191"}
    update_response = await client.patch("/users/me/password", json=payload)
    assert update_response.status_code == 401
    updated_data = update_response.json()
    assert updated_data["detail"] == "Not authenticated"

@pytest.mark.asyncio
async def test_user_update_password_same_password_400(client, create_user):
    user_a = await create_user({"username": "gleb", "password": "gleb321"})

    payload = {"current_password": "gleb321", "new_password": "gleb321"}
    update_response = await client.patch("/users/me/password", json=payload, headers=user_a["headers"])
    assert update_response.status_code == 400
    updated_data = update_response.json()
    assert updated_data["detail"] == "New password must be different from current password"

@pytest.mark.asyncio
async def test_user_update_password_validation_error_422(client, create_user):
    user = await create_user({"username": "gleb", "password": "gleb321"})

    response = await client.patch(
        "/users/me/password",
        json={"current_password": "gleb321", "new_password": "123"},
        headers=user["headers"],
    )

    assert response.status_code == 422
