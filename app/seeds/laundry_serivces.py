
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.modules.laundry_services.model import LaundryService, ServiceEnum


async def seed_laundry_service(session: AsyncSession) -> int:
    existing = (await session.execute(select(LaundryService).limit(1))).first()
    if existing:
        return 0

    created = 0
    now = datetime.now(timezone.utc)


    washing = LaundryService(name=ServiceEnum.WASH, code="WASH001", description="Washing service", price=5.0, created_at=now, updated_at=now)
    drying = LaundryService(name=ServiceEnum.DRY_CLEAN, code="DRY001", description="Drying service", price=3.0, created_at=now, updated_at=now)
    ironing = LaundryService(name=ServiceEnum.IRON, code="IRON001", description="Ironing service", price=4.0, created_at=now, updated_at=now)

    session.add(washing)
    session.add(drying)   
    session.add(ironing)

    await session.commit()
    return 3