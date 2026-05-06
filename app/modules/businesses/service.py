import logging
from uuid import UUID
import uuid

from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select

from app.api.reponse_model import Page
from app.exceptions.http import create_400, create_401, create_403, create_404, create_409
from app.modules.business_services.model import BusinessService
from app.modules.businesses.models import LaundryBusiness, ShopStatus
from app.modules.businesses.schema import (
    BusinessRead,
    BusinessUpdate,
    BusinessWrite,
    DeactivationAction,
    DeactivationActionRequest,
    ShopStatusAction,
    ShopStatusResponse,
    ShopStatusUpdate,
    SingleBusinessRead,
)
from app.modules.businesses import repository as repo
from app.modules.users.models import UserStatus
from app.modules.users import repository as user_repo

logger = logging.getLogger(__name__)


async def list_my_businesses(
    owner_id: uuid.UUID | str, session: AsyncSession, page: int, size: int
) -> Page[BusinessRead]:
    if isinstance(owner_id, str):
        owner_id = UUID(owner_id)
    page_result = await repo.list_by_owner(owner_id, session, page=page, size=size)
    summaries = await repo.batch_review_summaries([b.id for b in page_result.items], session)
    items = []
    for b in page_result.items:
        read = BusinessRead.model_validate(b)
        read.review_summary = summaries.get(b.id)
        items.append(read)
    return Page[BusinessRead](
        items=items,
        total=page_result.total,
        page=page_result.page,
        size=page_result.size,
        pages=page_result.pages,
    )


async def list_businesses(
    session: AsyncSession,
    page: int,
    size: int,
    status: ShopStatus = None,
    is_open: bool = None,
    q: str = None,
) -> Page[BusinessRead]:
    page_result = await repo.list_paginated(
        session, status=status, is_open=is_open, q=q, page=page, size=size
    )
    summaries = await repo.batch_review_summaries([b.id for b in page_result.items], session)
    items = []
    for b in page_result.items:
        read = BusinessRead.model_validate(b)
        read.review_summary = summaries.get(b.id)
        items.append(read)
    return Page[BusinessRead](
        items=items,
        total=page_result.total,
        page=page_result.page,
        size=page_result.size,
        pages=page_result.pages,
    )


async def list_one_business(id: UUID, session: AsyncSession) -> SingleBusinessRead:
    business = await repo.get_by_id_with_services(id, session)
    if not business:
        raise create_404("Business not found")
    summaries = await repo.batch_review_summaries([business.id], session)
    read = SingleBusinessRead.model_validate(business)
    read.review_summary = summaries.get(business.id)
    return read


async def edit_business(
    id: UUID, data: BusinessUpdate, current_user: uuid.UUID, session: AsyncSession
) -> SingleBusinessRead:
    business = await repo.get_by_id(id, session)
    if not business:
        raise create_404("Business not found")
    if business.owner_id != UUID(current_user):
        raise create_401("You are not authorized to edit this business")

    for key, value in data.model_dump(exclude_unset=True, exclude={"services"}).items():
        setattr(business, key, value)

    session.add(business)

    if data.services is not None:
        updated_services = {
            service_data.id: service_data
            for service_data in data.services
            if service_data.id is not None
        }
        existing_services = await repo.get_services_by_business(id, session)
        for service in existing_services:
            if service.id not in updated_services:
                await session.delete(service)
        for service_data in data.services:
            if service_data.id is None:
                session.add(BusinessService(**service_data.model_dump(exclude_unset=True)))
                continue
            service = await repo.get_service_by_id_and_business(service_data.id, id, session)
            if service:
                for key, value in service_data.model_dump(exclude_unset=True).items():
                    setattr(service, key, value)
                session.add(service)

    await session.commit()

    business = await repo.get_by_id_with_services(id, session)
    if not business:
        raise create_404("Business not found")
    summaries = await repo.batch_review_summaries([business.id], session)
    read = SingleBusinessRead.model_validate(business)
    read.review_summary = summaries.get(business.id)
    return read


async def create_business(
    data: BusinessWrite, current_user: uuid.UUID | str, session: AsyncSession
) -> BusinessRead:
    owner_uuid = UUID(current_user) if isinstance(current_user, str) else current_user
    user = await user_repo.get_by_id(owner_uuid, session)
    if not user or user.status != UserStatus.ACTIVE or user.role != "MERCHANT":
        raise create_404("User not found")
    business = LaundryBusiness(**data.model_dump(exclude_unset=True))
    business.owner_id = owner_uuid
    business.business_license_number = "1234567890"
    await repo.save(business, session)
    return BusinessRead.model_validate(business)


async def toggle_shop_status(
    business_id: UUID,
    data: ShopStatusUpdate,
    current_user: uuid.UUID,
    session: AsyncSession,
) -> ShopStatusResponse:
    business = await repo.get_by_id(business_id, session)
    if not business:
        raise create_404("Business not found")
    if business.owner_id != UUID(current_user):
        raise create_403("You are not authorized to manage this shop")

    if data.action == ShopStatusAction.CLOSE:
        if business.status == ShopStatus.CLOSED:
            raise create_409("Shop is already closed")
        if not data.force:
            active_count = await repo.count_active_orders(business_id, session)
            if active_count > 0:
                return ShopStatusResponse(
                    shop_id=business_id,
                    status=business.status.value,
                    message="Shop not closed yet. Confirm to proceed.",
                    warning=f"You have {active_count} active order{'s' if active_count != 1 else ''}. Closing will not cancel existing orders.",
                    active_order_count=active_count,
                )
        business.status = ShopStatus.CLOSED
        await repo.save(business, session)
        return ShopStatusResponse(
            shop_id=business_id,
            status=ShopStatus.CLOSED.value,
            message="Shop has been closed successfully.",
        )

    if business.status in (ShopStatus.OPEN, ShopStatus.APPROVED):
        raise create_409("Shop is already open")
    business.status = ShopStatus.OPEN
    await repo.save(business, session)
    return ShopStatusResponse(
        shop_id=business_id,
        status=ShopStatus.OPEN.value,
        message="Shop is now open.",
    )


async def remove_business(business_id: UUID, current_user: uuid.UUID, session: AsyncSession) -> None:
    business = await repo.get_by_id(business_id, session)
    if not business:
        raise create_404("Business not found")
    if business.owner_id != UUID(current_user):
        raise create_401("You are not authorized to delete this business")
    business.status = ShopStatus.DEACTIVATED if business.status == ShopStatus.PENDING else ShopStatus.PENDING_DEACTIVATION
    await repo.save(business, session)


async def resolve_deactivation(
    business_id: UUID,
    data: DeactivationActionRequest,
    session: AsyncSession,
) -> BusinessRead:
    """Approve or reject a PENDING_DEACTIVATION request; admin only."""
    business = await repo.get_by_id_with_owner(business_id, session)
    if not business:
        raise create_404("Business not found")
    if business.status != ShopStatus.PENDING_DEACTIVATION:
        raise create_400("Business is not pending deactivation")
    business.status = ShopStatus.DEACTIVATED if data.action == DeactivationAction.APPROVE else ShopStatus.CLOSED
    return await repo.save(business, session)
