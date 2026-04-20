# Pydantic models for API

from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict, field_serializer


class TaskCreate(BaseModel):
    """What client is allowed to send"""
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None


class TaskRead(BaseModel):
    """API response of task info"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    is_done: bool
    created_at: datetime
    last_updated: datetime | None
    user_id: int


class DeletedResponse(BaseModel):
    deleted: TaskRead


class TaskUpdate(BaseModel):
    """What client is allowed to send for updating task"""
    model_config = ConfigDict(from_attributes=True)

    title: str | None = None
    description: str | None = None
    is_done: bool | None = None


class TaskListResponse(BaseModel):
    """API response with list of tasks and pagination"""
    items: list[TaskRead]
    total: int
    limit: int
    offset: int
