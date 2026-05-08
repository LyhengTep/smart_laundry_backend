from __future__ import annotations

from decimal import Decimal
import json
import logging
from uuid import UUID, uuid4

from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import selectinload
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy import func
from app.api.reponse_model import Page
from app.core.config import TOPIC_DELIVERY_ASSIGNMENT, TOPIC_PICKUP_ASSIGNMENT
from app.core.firebase import send_firebase_message
from app.exceptions.http import create_400, create_404
from app.lib.aws import send_sqs_message
from app.modules.device_tokens.models import DeviceToken
from app.modules.realtime.manager import connection_manager
from app.modules.business_services.model import BusinessService
from app.modules.businesses.models import LaundryBusiness
from app.modules.notifications.models import Notification, NotificationChannel, NotificationStatus, NotificationType
from app.modules.orders.models import Order, OrderItem, OrderStatus
from app.modules.orders.schema import (
    OrderCreate,
    OrderCreateItem,
    OrderPricingUpdate,
    OrderRead,
    OrderStatusUpdate,
    OrderTrackingRead,
)

import app.modules.orders.repository as order_repo
from app.modules.payments.models import PaidByType, Payment, PaymentStatus
from app.modules.users.models import RoleName, User
from app.patterns.factories.order_factory import create_order_factory
from app.shared.common import get_notification_template, get_notification_title, utc_now

logger=logging.getLogger(__name__)
ORDER_STATUS_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PENDING: {OrderStatus.CONFIRMED, OrderStatus.CANCELLED},
    OrderStatus.CONFIRMED: {OrderStatus.PICKUP_ASSIGNED,OrderStatus.OUT_FOR_PICKUP, OrderStatus.CANCELLED},
    OrderStatus.PICKUP_ASSIGNED: {OrderStatus.PICKED_UP,OrderStatus.OUT_FOR_PICKUP, OrderStatus.CANCELLED},
    OrderStatus.OUT_FOR_PICKUP: {OrderStatus.PICKED_UP, OrderStatus.CANCELLED},
    OrderStatus.PICKED_UP: {OrderStatus.DELIVERED_TO_SHOP},
    OrderStatus.DELIVERED_TO_SHOP: {OrderStatus.PROCESSING},
    OrderStatus.PROCESSING: {OrderStatus.READY_FOR_DELIVERY},
    OrderStatus.READY_FOR_DELIVERY: {OrderStatus.DELIVERY_ASSIGNED,OrderStatus.OUT_FOR_DELIVERY},
    OrderStatus.DELIVERY_ASSIGNED: {OrderStatus.OUT_FOR_DELIVERY},
    OrderStatus.OUT_FOR_DELIVERY: {OrderStatus.PICKED_UP_DELIVERY},
    OrderStatus.PICKED_UP_DELIVERY:{OrderStatus.DELIVERED},
    OrderStatus.DELIVERED: set(),
    OrderStatus.CANCELLED: {OrderStatus.PICKUP_ASSIGNED, OrderStatus.OUT_FOR_DELIVERY,OrderStatus.PENDING,},
}



def pricing_type_to_measure_type(pricing_type: str) -> str:
    if pricing_type == "per_kg":
        return "kg"
    if pricing_type == "per_item":
        return "item"
    return "fixed"


def calculate_order_item_subtotal(unit_price: float, quantity: float) -> float:
    if unit_price < 0:
        raise create_400("Unit price cannot be negative")
    if quantity <= 0:
        raise create_400("Quantity must be greater than zero")
    return round(unit_price * quantity, 2)


def calculate_order_total(subtotals: list[float], discount: float = 0, delivery_fee: float = 0,pickup_fee:float=0) -> float:
    if discount < 0:
        raise create_400("Discount cannot be negative")
    if delivery_fee < 0:
        raise create_400("Delivery fee cannot be negative")
    if pickup_fee < 0:
        raise create_400("Pickup fee cannot be negative")
    subtotal = round(sum(subtotals), 2)
    if discount > subtotal:
        raise create_400("Discount cannot be greater than subtotal")
    return round((subtotal - discount) + delivery_fee + pickup_fee, 2)


