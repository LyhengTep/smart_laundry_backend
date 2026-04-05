
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.engine import URL
from sqlmodel.ext.asyncio.session import AsyncSession
import os
load_dotenv()
url = URL.create(
    drivername="postgresql+asyncpg",
    username="smart_laundry",
    password="p_JI7F7!|3x>",
    host="localhost",
    port=5432,
    database="smart_laundry",
)

print("Database URL:",os.getenv("DATABASE_URL"))  # Debug print to check the URL being used
engine = create_async_engine(os.getenv("DATABASE_URL"), echo=False)

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session


@asynccontextmanager
async def get_session_context() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise