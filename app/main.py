import asyncio
from sqlalchemy import text
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.core.db import engine
from app.api.routes.tasks import router as tasks_router
from app.api.routes.users import router as users_router
from app.api.routes.auth import router as auth_router
from app.core.exceptions import register_exception_handlers

app = FastAPI(title="TaskFlow")

register_exception_handlers(app)
app.include_router(tasks_router)
app.include_router(users_router)
app.include_router(auth_router)
app.mount("/ui", StaticFiles(directory="frontend", html=True), name="ui")

async def test_db():
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT 1;"))
        print("DB result: ", result.scalar())

if __name__ == "__main__":
    asyncio.run(test_db())
