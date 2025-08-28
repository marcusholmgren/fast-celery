from typing import Any, AsyncGenerator, Coroutine

from alchemical.aio import Alchemical
from sqlalchemy.ext.asyncio import AsyncSession



db = Alchemical("sqlite+aiosqlite:///little-fast-celery.db")


async def get_db_session() ->  AsyncGenerator[AsyncSession | Any, Any]:
    async with db.Session() as session:
        yield session


async def create_db_and_tables():
    await db.create_all()
