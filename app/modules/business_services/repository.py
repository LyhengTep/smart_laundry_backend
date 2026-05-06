from uuid import UUID

from sqlalchemy.orm import selectinload
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.modules.business_services.model import BusinessService


def _with_relations():
    return [selectinload(BusinessService.business), selectinload(BusinessService.laundry_service)]


async def get_by_id(service_id: UUID, session: AsyncSession) -> BusinessService | None:
    result = await session.exec(
        select(BusinessService).where(BusinessService.id == service_id).options(*_with_relations())
    )
    return result.first()


async def list_by_business(business_id: UUID, session: AsyncSession) -> list[BusinessService]:
    result = await session.exec(
        select(BusinessService)
        .where(BusinessService.business_id == business_id)
        .options(selectinload(BusinessService.laundry_service))
    )
    return list(result.all())


async def list_all(session: AsyncSession) -> list[BusinessService]:
    result = await session.exec(
        select(BusinessService).options(*_with_relations())
    )
    return list(result.all())


async def save(service: BusinessService, session: AsyncSession) -> BusinessService:
    session.add(service)
    await session.commit()
    await session.refresh(service)
    return service


async def save_all(services: list[BusinessService], session: AsyncSession) -> list[BusinessService]:
    session.add_all(services)
    await session.commit()
    return services


async def delete(service: BusinessService, session: AsyncSession) -> None:
    await session.delete(service)
    await session.commit()
