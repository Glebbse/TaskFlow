# Routes for tasks' requests

from fastapi import Depends, APIRouter, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, get_current_user
from app.models.user import User
from app.schemas.task import TaskRead, TaskCreate, DeletedResponse, TaskUpdate, TaskListResponse
from app.services import task_service
from app.services.task_service import TaskNotFoundError, TaskForbiddenError

router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.post("", status_code=201, response_model=TaskRead)
async def create_task_handler(payload: TaskCreate, current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    return await task_service.create_task_for_user_service(session, current_user.id, payload)

@router.get("/{task_id}", response_model=TaskRead)
async def get_task_handler(task_id: int, current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    try:
        return await task_service.get_task_service(session, task_id, current_user.id)
    except TaskForbiddenError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except TaskNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("", response_model=TaskListResponse)
async def get_list_of_tasks_handler(limit: int = Query(default=10, ge=1, le=100),
                                    offset: int = Query(default=0, ge=0),
                                    search: str | None = Query(default=None, min_length=1, max_length=255),
                                    is_done: bool | None = Query(default=None),
                                    current_user: User = Depends(get_current_user),
                                    session: AsyncSession = Depends(get_session)):
    return await task_service.get_tasks_by_user_service(session, current_user.id, limit, offset, search, is_done)

@router.delete("/{task_id}", response_model=DeletedResponse)
async def delete_task_handler(task_id:int, current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    try:
        return await task_service.delete_task_service(session, task_id, current_user.id)
    except TaskForbiddenError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except TaskNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.patch("/{task_id}", response_model=TaskRead)
async def update_task_handler(task_id: int, payload: TaskUpdate, current_user: User = Depends(get_current_user),  session: AsyncSession = Depends(get_session)):
    try:
        return await task_service.update_task_service(session, task_id, current_user.id, payload)
    except TaskForbiddenError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except TaskNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
