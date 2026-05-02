from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.reponse_model import Page
from app.db.engine import get_session
from app.lib.security import get_current_user
from app.modules.orders import service as svc
from app.modules.orders.models import OrderStatus
from app.modules.orders.schema import OrderCreate, OrderPricingUpdate, OrderRead, OrderStatusUpdate, OrderTrackingRead


router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("/", response_model=Page[OrderRead])
async def list_orders(
    customer_id: UUID | None = Query(default=None),
    business_id: UUID | None = Query(default=None),
    order_no: str | None = Query(default=None),
    status: OrderStatus | None = Query(default=None),
    page: int =Query(1,ge=1),size: int=Query(10,ge=1,le=100),
    session: AsyncSession = Depends(get_session),

) -> Page[OrderRead]:
    return await svc.list_orders(
        session=session,
        customer_id=customer_id,
        business_id=business_id,
        order_no=order_no,
        status=status,
        page=page,
        size=size, 
    )


@router.get("/search", response_model=OrderTrackingRead)
async def search_order(
    order_no: str = Query(..., description="Exact order number"),
    session: AsyncSession = Depends(get_session),
) -> OrderTrackingRead:
    return await svc.search_order_by_order_no(order_no=order_no, session=session)


@router.get("/{order_id}", response_model=OrderRead)
async def get_order(order_id: UUID, session: AsyncSession = Depends(get_session)) -> OrderRead:
    return await svc.get_order_by_id(order_id=order_id, session=session)


@router.post("/", response_model=OrderRead)
async def create_order(data: OrderCreate, session: AsyncSession = Depends(get_session)) -> OrderRead:
    return await svc.create_order(session=session, data=data)


@router.patch("/{order_id}/status", response_model=OrderRead)
async def update_order_status(
    order_id: UUID,
    data: OrderStatusUpdate,
    current_user: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> OrderRead:
    return await svc.update_order_status_api(order_id=order_id, data=data, session=session,current_user_id=current_user)


@router.patch("/{order_id}/pricing", response_model=OrderRead)
async def update_order_pricing(
    order_id: UUID,
    data: OrderPricingUpdate,
    session: AsyncSession = Depends(get_session),
) -> OrderRead:
    return await svc.update_order_pricing(order_id=order_id, data=data, session=session)
