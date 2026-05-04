
from datetime import datetime
import logging
from uuid import UUID
import uuid
from venv import logger
from sqlalchemy import func, and_
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import selectinload
from app.api.reponse_model import Page
from app.exceptions.http import create_401, create_403, create_404, create_409
from app.modules.business_services.model import BusinessService
from app.modules.businesses.models import LaundryBusiness, ShopStatus
from app.modules.businesses.schema import BusinessRead, BusinessUpdate, BusinessWrite, ShopStatusAction, ShopStatusResponse, ShopStatusUpdate, SingleBusinessRead
from app.modules.orders.models import Order, OrderStatus
from app.modules.reviews.models import ShopReview
from app.modules.reviews.schema import ShopReviewSummary
from app.modules.users.models import User, UserStatus

logger=logging.getLogger(__name__)
async def _batch_review_summaries(
    business_ids: list[UUID], session: AsyncSession
) -> dict[UUID, ShopReviewSummary]:
    if not business_ids:
        return {}
    rows = (
        await session.exec(
            select(
                ShopReview.business_id,
                func.coalesce(func.avg(ShopReview.rating), 0).label("avg_rating"),
                func.count(ShopReview.id).label("total"),
            )
            .where(ShopReview.business_id.in_(business_ids))
            .group_by(ShopReview.business_id)
        )
    ).all()
    return {
        row.business_id: ShopReviewSummary(
            business_id=row.business_id,
            average_rating=round(float(row.avg_rating), 1),
            total_reviews=row.total,
        )
        for row in rows
    }

