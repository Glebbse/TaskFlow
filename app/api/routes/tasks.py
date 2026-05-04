# Routes for tasks' requests

from typing import Literal

from fastapi import Depends, APIRouter, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, get_current_user
from app.models.user import User
from app.schemas.task import TaskRead, TaskCreate, DeletedResponse, TaskUpdate, TaskListResponse
from app.services import task_service

router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.post("", status_code=201, response_model=TaskRead)
async def create_task_handler(payload: TaskCreate, current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    return await task_service.create_task_for_user_service(session, current_user.id, payload)

@router.get("/{task_id}", response_model=TaskRead)
async def get_task_handler(task_id: int, current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    return await task_service.get_task_service(session, task_id, current_user.id)

@router.get("", response_model=TaskListResponse)
async def get_list_of_tasks_handler(limit: int = Query(default=10, ge=1, le=100),
                                    offset: int = Query(default=0, ge=0),
                                    search: str | None = Query(default=None, min_length=1, max_length=255),
                                    is_done: bool | None = Query(default=None),
                                    sort_by: Literal["id", "title", "position", "created_at", "last_updated"] = Query(default="position"),
                                    order: Literal["asc", "desc"] = Query(default="asc"),
                                    current_user: User = Depends(get_current_user),
                                    session: AsyncSession = Depends(get_session)):
    return await task_service.get_tasks_by_user_service(session, current_user.id, limit, offset, search, is_done, sort_by, order)

@router.delete("/{task_id}", response_model=DeletedResponse)
async def delete_task_handler(task_id:int, current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    return await task_service.delete_task_service(session, task_id, current_user.id)

@router.patch("/{task_id}", response_model=TaskRead)
async def update_task_handler(task_id: int, payload: TaskUpdate, current_user: User = Depends(get_current_user),  session: AsyncSession = Depends(get_session)):
    return await task_service.update_task_service(session, task_id, current_user.id, payload)
