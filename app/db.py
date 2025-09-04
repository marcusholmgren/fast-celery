"""
This module contains the database setup and session management for the booking service.
"""
from typing import Any, AsyncGenerator

from alchemical.aio import Alchemical
from sqlalchemy.ext.asyncio import AsyncSession


db = Alchemical("sqlite+aiosqlite:///little-fast-celery.db")


async def get_db_session() -> AsyncGenerator[AsyncSession | Any, Any]:
    """
    Dependency that provides a database session.
    """
    async with db.Session() as session:
        yield session


async def create_db_and_tables():
    """
    Creates the database and tables.
    """
    await db.create_all()
