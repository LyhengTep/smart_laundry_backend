import decimal
import logging
from uuid import UUID
import uuid

from sqlalchemy import func,and_,or_
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.reponse_model import Page
from app.exceptions.http import create_400, create_404
from app.lib.datetime import utc_now
from app.modules.orders.models import Order
from app.modules.payments.models import CurrencyType, PaidByType, Payment, PaymentMethod, PaymentStatus, PaymentType
from app.modules.payments.schema import BusinessRevenueRead, DriverRevenueRead, PaymentConfirm, PaymentCreate, PaymentRead, PaymentUpdate
from app.patterns.factories.payment_factory import create_initial_payment_factory

logger=logging.getLogger(__name__)
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
    """Create a manual payment record for an existing order. Validates order existence and non-negative amount."""
    if data.amount < 0:
        raise create_400("Payment amount cannot be negative")

    order = await session.get(Order, data.order_id)
    if order is None:
        raise create_404("Order not found")

    payment = create_initial_payment_factory(data)
    # if payment.paid_at is None:
    #     payment.paid_at = utc_now()

    session.add(payment)
    await session.commit()
    await session.refresh(payment)
    return payment




# update payment assignment id
async def update_payment_for_pickup(id:uuid.UUID, ass_id:uuid.UUID, amount: decimal.Decimal, session:AsyncSession)->Payment:
    """Link a payment to a pickup assignment and set its type to PICKUP_FEE with the actual collected amount."""
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
    payment_type: PaymentType = PaymentType.DELIVERY_FEE,
    status: PaymentStatus = PaymentStatus.PENDING,
) -> Payment:
    """Create a delivery/washing-fee payment; inherits method and currency from the order's first payment."""
    existing = (await session.exec(select(Payment).where(Payment.order_id == order_id,Payment.type == payment_type))).first()

    if existing:
            return existing
    payment = Payment(
        order_id=order_id,
        assignment_id=assignment_id,
        method=PaymentMethod.CASH,
        status=status,
        amount=amount,
        currency=CurrencyType.USD,
        paid_by=PaidByType.CUSTOMER,
        paid_at=utc_now(),
        type=payment_type,
    )
    session.add(payment)
    await session.commit()
    await session.refresh(payment)
    return payment


async def create_pending_settlement_payment(
    order_id: uuid.UUID,
    assignment_id: uuid.UUID,
    amount: decimal.Decimal,
    payment_type: PaymentType,
    session: AsyncSession,
) -> Payment:
    """Create a PENDING_SETTLEMENT payment paid by SHOP, used when the shop advances the pickup fee on behalf of the customer."""
    existing = (await session.exec(select(Payment).where(Payment.order_id == order_id))).first()
    method = existing.method if existing else PaymentMethod.CASH
    currency = existing.currency if existing else CurrencyType.USD

    payment = Payment(
        order_id=order_id,
        assignment_id=assignment_id,
        method=method,
        status=PaymentStatus.PENDING_SETTLEMENT,
        amount=amount,
        currency=currency,
        paid_by=PaidByType.SHOP,
        type=payment_type,
    )
    session.add(payment)
    await session.commit()
    await session.refresh(payment)
    return payment


async def get_advance_settlement(order_id: uuid.UUID, session: AsyncSession) -> Payment | None:
    return (
        await session.exec(
            select(Payment).where(
                Payment.order_id == order_id,
                Payment.status == PaymentStatus.COLLECTED,
                Payment.type == PaymentType.ADVANCE_SETTLEMENT,
            )
        )
    ).first()


