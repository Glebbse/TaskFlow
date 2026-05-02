from functools import reduce
from operator import index

import pytest


@pytest.mark.asyncio
async def test_create_task_for_auth_user(client, create_user):
    user = await create_user({"username": "gleb", "password": "gleb123"})

    task_payload = {"title": "test", "description": "description"}

    create_task_request = await client.post("/tasks", json=task_payload, headers=user["headers"])
    assert create_task_request.status_code == 201
    task_data = create_task_request.json()

    assert task_data["user_id"] == user["user_data"]["id"]
    assert task_data["position"] == 1

@pytest.mark.asyncio
async def test_task_positions_are_sequential_per_user(client, create_user):
    user_a = await create_user({"username": "gleb", "password": "gleb123"})
    user_b = await create_user({"username": "anna", "password": "anna4321"})

    first_user_a_task = await client.post(
        "/tasks",
        json={"title": "first", "description": "description"},
        headers=user_a["headers"],
    )
    assert first_user_a_task.status_code == 201

    second_user_a_task = await client.post(
        "/tasks",
        json={"title": "second", "description": "description"},
        headers=user_a["headers"],
    )
    assert second_user_a_task.status_code == 201

    first_user_b_task = await client.post(
        "/tasks",
        json={"title": "first", "description": "description"},
        headers=user_b["headers"],
    )
    assert first_user_b_task.status_code == 201

    assert first_user_a_task.json()["position"] == 1
    assert second_user_a_task.json()["position"] == 2
    assert first_user_b_task.json()["position"] == 1

@pytest.mark.asyncio
async def test_deleting_task_shifts_later_positions_for_same_user(client, create_user):
    user_a = await create_user({"username": "gleb", "password": "gleb123"})
    user_b = await create_user({"username": "anna", "password": "anna4321"})

    user_a_tasks = []
    for title in ["first", "second", "third"]:
        response = await client.post(
            "/tasks",
            json={"title": title, "description": "description"},
            headers=user_a["headers"],
        )
        assert response.status_code == 201
        user_a_tasks.append(response.json())

    user_b_task = await client.post(
        "/tasks",
        json={"title": "other user", "description": "description"},
        headers=user_b["headers"],
    )
    assert user_b_task.status_code == 201

    delete_response = await client.delete(f"/tasks/{user_a_tasks[1]['id']}", headers=user_a["headers"])
    assert delete_response.status_code == 200
    assert delete_response.json()["deleted"]["position"] == 2
    assert delete_response.json()["deleted"]["title"] == "second"

    user_a_list = await client.get("/tasks", headers=user_a["headers"])
    assert user_a_list.status_code == 200
    user_a_items = user_a_list.json()["items"]

    user_b_list = await client.get("/tasks", headers=user_b["headers"])
    assert user_b_list.status_code == 200
    user_b_items = user_b_list.json()["items"]

    assert [task["title"] for task in user_a_items] == ["first", "third"]
    assert [task["position"] for task in user_a_items] == [1, 2]
    assert [task["position"] for task in user_b_items] == [1]

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
async def test_user_cannot_delete_another_users_task_401(client, create_user):
    user_a = await create_user({"username": "gleb", "password": "gleb123"})
    user_b = await create_user({"username": "anna", "password": "anna4321"})

    task_payload = {"title": "test", "description": "description"}
    create_task = await client.post("/tasks", json=task_payload, headers=user_a["headers"])
    assert create_task.status_code == 201
    task_id_user_a = create_task.json()["id"]

    delete_request = await client.delete(f"/tasks/{task_id_user_a}", headers=user_b["headers"])
    assert delete_request.status_code == 403
    forbidden = delete_request.json()
    assert forbidden["detail"] == "Forbidden"


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


@pytest.mark.asyncio
async def test_get_task_not_found_404(client, create_user):
    user = await create_user({"username": "gleb", "password": "gleb123"})

    missing_id = 5

    request = await client.get(f"/tasks/{missing_id}", headers=user["headers"])
    assert request.status_code == 404
    request_data = request.json()
    assert request_data["detail"] == f"Task with id {missing_id} not found"