def validate_status_transition(current_status: OrderStatus, new_status: OrderStatus) -> None:
    if current_status == new_status:
        raise create_400("Order is already in the requested status")
    allowed_statuses = ORDER_STATUS_TRANSITIONS[current_status]
    if new_status not in allowed_statuses:
        raise create_400(f"Cannot change order status from {current_status} to {new_status}")


def build_order_event_payload(event: str, order: OrderRead) -> dict:
    return {
        "event": event,
        "order_id": str(order.id),
        "customer_id": str(order.customer_id),
        "business_id": str(order.business_id),
        "status": order.status.value,
        "data": jsonable_encoder(order),
    }


def build_initial_order_payment(order: Order, data: OrderCreate) -> Payment:
    return Payment(
        order_id=order.id,
        method=data.payment_method,
        status=PaymentStatus.PENDING,
        amount=Decimal(str(order.total)),
        currency=data.payment_currency,
        paid_by=PaidByType.CUSTOMER,
        paid_at=utc_now(),
    )


async def update_pending_order_payment_amount(order: Order, session: AsyncSession) -> None:
    statement = select(Payment).where(
        Payment.order_id == order.id,
        Payment.status == PaymentStatus.PENDING,
        Payment.paid_by == PaidByType.CUSTOMER,
    )
    result = await session.exec(statement)
    for payment in result.all():
        payment.amount = Decimal(str(order.total))
        payment.updated_at = utc_now()
        session.add(payment)


async def broadcast_order_event(event: str, order: OrderRead) -> None:
    payload = build_order_event_payload(event=event, order=order)
    await connection_manager.send_json(f"order:{order.id}", payload)
    await connection_manager.send_json(f"user:{order.customer_id}", payload)

def build_order_items(
    items_data: list[OrderCreateItem],
    business_services_by_id: dict[UUID, BusinessService],
) -> tuple[list[OrderItem], float]:
    if not items_data:
        raise create_400("Order must include at least one item")

    snapshots: list[OrderItem] = []
    subtotals: list[float] = []
    seen_service_ids: set[UUID] = set()

    for item_data in items_data:
        if item_data.business_service_id in seen_service_ids:
            raise create_400("Duplicate business service is not allowed in the same order")
        seen_service_ids.add(item_data.business_service_id)

        business_service = business_services_by_id.get(item_data.business_service_id)
        if business_service is None:
            raise create_400("One or more order items reference an invalid business service")
        if business_service.laundry_service is None:
            raise create_400("Business service is missing laundry service details")

        final_quantity = item_data.quantity
        subtotal = calculate_order_item_subtotal(
            unit_price=business_service.base_price,
            quantity=final_quantity,
        )
        subtotals.append(subtotal)
        snapshots.append(
            OrderItem(
                business_service_id=business_service.id,
                service_id=business_service.service_id,
                service_name=business_service.laundry_service.name.value,
                pricing_type=business_service.pricing_type,
                measure_type=pricing_type_to_measure_type(business_service.pricing_type.value),
                unit_price=business_service.base_price,
                quantity=final_quantity,
                sub_total=subtotal,
                note=item_data.note,
            )
        )

    return snapshots, round(sum(subtotals), 2)

async def list_orders(
    session: AsyncSession,
    customer_id: UUID | None = None,
    business_id: UUID | None = None,
    order_no: str | None = None,
    status: OrderStatus | None = None,
    page: int = 1,
    size: int = 10,
) -> Page[OrderRead]:
    offset = (page - 1) * size

    statement = (
        select(Order)
        .options(selectinload(Order.items))
        .order_by(Order.created_at.desc())
        .offset(offset)
        .limit(size)
    )
    count_statement = select(func.count(Order.id))

    if customer_id:
        statement = statement.where(Order.customer_id == customer_id)
        count_statement = count_statement.where(Order.customer_id == customer_id)
    if business_id:
        statement = statement.where(Order.business_id == business_id)
        count_statement = count_statement.where(Order.business_id == business_id)
    if order_no:
        statement = statement.where(Order.order_no.ilike(f"%{order_no}%"))
        count_statement = count_statement.where(Order.order_no.ilike(f"%{order_no}%"))
    if status:
        statement = statement.where(Order.status == status)
        count_statement = count_statement.where(Order.status == status)

    total_result = await session.exec(count_statement)
    total = total_result.one()
    result = await session.exec(statement)
    return Page[OrderRead](
        items=result.all(),
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size,
    )