async def settle_shop_advance_payment(
    order_id: uuid.UUID,
    assignment_id: uuid.UUID,
    payment_type: PaymentType,
    session: AsyncSession,
) -> Payment | None:
    """Settle a pending shop advance: creates a COLLECTED ADVANCE_SETTLEMENT payment and marks the source as SETTLED."""
    pending = (
        await session.exec(
            select(Payment).where(
                Payment.order_id == order_id,
                Payment.status == PaymentStatus.PENDING_SETTLEMENT,
                Payment.type == payment_type,
            )
        )
    ).first()
    if pending is None:
        return None

    settlement = Payment(
        order_id=order_id,
        assignment_id=assignment_id,
        method=pending.method,
        status=PaymentStatus.COLLECTED,
        amount=pending.amount,
        currency=pending.currency,
        paid_by=PaidByType.SHOP,
        type=PaymentType.ADVANCE_SETTLEMENT,
    )
    session.add(settlement)
    await session.flush()

    pending.status = PaymentStatus.SETTLED
    pending.settled_by_payment_id = settlement.id
    pending.updated_at = utc_now()
    session.add(pending)
    await session.commit()
    await session.refresh(settlement)
    return settlement


async def collect_assignment_payments(assignment_id: uuid.UUID, session: AsyncSession) -> None:
    """Mark all PENDING payments for an assignment as COLLECTED (called when delivery is completed)."""
    payments = (
        await session.exec(
            select(Payment).where(
                Payment.assignment_id == assignment_id,
                Payment.status == PaymentStatus.PENDING,
            )
        )
    ).all()
    for payment in payments:
        payment.status = PaymentStatus.COLLECTED
        payment.paid_at = utc_now()
        payment.updated_at = utc_now()
        session.add(payment)
    await session.commit()


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
    """Confirm a PENDING payment as COLLECTED; rejects if already confirmed."""
    payment = await session.get(Payment, payment_id)
    if payment is None:
        raise create_404("Payment not found")
    if payment.status != PaymentStatus.PENDING:
        raise create_400("Only pending payments can be confirmed")

    payment.status = PaymentStatus.COLLECTED
    payment.confirmed_by = data.confirmed_by
    payment.paid_at = utc_now()
    payment.updated_at = utc_now()
    session.add(payment)
    await session.commit()
    await session.refresh(payment)
    return payment


async def get_driver_revenue(driver_id: UUID, session: AsyncSession) -> DriverRevenueRead:
    """Sum COLLECTED/SETTLED PICKUP_FEE and DELIVERY_FEE payments across all assignments for a driver."""
    from app.modules.drivers.models import DriverAssignment

    total = (
        await session.exec(
            select(func.coalesce(func.sum(Payment.amount), 0)).join(
                DriverAssignment, Payment.assignment_id == DriverAssignment.id
            ).where(
                DriverAssignment.driver_id == driver_id,
               Payment.type.in_([PaymentType.PICKUP_FEE, PaymentType.DELIVERY_FEE]),
                or_(
                        Payment.status==PaymentStatus.COLLECTED,
                        Payment.status==PaymentStatus.SETTLED,
                )
            
            )
        )
    ).one()

    logger.info(f'receive total revenue {total} {driver_id}')
    return DriverRevenueRead(
        driver_id=driver_id,
        total_revenue=decimal.Decimal(str(total)),
        currency=CurrencyType.USD,
    )


async def get_business_revenue(business_id: UUID, session: AsyncSession) -> BusinessRevenueRead:
    """Sum COLLECTED WASHING_SERVICE_FEE payments for all orders belonging to a business."""
    total = (
        await session.exec(
            select(func.coalesce(func.sum(Payment.amount), 0))
            .join(Order, Payment.order_id == Order.id)
            .where(
                Order.business_id == business_id,
                Payment.status == PaymentStatus.COLLECTED,
                Payment.type == PaymentType.WASHING_SERVICE_FEE,
            )
        )
    ).one()
    return BusinessRevenueRead(
        business_id=business_id,
        total_revenue=decimal.Decimal(str(total)),
        currency=CurrencyType.USD,
    )


async def delete_payment(payment_id: UUID, session: AsyncSession) -> bool:
    payment = await session.get(Payment, payment_id)
    if payment is None:
        raise create_404("Payment not found")

    await session.delete(payment)
    await session.commit()
    return True
