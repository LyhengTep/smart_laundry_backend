
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession
import os

load_dotenv()

_engine = None
_session_factory = None


def _get_engine():
    global _engine
    if _engine is None:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise RuntimeError("DATABASE_URL environment variable is not set")
        _engine = create_async_engine(database_url, echo=False)
    return _engine


class _EngineProxy:
    """Forwards attribute access to the lazily-created engine instance."""
    def __getattr__(self, name):
        return getattr(_get_engine(), name)


engine = _EngineProxy()


def _get_session_factory():
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            _get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with _get_session_factory()() as session:
        yield session


@asynccontextmanager
async def get_session_context() -> AsyncGenerator[AsyncSession, None]:
    async with _get_session_factory()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise