# Service layer for tasks

from sqlalchemy.ext.asyncio import  AsyncSession

from app.models.task import Task
from app.schemas.task import TaskCreate, TaskUpdate
from app.repos import db_tasks
from app.services.user_service import get_user_by_id_service


class TaskNotFoundError(Exception):
    pass

class TaskForbiddenError(Exception):
    pass

async def create_task_for_user_service(session: AsyncSession, user_id: int, payload: TaskCreate) -> Task:
    await get_user_by_id_service(session, user_id)
    task = await db_tasks.create_db_task(session, user_id, payload)
    await session.commit()
    await session.refresh(task)
    return task

async def get_tasks_by_user_service(session: AsyncSession,
                                    user_id: int,
                                    limit: int,
                                    offset: int,
                                    search: str | None,
                                    is_done: bool | None,
                                    sort_by: str = "id",
                                    order: str = "desc") -> dict:
    await get_user_by_id_service(session, user_id)
    items, total = await db_tasks.get_db_tasks_by_user_id(session, user_id, limit, offset, search, is_done, sort_by, order)
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset
    }

async def delete_task_service(session: AsyncSession, task_id: int, current_user_id: int) -> dict:
    task = await get_task_service(session, task_id, current_user_id)
    deleted_task =  await db_tasks.delete_db_task(session, task)
    await session.commit()
    return deleted_task

async def get_task_service(session: AsyncSession, task_id: int, current_user_id: int) -> Task:
    task = await db_tasks.get_db_task(session, task_id)
    if task is None:
        raise TaskNotFoundError(f"Task with id {task_id} not found")
    if task.user_id != current_user_id:
        raise TaskForbiddenError("Forbidden")
    return task

async def update_task_service(session: AsyncSession, task_id: int, current_user_id: int,  payload: TaskUpdate) -> Task:
    updated_data = payload.model_dump(exclude_unset=True)
    task = await get_task_service(session, task_id, current_user_id)
    updated_task = await db_tasks.update_db_task(session, task, updated_data)
    await session.commit()
    await session.refresh(updated_task)
    return updated_task
