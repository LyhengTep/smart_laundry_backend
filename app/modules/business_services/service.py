from sqlmodel.ext.asyncio.session import AsyncSession

from app.modules.business_services.model import BusinessService
from app.modules.business_services.schema import BusinessServiceRead, BusinessServiceWrite
from app.modules.business_services import repository as repo


async def list_business_services(session: AsyncSession) -> list[BusinessServiceRead]:
    return await repo.list_all(session)


async def create_business_service(session: AsyncSession, data: BusinessServiceWrite) -> BusinessServiceRead:
    service = BusinessService(
        business_id=data.business_id,
        service_id=data.service_id,
        base_price=data.base_price,
        pricing_type=data.pricing_type,
    )
    return await repo.save(service, session)


async def create_business_service_bulk(
    session: AsyncSession, data: list[BusinessServiceWrite]
) -> list[BusinessServiceRead]:
    services = [
        BusinessService(
            business_id=item.business_id,
            service_id=item.service_id,
            base_price=item.base_price,
            pricing_type=item.pricing_type,
        )
        for item in data
    ]
    await repo.save_all(services, session)
    return await repo.list_by_business(services[0].business_id, session)
