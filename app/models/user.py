from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

# from app.models.task import Task
from app.core.base import Base


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="user", server_default="user")

    tasks: Mapped[list["Task"]] = relationship(back_populates="user")
