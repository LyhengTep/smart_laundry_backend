from __future__ import annotations
from uuid import UUID
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from app.exceptions.http import create_404
from app.modules.businesses.models import LaundryBusiness

from app.modules.laundry_services.model import LaundryService
from app.modules.laundry_services.schema import LaundryServiceRead, LaundryServiceWrite
from app.shared.passwords import hash_password



async def list_laundry_services(session: AsyncSession) -> list[LaundryServiceRead]:
    result = await session.exec(select(LaundryService))
    return result.all()


async def create_laundry_service(data:LaundryServiceWrite ,session: AsyncSession) -> LaundryServiceRead:
    laundry_service = LaundryService(name=data.name, code=data.code, description=data.description)
    session.add(laundry_service)
    await session.commit()
    await session.refresh(laundry_service)
    return laundry_service