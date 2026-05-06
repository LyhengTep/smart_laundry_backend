from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.modules.laundry_services.model import LaundryService


async def get_by_id(service_id: int, session: AsyncSession) -> LaundryService | None:
    return await session.get(LaundryService, service_id)


async def list_all(session: AsyncSession) -> list[LaundryService]:
    result = await session.exec(select(LaundryService))
    return list(result.all())


async def save(service: LaundryService, session: AsyncSession) -> LaundryService:
    session.add(service)
    await session.commit()
    await session.refresh(service)
    return service


async def delete(service: LaundryService, session: AsyncSession) -> None:
    await session.delete(service)
    await session.commit()