async def list_my_businesses(
    owner_id: uuid.UUID | str, session: AsyncSession, page: int, size: int
) -> Page[BusinessRead]:
    if isinstance(owner_id, str):
        owner_id = UUID(owner_id)
    offset = (page - 1) * size
    statement = (
        select(LaundryBusiness)
        .where(LaundryBusiness.owner_id == owner_id, LaundryBusiness.status != ShopStatus.DEACTIVATED)
        .options(selectinload(LaundryBusiness.owner))
        .offset(offset)
        .limit(size)
    )
    count_statement = select(func.count(LaundryBusiness.id)).where(
        LaundryBusiness.owner_id == owner_id, LaundryBusiness.status != ShopStatus.DEACTIVATED
    )
    total = (await session.exec(count_statement)).one()
    businesses = (await session.exec(statement)).all()

    summaries = await _batch_review_summaries([b.id for b in businesses], session)
    items = []
    for b in businesses:
        read = BusinessRead.model_validate(b)
        read.review_summary = summaries.get(b.id)
        items.append(read)

    return Page[BusinessRead](items=items, total=total, page=page, size=size, pages=(total + size - 1) // size)


async def list_businesses(session: AsyncSession, page: int, size: int, status: ShopStatus = None, is_open: bool = None, q: str = None) -> Page[BusinessRead]:

    offset= (page-1)*size

    statement= select(LaundryBusiness).join(User).offset(offset).limit(size).where(LaundryBusiness.status!=ShopStatus.DEACTIVATED).options(selectinload(LaundryBusiness.owner))

    count_statement= select(func.count(LaundryBusiness.id)).join(User).where(LaundryBusiness.status!=ShopStatus.DEACTIVATED)
    if status:
        statement= statement.where(LaundryBusiness.status==status)
        count_statement= count_statement.where(LaundryBusiness.status==status)

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
    businesses = result.all()
    logging.info("======= Query businesses result ======= %s", len(businesses))

    summaries = await _batch_review_summaries([b.id for b in businesses], session)
    items = []
    for b in businesses:
        read = BusinessRead.model_validate(b)
        read.review_summary = summaries.get(b.id)
        items.append(read)

    return Page[BusinessRead](items=items, total=total, page=page, size=size, pages=(total + size - 1) // size)


async def list_one_business(id: UUID, session: AsyncSession) -> SingleBusinessRead:
    statement = select(LaundryBusiness).where(LaundryBusiness.id == id).options(selectinload(LaundryBusiness.services).selectinload(BusinessService.laundry_service))
    result = await session.exec(statement)
    business = result.first()
    if not business:
        raise create_404("Business not found")

    summaries = await _batch_review_summaries([business.id], session)
    read = SingleBusinessRead.model_validate(business)
    read.review_summary = summaries.get(business.id)
    return read



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

    if not business:
        raise create_404("Business not found")

    summaries = await _batch_review_summaries([business.id], session)
    read = SingleBusinessRead.model_validate(business)
    read.review_summary = summaries.get(business.id)
    return read

async def create_business( data: BusinessWrite,current_user: uuid.UUID | str,session: AsyncSession) -> BusinessRead:
     owner_uuid = UUID(current_user) if isinstance(current_user, str) else current_user
     user_result= await session.exec(select(User).where(User.id==owner_uuid,User.status==UserStatus.ACTIVE,User.role=="MERCHANT"))
     user = user_result.first()
     if not user:
         raise create_404("User not found")
     business = LaundryBusiness(**data.model_dump(exclude_unset=True))
     business.owner_id=owner_uuid
     business.business_license_number="1234567890"
     session.add(business)
     await session.commit()
     await session.refresh(business)
     return BusinessRead.model_validate(business)

_ACTIVE_ORDER_STATUSES = [
    OrderStatus.PENDING,
    OrderStatus.CONFIRMED,
    OrderStatus.PICKUP_ASSIGNED,
    OrderStatus.OUT_FOR_PICKUP,
    OrderStatus.PICKED_UP,
    OrderStatus.DELIVERED_TO_SHOP,
    OrderStatus.PROCESSING,
    OrderStatus.READY_FOR_DELIVERY,
    OrderStatus.DELIVERY_ASSIGNED,
    OrderStatus.OUT_FOR_DELIVERY,
    OrderStatus.PICKED_UP_DELIVERY,
]


async def toggle_shop_status(
    business_id: UUID,
    data: ShopStatusUpdate,
    current_user: uuid.UUID,
    session: AsyncSession,
) -> ShopStatusResponse:
    business_result = await session.exec(select(LaundryBusiness).where(LaundryBusiness.id == business_id))
    business = business_result.first()
    if not business:
        raise create_404("Business not found")
    logger.info(f"business owner: {business.owner_id}, current_user: {current_user}")
    if business.owner_id != UUID(current_user):
        raise create_403("You are not authorized to manage this shop")

    if data.action == ShopStatusAction.CLOSE:
        if business.status == ShopStatus.CLOSED:
            raise create_409("Shop is already closed")

        if not data.force:
            active_count_result = await session.exec(
                select(func.count(Order.id)).where(
                    Order.business_id == business_id,
                    Order.status.in_(_ACTIVE_ORDER_STATUSES),
                )
            )
            active_count = active_count_result.one()
            if active_count > 0:
                return ShopStatusResponse(
                    shop_id=business_id,
                    status=business.status.value,
                    message="Shop not closed yet. Confirm to proceed.",
                    warning=f"You have {active_count} active order{'s' if active_count != 1 else ''}. Closing will not cancel existing orders.",
                    active_order_count=active_count,
                )

        business.status = ShopStatus.CLOSED
        session.add(business)
        await session.commit()
        return ShopStatusResponse(
            shop_id=business_id,
            status=ShopStatus.CLOSED.value,
            message="Shop has been closed successfully.",
        )

    # action == OPEN
    if business.status in (ShopStatus.OPEN, ShopStatus.APPROVED):
        raise create_409("Shop is already open")

    business.status = ShopStatus.OPEN
    session.add(business)
    await session.commit()
    return ShopStatusResponse(
        shop_id=business_id,
        status=ShopStatus.OPEN.value,
        message="Shop is now open.",
    )


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