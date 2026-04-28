import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.api.deps import get_session
from app.core.base import Base
from app.main import app
from app.models.user import User

TEST_DB_URL = "sqlite+aiosqlite:///./test.db"

test_engine = create_async_engine(TEST_DB_URL, echo=False)
TestSessionLocal = async_sessionmaker(bind=test_engine, expire_on_commit=False)

async def override_get_session() -> AsyncSession:
    async with TestSessionLocal() as session:
        yield session

@pytest_asyncio.fixture(scope="function", autouse=True)
async def prepare_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture(scope="function")
async def client():
    app.dependency_overrides[get_session] = override_get_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()

@pytest_asyncio.fixture
async def create_user(client):
    async def _create_user(payload: dict):
        register_response = await client.post("/auth/register", json=payload)
        assert register_response.status_code == 200
        user_data = register_response.json()

        login_response = await client.post("/auth/login", json=payload)
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        headers = {"Authorization": f"Bearer {token}"}

        return {
            "payload": payload,
            "user_data": user_data,
            "token": token,
            "headers": headers
        }
    return _create_user

@pytest_asyncio.fixture
async def make_user_admin():
    async def _make_user_admin(user_id: int):
        async with TestSessionLocal() as session:
            user = await session.get(User, user_id)
            if user is None:
                raise ValueError(f"User with user_id {user_id} not found")
            user.role = "admin"
            await session.commit()
            await session.refresh(user)

            return user

    return _make_user_admin