@pytest.mark.asyncio
async def test_delete_task_not_found_404(client, create_user):
    user = await create_user({"username": "gleb", "password": "gleb123"})

    missing_id = 5

    request = await client.delete(f"/tasks/{missing_id}", headers=user["headers"])
    assert request.status_code == 404
    request_data = request.json()
    assert request_data["detail"] == f"Task with id {missing_id} not found"

@pytest.mark.asyncio
async def test_update_task_not_found_404(client, create_user):
    user = await create_user({"username": "gleb", "password": "gleb123"})

    missing_id = 5
    task_update_payload = {"is_done": True}

    request = await client.patch(f"/tasks/{missing_id}", json=task_update_payload, headers=user["headers"])
    assert request.status_code == 404
    request_data = request.json()
    assert request_data["detail"] == f"Task with id {missing_id} not found"


@pytest.mark.asyncio
async def test_search_in_tasks_for_user(client, create_user):
    user_a = await create_user({"username": "gleb", "password": "gleb123"})
    user_b = await create_user({"username": "thomas", "password": "tom1234"})

    for title in ["first", "first and second", "third"]:
        response_user_a = await client.post(
            "/tasks",
            json={"title": title, "description": "description"},
            headers=user_a["headers"])
        assert response_user_a.status_code == 201

    response_user_b = await client.post(
        "/tasks",
        json={"title": "learn fastapi", "description": "description"},
        headers=user_b["headers"])
    assert response_user_b.status_code == 201

    request_user_a = await client.get("/tasks?search=first", headers=user_a["headers"])
    assert request_user_a.status_code == 200
    items_user_a = request_user_a.json()["items"]
    titles = [item["title"] for item in items_user_a]
    assert titles == ["first", "first and second"]
    assert all(item["user_id"] == user_a["user_data"]["id"] for item in items_user_a)
    assert request_user_a.json()["total"] == 2

@pytest.mark.asyncio
async def test_is_done_in_tasks_for_user(client, create_user):
    user_a = await create_user({"username": "gleb", "password": "gleb123"})
    user_b = await create_user({"username": "thomas", "password": "tom1234"})

    created_user_a_tasks = []
    for title in ["first", "first and second", "third"]:
        response_user_a = await client.post(
            "/tasks",
            json={"title": title, "description": "description"},
            headers=user_a["headers"])
        assert response_user_a.status_code == 201
        created_user_a_tasks.append(response_user_a.json())
    task_id_a = created_user_a_tasks[2]["id"]

    update_response_a = await client.patch(f"/tasks/{task_id_a}", json={"is_done": True}, headers=user_a["headers"])
    assert update_response_a.status_code == 200
    assert update_response_a.json()["is_done"] is True

    response_user_b = await client.post(
        "/tasks",
        json={"title": "learn fastapi", "description": "description"},
        headers=user_b["headers"])
    assert response_user_b.status_code == 201
    task_id_b = response_user_b.json()["id"]

    update_response_b = await client.patch(f"/tasks/{task_id_b}", json={"is_done": True}, headers=user_b["headers"])
    assert update_response_b.status_code == 200
    assert update_response_b.json()["is_done"] is True

    response_is_done_user_a = await client.get("/tasks?is_done=false", headers=user_a["headers"])
    assert response_is_done_user_a.status_code == 200
    items_user_a = response_is_done_user_a.json()["items"]
    assert all(item["is_done"] is False for item in items_user_a)
    assert all(item["user_id"] == user_a["user_data"]["id"] for item in items_user_a)
    assert response_is_done_user_a.json()["total"] == 2

