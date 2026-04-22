# Routes for users' requests

from fastapi import Depends, APIRouter, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Literal

from app.api.deps import get_session, get_current_user
from app.models.user import User
from app.schemas.task import TaskRead, TaskCreate, TaskListResponse
from app.schemas.user import UserRead, UserCreate, UserListResponse
from app.services import user_service, task_service
from app.services.task_service import create_task_for_user_service
from app.services.user_service import UsernameAlreadyExistError, UserNotFoundError


router = APIRouter(prefix="/users", tags=["users"])

@router.post("/{user_id}/tasks", response_model=TaskRead)
async def create_task_for_user_handler(user_id: int, payload: TaskCreate, session: AsyncSession = Depends(get_session)):
    try:
        return await create_task_for_user_service(session, user_id, payload)
    except UserNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

# @router.post("", status_code=201, response_model=UserRead)
# async def create_user_handler(payload: UserCreate, session: AsyncSession = Depends(get_session)):
#     try:
#         return await user_service.create_user_service(session, payload)
#     except UsernameAlreadyExistError as e:
#         raise HTTPException(status_code=409, detail=str(e))

@router.get("/{user_id}/tasks", response_model=TaskListResponse)
async def get_user_tasks_handler(user_id: int,
                                 limit: int = Query(default=10, ge=1, le=100),
                                 offset: int = Query(default=0, ge=0),
                                 search: str | None = Query(default=None, min_length=1, max_length=255),
                                 is_done: bool | None = Query(default=None),
                                 sort_by: Literal["id", "title", "created_at", "last_updated"] = Query(default="id"),
                                 order: Literal["asc", "desc"] = Query(default="desc"),
                                 session: AsyncSession = Depends(get_session)):
    try:
        return await task_service.get_tasks_by_user_service(session, user_id, limit, offset, search, is_done, sort_by, order)
    except UserNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("", response_model=UserListResponse)
async def get_all_users_handler(limit: int = Query(default=10, ge=1, le=100),
                                offset: int = Query(default=0, ge=0),
                                search: str | None = Query(default=None),
                                sort_by: Literal["id", "username"] = Query(default="id"),
                                order: Literal["asc", "desc"] = Query(default="asc"),
                                session: AsyncSession = Depends(get_session)):
    return await user_service.get_all_users_service(session, limit, offset, search, sort_by, order)

@router.get("/{user_id}", response_model=UserRead)
async def get_user_by_id_handler(user_id: int, current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    try:
        return await user_service.get_user_by_id_service(session, user_id)
    except UserNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

