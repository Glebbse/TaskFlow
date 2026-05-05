# DB model (SQLAlchemy)
from typing import TYPE_CHECKING

from sqlalchemy import Index, String, Boolean, DateTime, func, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime


from app.core.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        UniqueConstraint("user_id", "position", name="uq_tasks_user_position"),
        Index("ix_tasks_user_done_position", "user_id", "is_done", "position"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    position: Mapped[int] = mapped_column(nullable=False)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(nullable=True)
    is_done: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now())
    last_updated: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=True)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user: Mapped["User"] = relationship(back_populates="tasks")
