from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.reponse_model import Page
from app.db.engine import get_session
from app.modules.payments import service as svc
from app.modules.payments.schema import PaymentConfirm, PaymentCreate, PaymentRead, PaymentUpdate


router = APIRouter(prefix="/payments", tags=["payments"])


@router.get("/", response_model=Page[PaymentRead])
async def list_payments(
    order_id: UUID | None = Query(default=None),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> Page[PaymentRead]:
    return await svc.list_payments(session=session, order_id=order_id, page=page, size=size)


@router.get("/{payment_id}", response_model=PaymentRead)
async def get_payment(payment_id: UUID, session: AsyncSession = Depends(get_session)) -> PaymentRead:
    return await svc.get_payment(payment_id=payment_id, session=session)


@router.post("/", response_model=PaymentRead)
async def create_payment(data: PaymentCreate, session: AsyncSession = Depends(get_session)) -> PaymentRead:
    return await svc.create_payment(data=data, session=session)


@router.patch("/{payment_id}", response_model=PaymentRead)
async def update_payment(
    payment_id: UUID,
    data: PaymentUpdate,
    session: AsyncSession = Depends(get_session),
) -> PaymentRead:
    return await svc.update_payment(payment_id=payment_id, data=data, session=session)


@router.post("/{payment_id}/confirm", response_model=PaymentRead)
async def confirm_payment(
    payment_id: UUID,
    data: PaymentConfirm,
    session: AsyncSession = Depends(get_session),
) -> PaymentRead:
    return await svc.confirm_payment(payment_id=payment_id, data=data, session=session)


@router.delete("/{payment_id}", response_model=bool)
async def delete_payment(payment_id: UUID, session: AsyncSession = Depends(get_session)) -> bool:
    return await svc.delete_payment(payment_id=payment_id, session=session)
