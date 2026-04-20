import asyncio
from sqlalchemy import text
from fastapi import FastAPI

from app.core.db import engine
from app.api.routes.tasks import router as tasks_router
from app.api.routes.users import router as users_router
from app.api.routes.auth import router as auth_router

app = FastAPI(title="TaskFlow")

app.include_router(tasks_router)
app.include_router(users_router)
app.include_router(auth_router)

async def test_db():
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT 1;"))
        print("DB result: ", result.scalar())

if __name__ == "__main__":
    asyncio.run(test_db())
