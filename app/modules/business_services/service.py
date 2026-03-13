





from unittest import result

from sqlalchemy.orm import selectinload
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from app.modules.business_services.model import BusinessService
from app.modules.business_services.schema import BusinessServiceRead, BusinessServiceWrite




async def list_business_services(session: AsyncSession) -> list[BusinessServiceRead]:
    result = await session.exec(select(BusinessService).options(selectinload(BusinessService.business), selectinload(BusinessService.laundry_service)))
    return result.all()



async def create_business_service(session: AsyncSession, data: BusinessServiceWrite) -> BusinessServiceRead:

    business_service = BusinessService(
        business_id=data.business_id,
        service_id=data.service_id,
        base_price=data.base_price
    )
    session.add(business_service)
    await session.commit()
    await session.refresh(business_service)
    return business_service





async def create_business_service_bulk(session: AsyncSession, data: list[BusinessServiceWrite]) -> list[BusinessServiceRead]:

    business_services = []
    for item in data:
        business_service = BusinessService(
            business_id=item.business_id,
            service_id=item.service_id,
            base_price=item.base_price,
            pricing_type=item.pricing_type
        )
        business_services.append(business_service)
    session.add_all(business_services)
    await session.commit()

    print("Created business services:", business_services)
    statements=select(BusinessService).where(BusinessService.business_id==business_services[0].business_id).options(selectinload(BusinessService.laundry_service))

    result= await session.exec(statements)

    services = result.all()
    print("Created business services:", services)
    return services