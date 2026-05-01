"""
Integration test fixtures.

Each test gets:
  - A fresh in-memory SQLite database (create_all → test → drop_all)
  - An httpx AsyncClient pointed at a test FastAPI app (same routers, no lifespan side-effects)
  - get_session dependency overridden with the test session
  - send_sqs_message and send_firebase_message patched to no-ops
"""
from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

import app.db.base  # noqa: F401 — registers all SQLModel table metadata


# ---------------------------------------------------------------------------
# Test database — one in-memory SQLite DB per test function (StaticPool keeps
# all connections pointing at the same in-memory file within a test).
# ---------------------------------------------------------------------------

def _make_engine():
    return create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


# ---------------------------------------------------------------------------
# Minimal lifespan — no Firebase, no SQS consumers.
# Tables are managed by the db_session fixture below.
# ---------------------------------------------------------------------------

@asynccontextmanager
async def _test_lifespan(app: FastAPI):
    yield


def _make_test_app() -> FastAPI:
    from app.api.v1.router import api_router
    application = FastAPI(lifespan=_test_lifespan)
    application.include_router(api_router, prefix="/api/v1")
    return application


# ---------------------------------------------------------------------------
# anyio backend (used by @pytest.mark.anyio)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


# ---------------------------------------------------------------------------
# DB session — fresh schema per test
# ---------------------------------------------------------------------------

@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = _make_engine()
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
    await engine.dispose()


# ---------------------------------------------------------------------------
# HTTP client — overrides get_session + patches external calls
# ---------------------------------------------------------------------------

@pytest.fixture
async def client(db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch) -> AsyncGenerator[AsyncClient, None]:
    import app.lib.aws as aws_module
    import app.core.firebase as firebase_module

    monkeypatch.setattr(aws_module, "send_sqs_message", lambda *a, **kw: {"MessageId": "test"})
    monkeypatch.setattr(firebase_module, "send_firebase_message", lambda *a, **kw: None)

    from app.db.engine import get_session

    async def _override_session():
        yield db_session

    test_app = _make_test_app()
    test_app.dependency_overrides[get_session] = _override_session

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as http:
        yield http


# ---------------------------------------------------------------------------
# Helpers used by multiple test modules
# ---------------------------------------------------------------------------

async def make_user(
    session: AsyncSession,
    *,
    role: str = "CUSTOMER",
    status: str = "ACTIVE",
) -> tuple:
    """Insert a user into the DB and return (user, bearer_token)."""
    from app.lib.datetime import utc_now
    from app.lib.security import create_access_token, hash_password
    from app.modules.users.models import RoleName, User, UserStatus

    uid = uuid4()
    user = User(
        id=uid,
        full_name="Test User",
        user_name=f"user_{uid.hex[:8]}",
        email=f"{uid.hex[:8]}@test.com",
        phone=None,
        msg_token=None,
        password_hash=hash_password("secret123"),
        role=RoleName(role),
        status=UserStatus(status),
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    token = create_access_token(str(user.id))
    return user, token


async def make_business(session: AsyncSession, owner_id) -> object:
    """Insert a LaundryBusiness owned by owner_id."""
    from datetime import time

    from app.lib.datetime import utc_now
    from app.modules.businesses.models import LaundryBusiness, ShopStatus

    business = LaundryBusiness(
        id=uuid4(),
        owner_id=owner_id,
        name="Test Laundry",
        address="123 Test St",
        phone="0001112222",
        latitude=11.5,
        longitude=104.9,
        profile_image_url=None,
        cover_image_url=None,
        business_license_number="LIC-TEST",
        rating_avg=0.0,
        open_time=time(8, 0),
        close_time=time(20, 0),
        status=ShopStatus.OPEN,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    session.add(business)
    await session.commit()
    await session.refresh(business)
    return business


async def make_laundry_service(session: AsyncSession) -> object:
    """Insert a LaundryService (WASH)."""
    from app.lib.datetime import utc_now
    from app.modules.laundry_services.model import LaundryService, ServiceEnum

    svc = LaundryService(
        name=ServiceEnum.WASH,
        code="WASH",
        description="Standard wash service",
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    session.add(svc)
    await session.commit()
    await session.refresh(svc)
    return svc


async def make_business_service(session: AsyncSession, business_id, laundry_service_id: int) -> object:
    """Insert a BusinessService linking a business to a laundry service."""
    from app.lib.datetime import utc_now
    from app.modules.business_services.model import BusinessService, PriceType

    bs = BusinessService(
        id=uuid4(),
        business_id=business_id,
        service_id=laundry_service_id,
        base_price=5.0,
        is_active=True,
        pricing_type=PriceType.PER_WEIGHT,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    session.add(bs)
    await session.commit()
    await session.refresh(bs)
    return bs
