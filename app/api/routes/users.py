# Routes for users' requests

from fastapi import Depends, APIRouter, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Literal

from app.api.deps import get_session, get_current_user, get_current_admin
from app.models.user import User
from app.schemas.user import UserRead, UserListResponse, UserDeleted
from app.services import user_service


router = APIRouter(prefix="/users", tags=["users"])

@router.get("/me", response_model=UserRead)
async def get_my_info_handler(current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    return current_user

@router.get("", response_model=UserListResponse)
async def get_all_users_handler(limit: int = Query(default=10, ge=1, le=100),
                                offset: int = Query(default=0, ge=0),
                                search: str | None = Query(default=None),
                                sort_by: Literal["id", "username"] = Query(default="id"),
                                order: Literal["asc", "desc"] = Query(default="asc"),
                                current_user: User = Depends(get_current_admin),
                                session: AsyncSession = Depends(get_session)):
    return await user_service.get_all_users_service(session, limit, offset, search, sort_by, order)

@router.get("/{user_id}", response_model=UserRead)
async def get_user_by_id_handler(user_id: int, current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    if current_user.id == user_id or current_user.role == "admin":
        return await user_service.get_user_by_id_service(session, user_id)

    raise HTTPException(status_code=403, detail= "Forbidden")

@router.delete("/{user_id}", response_model=UserDeleted)
async def delete_user_handler(user_id: int, current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    if current_user.id == user_id or current_user.role == "admin":
        return await user_service.delete_user_service(session, user_id)

    raise HTTPException(status_code=403, detail="Forbidden")
