import decimal
from uuid import UUID
import uuid

from pydantic_extra_types import payment
from sqlalchemy import func
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.reponse_model import Page
from app.exceptions.http import create_400, create_404
from app.lib.datetime import utc_now
from app.modules.orders.models import Order
from app.modules.payments.models import CurrencyType, PaidByType, Payment, PaymentMethod, PaymentStatus, PaymentType
from app.modules.payments.schema import PaymentConfirm, PaymentCreate, PaymentRead, PaymentUpdate


async def list_payments(
    session: AsyncSession,
    *,
    order_id: UUID | None = None,
    page: int = 1,
    size: int = 10,
) -> Page[PaymentRead]:
    offset = (page - 1) * size
    statement = select(Payment).order_by(Payment.created_at.desc()).offset(offset).limit(size)
    count_statement = select(func.count(Payment.id))

    if order_id is not None:
        statement = statement.where(Payment.order_id == order_id)
        count_statement = count_statement.where(Payment.order_id == order_id)

    total = (await session.exec(count_statement)).one()
    payments = (await session.exec(statement)).all()
    return Page[PaymentRead](
        items=payments,
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size,
    )


async def get_payment(payment_id: UUID, session: AsyncSession) -> PaymentRead:
    payment = await get_payment_by_id(payment_id,session)
    if payment is None:
        raise create_404("Payment not found")
    return payment




async def get_payment_by_id(payment_id: UUID, session: AsyncSession) -> Payment:
    payment = await session.get(Payment, payment_id)
    return payment

async def create_payment(data: PaymentCreate, session: AsyncSession) -> PaymentRead:
    if data.amount < 0:
        raise create_400("Payment amount cannot be negative")

    order = await session.get(Order, data.order_id)
    if order is None:
        raise create_404("Order not found")

    payment = Payment(**data.model_dump(exclude_none=True))
    if payment.paid_at is None:
        payment.paid_at = utc_now()

    session.add(payment)
    await session.commit()
    await session.refresh(payment)
    return payment


# update payment assignment id
async def update_payment_for_pickup(id:uuid.UUID, ass_id:uuid.UUID, amount: decimal.Decimal, session:AsyncSession)->Payment:
    payment = await get_payment_by_id(id,session);
    payment.assignment_id=ass_id;
    payment.type= PaymentType.PICKUP_FEE
    payment.amount = amount
    session.add(payment)
    await session.commit()
    await session.refresh(payment)
    return payment



async def create_delivery_payment(
    order_id: uuid.UUID,
    assignment_id: uuid.UUID,
    amount: decimal.Decimal,
    session: AsyncSession,
) -> Payment:
    existing = (await session.exec(select(Payment).where(Payment.order_id == order_id))).first()
    method = existing.method if existing else PaymentMethod.CASH
    currency = existing.currency if existing else CurrencyType.USD

    payment = Payment(
        order_id=order_id,
        assignment_id=assignment_id,
        method=method,
        status=PaymentStatus.PENDING,
        amount=amount,
        currency=currency,
        paid_by=PaidByType.CUSTOMER,
        paid_at=utc_now(),
        type=PaymentType.FINAL_PAYMENT,
    )
    session.add(payment)
    await session.commit()
    await session.refresh(payment)
    return payment


async def get_pending_payment_by_order_id(order_id: uuid.UUID,session: AsyncSession)->Payment:
    payment_statement = select(Payment).where(Payment.order_id==order_id,Payment.status=="PENDING")
    payment_res= await session.exec(payment_statement);
    payment= payment_res.one_or_none()
    return payment

async def update_payment(payment_id: UUID, data: PaymentUpdate, session: AsyncSession) -> PaymentRead:
    payment = await session.get(Payment, payment_id)
    if payment is None:
        raise create_404("Payment not found")

    update_data = data.model_dump(exclude_unset=True)
    if update_data.get("amount") is not None and update_data["amount"] < 0:
        raise create_400("Payment amount cannot be negative")

    for key, value in update_data.items():
        setattr(payment, key, value)

    payment.updated_at = utc_now()
    session.add(payment)
    await session.commit()
    await session.refresh(payment)
    return payment


async def update_plain_payment(payment: Payment,session:AsyncSession)->Payment:
    session.add(payment)
    await session.commit()
    await session.refresh(payment)
    return payment

# async def update_
async def confirm_payment(payment_id: UUID, data: PaymentConfirm, session: AsyncSession) -> PaymentRead:
    payment = await session.get(Payment, payment_id)
    if payment is None:
        raise create_404("Payment not found")
    if payment.status != PaymentStatus.PENDING:
        raise create_400("Only pending payments can be confirmed")

    payment.status = PaymentStatus.SUCCESS
    payment.confirmed_by = data.confirmed_by
    payment.paid_at = utc_now()
    payment.updated_at = utc_now()
    session.add(payment)
    await session.commit()
    await session.refresh(payment)
    return payment


async def delete_payment(payment_id: UUID, session: AsyncSession) -> bool:
    payment = await session.get(Payment, payment_id)
    if payment is None:
        raise create_404("Payment not found")

    await session.delete(payment)
    await session.commit()
    return True
