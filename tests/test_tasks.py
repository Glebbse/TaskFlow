import pytest


@pytest.mark.asyncio
async def test_create_task_for_auth_user(client, create_user):
    user = await create_user({"username": "gleb", "password": "gleb123"})

    task_payload = {"title": "test", "description": "description"}

    create_task_request = await client.post("/tasks", json=task_payload, headers=user["headers"])
    assert create_task_request.status_code == 201
    task_data = create_task_request.json()

    assert task_data["user_id"] == user["user_data"]["id"]

@pytest.mark.asyncio
async def test_create_task_requires_auth_401(client):
    task_payload = {"title": "test", "description": "description"}

    request = await client.post("/tasks", json=task_payload)
    assert request.status_code == 401

@pytest.mark.asyncio
async def test_get_list_of_tasks_for_auth_user(client, create_user):
    user = await create_user({"username": "gleb", "password": "gleb123"})

    params = {"limit": 5, "offset": 0}
    task_payload = {"title": "test", "description": "description"}

    task_create = await client.post("/tasks", json=task_payload, headers=user["headers"])
    assert task_create.status_code == 201

    request = await client.get("/tasks", params=params, headers=user["headers"])
    assert request.status_code == 200
    tasks_list_data = request.json()["items"]

    assert all(task["user_id"] == user["user_data"]["id"] for task in tasks_list_data)

@pytest.mark.asyncio
async def test_get_list_of_tasks_requires_auth_401(client):
    params = {"limit": 5, "offset": 0}

    request = await client.get("/tasks", params=params)
    assert request.status_code == 401

@pytest.mark.asyncio
async def test_get_task_requires_auth_401(client, create_user):
    user = await create_user({"username": "gleb", "password": "gleb123"})

    task_payload = {"title": "test", "description": "description"}
    create_task = await client.post("/tasks", json=task_payload, headers=user["headers"])
    assert create_task.status_code == 201
    task_id = create_task.json()["id"]

    request = await client.get(f"/tasks/{task_id}")
    assert request.status_code == 401
    request_data = request.json()
    assert request_data["detail"] == "Not authenticated"


@pytest.mark.asyncio
async def test_user_cannot_access_another_users_task_403(client, create_user):
    user_a = await create_user({"username": "gleb", "password": "gleb123"})
    user_b = await create_user({"username": "anna", "password": "anna4321"})

    task_payload = {"title": "test", "description": "description"}

    task_create = await client.post("/tasks", json=task_payload, headers=user_b["headers"])
    assert task_create.status_code == 201
    task_id_user_b = task_create.json()["id"]


    user_a_request = await client.get(f"/tasks/{task_id_user_b}", headers=user_a["headers"])
    assert user_a_request.status_code == 403
    user_a_request_data = user_a_request.json()
    assert user_a_request_data["detail"] == "Forbidden"

    user_b_request = await client.get(f"/tasks/{task_id_user_b}", headers=user_b["headers"])
    assert user_b_request.status_code == 200
    user_b_request_data = user_b_request.json()
    assert user_b_request_data["user_id"] == user_b["user_data"]["id"]

@pytest.mark.asyncio
async def test_delete_task_for_auth_user(client, create_user):
    user_a = await create_user({"username": "gleb", "password": "gleb123"})

    task_payload = {"title": "test", "description": "description"}

    request = await client.post("/tasks", json=task_payload, headers=user_a["headers"])
    assert request.status_code == 201
    task_id = request.json()["id"]

    delete_auth_request = await client.delete(f"/tasks/{task_id}", headers=user_a["headers"])
    assert delete_auth_request.status_code == 200
    deleted_task = delete_auth_request.json().get("deleted")
    assert deleted_task["user_id"] == user_a["user_data"]["id"]

@pytest.mark.asyncio
async def test_delete_task_for_unauthenticated_user_401(client):
    delete_request_error = await client.delete(f"/tasks/10")
    assert delete_request_error.status_code == 401
    error = delete_request_error.json()
    assert error["detail"] == "Not authenticated"

@pytest.mark.asyncio
async def test_update_task_requires_auth_error_401(client, create_user):
    user = await create_user({"username": "gleb", "password": "gleb123"})

    task_payload = {"title": "test", "description": "description"}
    create_task_request = await client.post("/tasks", json=task_payload, headers=user["headers"])
    assert create_task_request.status_code == 201
    task = create_task_request.json()

    task_update_payload = {"is_done": True}

    update_task_error = await client.patch(f"/tasks/{task['id']}", json=task_update_payload)
    assert update_task_error.status_code == 401

@pytest.mark.asyncio
async def test_update_task_for_auth_user(client, create_user):
    user = await create_user({"username": "gleb", "password": "gleb123"})

    task_payload = {"title": "test", "description": "description"}
    create_task_request = await client.post("/tasks", json=task_payload, headers=user["headers"])
    assert create_task_request.status_code == 201
    task = create_task_request.json()

    task_update_payload = {"is_done": True}
    update_task_request = await client.patch(f"/tasks/{task['id']}", json=task_update_payload, headers=user["headers"])
    assert update_task_request.status_code == 200
    updated_task = update_task_request.json()

    assert updated_task["user_id"] == user["user_data"]["id"]

@pytest.mark.asyncio
async def test_user_cannot_update_another_users_tasks_403(client, create_user):
    user_a = await create_user({"username": "gleb", "password": "gleb123"})
    user_b = await create_user({"username": "ivan", "password": "ivan123"})

    task_payload = {"title": "test", "description": "description"}
    create_task_request = await client.post("/tasks", json=task_payload, headers=user_a["headers"])
    assert create_task_request.status_code == 201
    task = create_task_request.json()

    task_update_payload = {"is_done": True}
    update_task_request_error = await client.patch(f"/tasks/{task['id']}", json=task_update_payload, headers=user_b["headers"])
    assert update_task_request_error.status_code == 403
    forbidden = update_task_request_error.json()
    assert forbidden["detail"] == "Forbidden"
