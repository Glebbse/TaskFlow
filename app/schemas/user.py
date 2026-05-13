# Pydantic models for API

from pydantic import Field, ConfigDict, BaseModel, EmailStr


class UserCreate(BaseModel):
    """Creating user"""
    username: str = Field(min_length=1, max_length=100)


class UserRead(BaseModel):
    """API response of user info"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    email: str | None
    role: str


class UserListResponse(BaseModel):
    """API response with list of users and pagination"""
    items: list[UserRead]
    total: int
    limit: int
    offset: int


class UserRegister(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    email: EmailStr | None = None
    password: str = Field(min_length=6, max_length=72)


class UserLogin(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=6, max_length=72)


class UserDeleted(BaseModel):
    deleted: UserRead


class PasswordUpdate(BaseModel):
    current_password: str = Field(min_length=6, max_length=72)
    new_password: str = Field(min_length=6, max_length=72)


class MessageResponse(BaseModel):
    detail: str
