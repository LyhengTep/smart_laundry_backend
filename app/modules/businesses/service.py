
from datetime import datetime
import logging
from math import log
from uuid import UUID
import uuid
from sentry_sdk import session
from sentry_sdk.utils import now
from sqlalchemy import func,and_, or_
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import selectinload
from app.api.reponse_model import Page
from app.exceptions import user
from app.exceptions.http import create_401, create_404
from app.modules.business_services.model import BusinessService
from app.modules.businesses.models import LaundryBusiness, ShopStatus
from app.modules.businesses.schema import BusinessRead, BusinessUpdate, BusinessWrite, SingleBusinessRead

from app.modules.users.models import User, UserStatus

async def list_businesses(session: AsyncSession, page: int, size: int,status: UserStatus,is_open:bool=None, q:str=None) -> Page[BusinessRead]:

    offset= (page-1)*size

    print(f"offset value {page} {size} {offset}")

    statement= select(LaundryBusiness).join(User).offset(offset).limit(size).where(LaundryBusiness.status!=ShopStatus.DEACTIVATED).options(selectinload(LaundryBusiness.owner))
    
    count_statement= select(func.count(LaundryBusiness.id)).join(User)
    if status: 
        statement= statement.where(User.status==status)
        count_statement= count_statement.where(User.status==status)

    if is_open:
        statuses = [ShopStatus.APPROVED,ShopStatus.OPEN]
        now = datetime.now().time()
        statement= statement.where(and_(
            LaundryBusiness.open_time<=LaundryBusiness.close_time,
            LaundryBusiness.open_time <= now,
            LaundryBusiness.close_time >= now
        ),LaundryBusiness.status.in_(statuses))

    if q: 
        statement =statement.where(LaundryBusiness.name.ilike(f"%{q}%"))
    total_result = await session.exec(count_statement)
    total = total_result.one()
    print(f"total result count {status}")

 
    result = await session.exec(statement)
    businesses= result.all()
    logging.info("======= Query businesses result ======= %s",len(businesses))
    return Page[BusinessRead](items=businesses,total=total,page=page,size=size,pages=(total+size-1)//size)


async def list_one_business(id: UUID, session: AsyncSession) -> SingleBusinessRead:
    statement= select(LaundryBusiness).where(LaundryBusiness.id==id).options(selectinload(LaundryBusiness.services).selectinload(BusinessService.laundry_service))
    result = await session.exec(statement)
    business= result.first()

    print(f"Business found: {business.services}")
    if not business:
        raise create_404("Business not found")
    return business



async def edit_business(id: UUID, data: BusinessUpdate, current_user: uuid.UUID, session: AsyncSession) -> SingleBusinessRead:
    business_result = await session.exec(select(LaundryBusiness).where(LaundryBusiness.id == id))
    business = business_result.first()
    print(f"calling edit business service {business}")
    if not business:
        raise create_404("Business not found")
    if business.owner_id != UUID(current_user):
        raise create_401("You are not authorized to edit this business")
    for key, value in data.model_dump(exclude_unset=True,exclude={"services"}).items():

        print(f"Updating business field {key} to {value}")
        setattr(business, key, value)


    print(f"Busines got updated: {business}")
    session.add(business)
    print(f"Busines got added")
    if data.services is not None:
        updated_services = {service_data.id: service_data for service_data in data.services if service_data.id is not None}

        service_result = await session.exec(select(BusinessService).where(BusinessService.business_id == id))
        existing_services = service_result.all()
        for service in existing_services:
            if service.id not in updated_services:
                await session.delete(service)
        for service_data in data.services:
            print(f"Business service got created: {service_data}")
            if service_data.id is None:
                new_service = BusinessService(**service_data.model_dump(exclude_unset=True))
                print(f"Business service got created: {new_service}")
                session.add(new_service)
                continue
            service_result = await session.exec(select(BusinessService).where(BusinessService.id == service_data.id, BusinessService.business_id == id))
            service = service_result.first()
            print(f"Found existing service: {service}")
            for key, value in service_data.model_dump(exclude_unset=True).items():
                print(f"setting value: {key} to {value}")
                setattr(service, key, value)
            session.add(service)

        print(f"finished update now removing old services")


    print(f"session lenthgth: {len(session.new)}")    
    await session.commit()
    await session.refresh(business)


    statement= select(LaundryBusiness).where(LaundryBusiness.id==id).options(selectinload(LaundryBusiness.services).selectinload(BusinessService.laundry_service))
    result = await session.exec(statement)
    business= result.first()

    print(f"Business found: {business.services}")
    if not business:
        raise create_404("Business not found")
    return business

async def create_business( data: BusinessWrite,current_user: uuid.UUID,session: AsyncSession) -> BusinessRead:
     user_result= await session.exec(select(User).where(User.id==current_user,User.status==UserStatus.ACTIVE,User.role=="MERCHANT"))
     user = user_result.first()
     if not user:
         raise create_404("User not found")
     business = LaundryBusiness(**data.model_dump(exclude_unset=True))
     business.owner_id=current_user
     business.business_license_number="1234567890"
     session.add(business)
     await session.commit()
     await session.refresh(business)
     return BusinessRead.model_validate(business)

async def remove_business(business_id: UUID, current_user: uuid.UUID, session: AsyncSession) -> None:
    business_result = await session.exec(select(LaundryBusiness).where(LaundryBusiness.id == business_id))
    business = business_result.first()
    if not business:
        raise create_404("Business not found")
    

    logging.info(f"Business found: {business.id}, owner_id: {business.owner_id != current_user}, current_user: {current_user}")
    if business.owner_id != UUID(current_user):
        raise create_401("You are not authorized to delete this business")
    
    if business.status==ShopStatus.PENDING: 
        business.status=ShopStatus.DEACTIVATED
    else:
        business.status=ShopStatus.PENDING_DEACTIVATION
    
    session.add(business)
    await session.commit()