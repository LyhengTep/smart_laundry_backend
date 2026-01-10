
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.engine import URL
from sqlmodel.ext.asyncio.session import AsyncSession

url = URL.create(
    drivername="postgresql+asyncpg",
    username="smart_laundry",
    password="p_JI7F7!|3x>",
    host="localhost",
    port=5432,
    database="smart_laundry",
)


engine = create_async_engine(url, echo=True)

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session