@pytest.mark.asyncio
async def test_pagination_for_user_tasks(client, create_user):
    user_a = await create_user({"username": "gleb", "password": "gleb123"})
    created_user_a_tasks = []
    for title in ["first", "first and second", "third"]:
        response_user_a = await client.post(
            "/tasks",
            json={"title": title, "description": "description"},
            headers=user_a["headers"])
        assert response_user_a.status_code == 201
        created_user_a_tasks.append(response_user_a.json())

    user_b = await create_user({"username": "thomas", "password": "tom1234"})
    await client.post(
        "/tasks",
        json={"title": "other user's task", "description": "description"},
        headers=user_b["headers"],
    )

    response = await client.get("/tasks?limit=2&offset=1", headers=user_a["headers"])
    assert response.status_code == 200
    items = response.json()["items"]
    titles = [item["title"] for item in items]
    assert titles == ["first and second", "third"]
    assert [item["id"] for item in items] == [
        created_user_a_tasks[1]["id"],
        created_user_a_tasks[2]["id"],
    ]
    assert response.json()["limit"] == 2
    assert response.json()["offset"] == 1
    assert response.json()["total"] == 3

@pytest.mark.asyncio
async def test_sort_by_and_order_for_user_tasks(client, create_user):
    user_a = await create_user({"username": "gleb", "password": "gleb123"})
    created_user_a_tasks = []
    for title in ["take delivery", "buy a car", "learn fastapi"]:
        response_user_a = await client.post(
            "/tasks",
            json={"title": title, "description": "description"},
            headers=user_a["headers"])
        assert response_user_a.status_code == 201
        created_user_a_tasks.append(response_user_a.json())
    expected_tasks = sorted(created_user_a_tasks, key=lambda task: task["title"])
    user_b = await create_user({"username": "thomas", "password": "tom1234"})
    await client.post(
        "/tasks",
        json={"title": "other user's task", "description": "description"},
        headers=user_b["headers"],
    )

    response = await client.get("/tasks?sort_by=title&order=asc", headers=user_a["headers"])
    assert response.status_code == 200
    response_data = response.json()
    items = response_data["items"]
    assert [item["title"] for item in items] == [task["title"] for task in expected_tasks]
    assert [item["id"] for item in items] == [task["id"] for task in expected_tasks]
    assert all(item["user_id"] == user_a["user_data"]["id"] for item in items)
    assert response_data["total"] == 3


@pytest.mark.asyncio
async def test_get_tasks_filter_sort_with_pagination(client, create_user):
    user_a = await create_user({"username": "gleb", "password": "gleb123"})
    created_user_a_tasks = []
    for title in ["make a fastapi backend", "buy a car", "learn fastapi", "debug fastapi tests"]:
        response_user_a = await client.post(
            "/tasks",
            json={"title": title, "description": "description"},
            headers=user_a["headers"])
        assert response_user_a.status_code == 201
        created_user_a_tasks.append(response_user_a.json())
    done_task = next(task for task in created_user_a_tasks if task["title"] == "learn fastapi")

    update_response_a = await client.patch(f"/tasks/{done_task['id']}", json={"is_done": True}, headers=user_a["headers"])
    assert update_response_a.status_code == 200
    assert update_response_a.json()["is_done"] is True

    done_task["is_done"] = True
    tasks = sorted(created_user_a_tasks, key=lambda task: task["title"], reverse=True)
    expected_tasks = list(filter(lambda task: task["is_done"] is False and "fastapi" in task["title"], tasks))

    user_b = await create_user({"username": "thomas", "password": "tom1234"})
    await client.post(
        "/tasks",
        json={"title": "other user's fastapi task", "description": "description"},
        headers=user_b["headers"],
    )

    response = await client.get("/tasks?search=fastapi&is_done=false&sort_by=title&order=desc&limit=2&offset=0",
                                headers=user_a["headers"])

    assert response.status_code == 200
    response_data = response.json()
    items = response_data["items"]
    assert [item["title"] for item in items] == [task["title"] for task in expected_tasks]
    assert [item["id"] for item in items] == [task["id"] for task in expected_tasks]
    assert all(item["user_id"] == user_a["user_data"]["id"] for item in items)
    assert all(item["is_done"] is False for item in items)
    assert response_data["total"] == 2
    assert response_data["offset"] == 0
    assert response_data["limit"] == 2