async def search_order_by_order_no(order_no: str, session: AsyncSession) -> OrderTrackingRead:
    statement = select(Order).where(Order.order_no == order_no).options(selectinload(Order.items))
    result = await session.exec(statement)
    order = result.first()
    if order is None:
        raise create_404("Order not found")
    return order


async def get_order_by_id(order_id: UUID, session: AsyncSession) -> OrderRead:
    statement = select(Order).where(Order.id == order_id).options(selectinload(Order.items))
    result = await session.exec(statement)
    order = result.first()
    if order is None:
        raise create_404("Order not found")
    return order

async def create_order(session: AsyncSession, data: OrderCreate) -> OrderRead:
    customer = await session.get(User, data.customer_id)
    if customer is None:
        raise create_404("Customer not found")
    if customer.role != RoleName.CUSTOMER:
        raise create_400("Order customer must have CUSTOMER role")

    business = await session.get(LaundryBusiness, data.business_id)
    if business is None:
        raise create_404("Business not found")

    business_service_ids = [item.business_service_id for item in data.items]
    statement = (
        select(BusinessService)
        .where(
            BusinessService.business_id == data.business_id,
            BusinessService.id.in_(business_service_ids),
            BusinessService.is_active == True,
        )
        .options(selectinload(BusinessService.laundry_service))
    )
    result = await session.exec(statement)
    business_services = result.all()
    business_services_by_id = {service.id: service for service in business_services}

    order_items, subtotal = build_order_items(
        items_data=data.items,
        business_services_by_id=business_services_by_id,
    )

    order = create_order_factory(data, subtotal, total=calculate_order_total(
            [item.sub_total for item in order_items],
            discount=data.discount,
            delivery_fee=0,
        ),
        order_item=order_items
    )

    session.add(order)
    payment = build_initial_order_payment(order, data)
    session.add(payment)
    await session.commit()
    await session.refresh(order)

    order_with_items = await order_repo.get_by_id(order.id, session)
    await broadcast_order_event("order_created", order_with_items)
    return order_with_items

async def notification_processor(order: Order, current_user_id: UUID, session: AsyncSession):
    try:
        customer_notification_types = [OrderStatus.CANCELLED, OrderStatus.DELIVERED_TO_SHOP, OrderStatus.DELIVERED]
        if order.status not in customer_notification_types:
            return

        title = get_notification_title(order.status)
        body = get_notification_template(order.status, order_no=order.order_no)

        statement = select(DeviceToken).where(DeviceToken.user_id == order.customer_id)
        res = await session.exec(statement)
        device = res.first()

        push_status = NotificationStatus.SENT
        channel = NotificationChannel.IN_APP

        if device is not None and str(order.customer_id) != str(current_user_id):
            channel = NotificationChannel.PUSH
            try:
                send_firebase_message(token=device.token, title=title, body=body)
            except Exception as firebase_err:
                logger.warning(f"Firebase push failed for order {order.id}: {firebase_err}")
                push_status = NotificationStatus.FAILED

        notification = Notification(
            user_id=order.customer_id,
            type=NotificationType.ORDER_STATUS,
            title=title,
            message=body,
            reference_id=order.id,
            reference_type="ORDER",
            channel=channel,
            status=push_status,
        )
        session.add(notification)
        await session.commit()

    except Exception as e:
        logger.error(f"Unknown error in notification processor {e}")

async def update_order_status_api(order_id: UUID,
    data: OrderStatusUpdate,
    session: AsyncSession,current_user_id: UUID)->OrderRead:

    order = await update_order_status(order_id=order_id,data= data,session=session)
    logger.info(f"called update order status api {order}")
    #Process notification based on status
    await notification_processor(order=order,current_user_id=current_user_id,session=session)
   
    # Broadcast event to pickup assignment service when order is confirmed, so that it can assign driver for pickup
    if data.status == OrderStatus.CONFIRMED:
        send_sqs_message(
                    queue_name=TOPIC_PICKUP_ASSIGNMENT,
                    message_body=json.dumps({
                        "order_id": str(order.id),
                        "type": "PICKUP"
                    })
                ) 
            
    if data.status == OrderStatus.READY_FOR_DELIVERY or data.status == OrderStatus.DELIVERY_ASSIGNED:
            send_sqs_message(
                    queue_name=TOPIC_DELIVERY_ASSIGNMENT,
                    message_body=json.dumps({
                        "order_id": str(order.id),
                        "type": "DELIVERY"
                    })
                ) 
    return order

