# Routes for tasks' requests

from fastapi import Depends, APIRouter, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.schemas.task import TaskRead, TaskCreate, DeletedResponse, TaskUpdate
from app.services import task_service
from app.services.task_service import TaskNotFoundError

router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.post("", status_code=201, response_model=TaskRead)
async def create_task_handler(payload: TaskCreate, session: AsyncSession = Depends(get_session)):
    return await task_service.create_task_for_user_service(session, payload)

@router.get("/{task_id}", response_model=TaskRead)
async def get_task_handler(task_id: int, session: AsyncSession = Depends(get_session)):
    try:
        return await task_service.get_task_service(session, task_id)
    except TaskNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.delete("", response_model=DeletedResponse)
async def delete_task_handler(task_id:int, session: AsyncSession = Depends(get_session)):
    try:
        return await task_service.delete_task_service(session, task_id)
    except TaskNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.patch("/{task_id}", response_model=TaskRead)
async def update_task_handler(task_id: int, payload: TaskUpdate, session: AsyncSession = Depends(get_session)):
    try:
        return await task_service.update_task_service(session, task_id, payload)
    except TaskNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
