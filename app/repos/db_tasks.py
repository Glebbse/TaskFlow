# Repo layer for tasks

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task
from app.schemas.task import TaskCreate


async def get_next_task_position(session: AsyncSession, user_id: int) -> int:
    query_max = select(func.max(Task.position)).select_from(Task).where(Task.user_id == user_id)
    result = await session.execute(query_max)
    max_position = result.scalar_one_or_none()
    return 1 if max_position is None else max_position + 1

async def shift_task_position(session: AsyncSession, deleted_task: Task) -> None:
    query_shift_position = (
        update(Task)
        .where(Task.user_id == deleted_task.user_id)
        .where(Task.position > deleted_task.position)
        .values(position=Task.position - 1)
    )
    await session.execute(query_shift_position)

async def create_db_task(session: AsyncSession, user_id: int, payload: TaskCreate, position: int) -> Task:
    task = Task(title=payload.title, description=payload.description, user_id=user_id, position=position)
    session.add(task)
    return task

async def get_all_db_tasks(session: AsyncSession,
                           limit: int,
                           offset: int,
                           search: str | None,
                           is_done: bool | None,
                           sort_by: str = "position",
                           order: str = "asc") -> tuple[list[Task], int]:
    query = select(Task)
    count_query = select(func.count()).select_from(Task)
    if search is not None:
        query = query.where(Task.title.ilike(f"%{search}%"))
        count_query = count_query.where(Task.title.ilike(f"%{search}%"))

    allowed_fields = {
        "id": Task.id,
        "title": Task.title,
        "position": Task.position,
        "created_at": Task.created_at,
        "last_updated": Task.last_updated
    }

    if is_done is not None:
        query = query.where(Task.is_done == is_done)
        count_query = count_query.where(Task.is_done == is_done)
    sorting_cond = allowed_fields.get(sort_by, Task.id)

    if order == "asc":
        query = query.order_by(sorting_cond.asc())
    else:
        query = query.order_by(sorting_cond.desc())

    query = query.limit(limit).offset(offset)
    result = await session.execute(query)
    items = list(result.scalars())
    total_result = await session.execute(count_query)
    total = total_result.scalar_one()
    return items, total


async def get_db_tasks_by_user_id(session: AsyncSession,
                                  user_id: int,
                                  limit: int,
                                  offset: int,
                                  search: str | None,
                                  is_done: bool | None,
                                  sort_by: str = "position",
                                  order: str = "asc") -> tuple[list[Task], int]:
    query = select(Task).where(Task.user_id == user_id)
    count_query = select(func.count()).select_from(Task).where(Task.user_id == user_id)
    if search is not None:
        query = query.where(Task.title.ilike(f"%{search}%"))
        count_query = count_query.where(Task.title.ilike(f"%{search}%"))

    if is_done is not None:
        query = query.where(Task.is_done == is_done)
        count_query = count_query.where(Task.is_done == is_done)

    allowed_fields = {
        "id": Task.id,
        "title": Task.title,
        "position": Task.position,
        "created_at": Task.created_at,
        "last_updated": Task.last_updated
    }
    sorting_cond = allowed_fields.get(sort_by, Task.id)
    if order == "asc":
        query = query.order_by(sorting_cond.asc())
    else:
        query = query.order_by(sorting_cond.desc())
    query = query.limit(limit).offset(offset)
    result = await session.execute(query)
    items = list(result.scalars())
    total_result = await session.execute(count_query)
    total = total_result.scalar_one()
    return items, total

async def get_db_task(session: AsyncSession, task_id: int) -> Task | None:
    result = await session.execute(select(Task).where(Task.id == task_id))
    return result.scalar_one_or_none()

async def delete_db_task(session: AsyncSession, task: Task):
    await session.delete(task)
    return {"deleted": task}

async def update_db_task(session: AsyncSession, task: Task, updated_data: dict) -> Task:
    allowed_fields = {"title", "description", "is_done"}
    for field, value in updated_data.items():
        if field in allowed_fields:
            setattr(task, field, value)
    return task
