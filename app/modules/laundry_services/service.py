from __future__ import annotations

from sqlmodel.ext.asyncio.session import AsyncSession

from app.modules.laundry_services.model import LaundryService
from app.modules.laundry_services.schema import LaundryServiceRead, LaundryServiceWrite
from app.modules.laundry_services import repository as repo


async def list_laundry_services(session: AsyncSession) -> list[LaundryServiceRead]:
    return await repo.list_all(session)


async def create_laundry_service(data: LaundryServiceWrite, session: AsyncSession) -> LaundryServiceRead:
    service = LaundryService(name=data.name, code=data.code, description=data.description)
    return await repo.save(service, session)
