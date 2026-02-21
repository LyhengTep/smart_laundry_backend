
import logging
from uuid import UUID
from sqlalchemy import func
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import selectinload
from app.api.reponse_model import Page
from app.exceptions.http import create_404
from app.exceptions.user import UserNotFoundError
from app.modules.drivers.models import Driver
from app.modules.drivers.schema import DriverRead, DriverWrite
from app.modules.users.models import User, UserStatus

async def list_drivers(session: AsyncSession, page: int, size: int,status: UserStatus) -> Page[DriverRead]:

    offset= (page-1)*size

    print(f"offset value {page} {size} {offset}")

    statement= select(Driver).join(User).offset(offset).limit(size).options(selectinload(Driver.user))

    count_statement= select(func.count(Driver.id)).join(User)
    if status: 
        statement= statement.where(User.status==status)
        count_statement= count_statement.where(User.status==status)
    total_result = await session.exec(count_statement)
    total = total_result.one()
    print(f"total result count {status}")

 
    result = await session.exec(statement)
    drivers= result.all()
    logging.info("======= Query driver result ======= %s",len(drivers))
    return Page[DriverRead](items=drivers,total=total,page=page,size=size,pages=(total+size-1)//size)

async def list_one_driver(session: AsyncSession, driver_id: str) -> DriverRead:
    result = await session.exec(select(Driver).where(Driver.id == driver_id).options(selectinload(Driver.user)))
    driver = result.one_or_none()
    if not driver:
        raise create_404("Driver not found")
    return driver


async def approve_driver(session: AsyncSession, driver_id: str) -> DriverRead:
    result = await session.exec(select(Driver).where(Driver.id == driver_id).options(selectinload(Driver.user)))
    driver = result.one_or_none()

    print(f"approve driver {driver_id} result {driver}")
    if not driver:
        raise create_404("Driver not found")
    driver.user.status = UserStatus.ACTIVE
    await session.commit()
    await session.refresh(driver)
    return driver


async def reject_driver(session: AsyncSession, driver_id: str) -> DriverRead:
    result = await session.exec(select(Driver).where(Driver.id == driver_id).options(selectinload(Driver.user)))
    driver = result.one_or_none()
    if not driver:
        raise create_404("Driver not found")
    driver.user.status = UserStatus.REJECTED
    await session.commit()
    await session.refresh(driver)
    return driver


async def suspend_driver(session: AsyncSession, driver_id: str) -> DriverRead:
    result = await session.exec(select(Driver).where(Driver.id == driver_id).options(selectinload(Driver.user)))
    driver = result.one_or_none()
    if not driver:
        raise create_404("Driver not found")
    driver.user.status = UserStatus.SUSPENDED
    await session.commit()
    await session.refresh(driver)
    return driver


async def edit_driver(session: AsyncSession, driver_id: UUID, data: DriverWrite) -> DriverRead:
    result = await session.exec(select(Driver).where(Driver.id == driver_id).options(selectinload(Driver.user)))
    driver = result.one_or_none()
    if not driver:
        raise create_404("Driver not found")
    for key, value in data.model_dump(exclude_unset=True,exclude={"user"}).items():
        setattr(driver, key, value)


    for key, value in data.user.model_dump(exclude_unset=True).items():
        setattr(driver.user, key, value)
    


    print(f"edit driver {driver_id} with data {data} result {driver}")
    await session.commit()
    await session.refresh(driver)
    return driver