async def mark_order_payment_received(order: Order, session: AsyncSession) -> None:
    statement = select(Payment).where(
        Payment.order_id == order.id,
        Payment.status == PaymentStatus.PENDING,
        Payment.paid_by == PaidByType.CUSTOMER,
    )
    result = await session.exec(statement)
    for payment in result.all():
        payment.status = PaymentStatus.COLLECTED
        payment.paid_at = utc_now()
        payment.updated_at = utc_now()
        session.add(payment)

async def update_order_status(
    order_id: UUID,
    data: OrderStatusUpdate,
    session: AsyncSession,
) -> OrderRead:
    order = await get_order_by_id(order_id=order_id, session=session)
    logger.info(f"Updating order {order_id} status from {order.status} to {data.status}")
    validate_status_transition(order.status, data.status)

    if data.driver_id is not None:
        order.driver_id = data.driver_id

    if data.pickup_fee is not None:
        if data.status != OrderStatus.CONFIRMED:
            raise create_400("Delivery fee can only be set when confirming an order")
        order.pickup_fee = data.pickup_fee
        order.delivery_fee = data.pickup_fee
        total= calculate_order_total(
            [item.sub_total for item in order.items],
            discount=order.discount,
            delivery_fee=order.delivery_fee,
            pickup_fee=order.pickup_fee
        )
        order.total = total 
        await update_pending_order_payment_amount(order=order, session=session)

    if data.delivery_fee_paid_by is not None:
        if data.status not in {OrderStatus.PICKED_UP, OrderStatus.PICKED_UP_DELIVERY}:
            raise create_400("Delivery fee payer can only be set at pickup")
        order.delivery_fee_paid_by = data.delivery_fee_paid_by

    order.status = data.status
    order.updated_at = utc_now()

    if data.status == OrderStatus.DELIVERED_TO_SHOP:
        await mark_order_payment_received(order=order, session=session)

    session.add(order)
    await session.commit()

    updated_order = await get_order_by_id(order_id=order_id, session=session)
    await broadcast_order_event("order_status_updated", updated_order)
    return updated_order

async def update_order_pricing(
    order_id: UUID,
    data: OrderPricingUpdate,
    session: AsyncSession,
) -> OrderRead:
    order = await get_order_by_id(order_id=order_id, session=session)
    if order.status in {OrderStatus.CANCELLED, OrderStatus.DELIVERED}:
        raise create_400("Cannot update pricing for a completed or cancelled order")
    if order.status != OrderStatus.DELIVERED_TO_SHOP:
        raise create_400("Order item weight can only be updated after delivery to the shop")

    requested_item_ids = {item.order_item_id for item in data.items}
    existing_items = {item.id: item for item in order.items}
    if requested_item_ids != set(existing_items):
        raise create_400("Pricing update must include every order item exactly once")

    for item_update in data.items:
        order_item = existing_items[item_update.order_item_id]
        order_item.quantity = item_update.quantity
        order_item.sub_total = calculate_order_item_subtotal(
            unit_price=order_item.unit_price,
            quantity=item_update.quantity,
        )
        session.add(order_item)

    order.subtotal = round(sum(item.sub_total for item in existing_items.values()), 2)
    if data.discount is not None:
        order.discount = data.discount
    if data.delivery_fee is not None:
        order.delivery_fee = data.delivery_fee
    order.total = calculate_order_total(
        [item.sub_total for item in existing_items.values()],
        discount=order.discount,
        delivery_fee=order.delivery_fee,
        pickup_fee=order.pickup_fee
    )
    
    order.updated_at = utc_now()
    await update_pending_order_payment_amount(order=order, session=session)

    session.add(order)
    await session.commit()
    updated_order = await get_order_by_id(order_id=order_id, session=session)
    await broadcast_order_event("order_pricing_updated", updated_order)
    return updated_order
