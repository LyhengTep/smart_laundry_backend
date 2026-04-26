import decimal
import logging
from math import log
from uuid import UUID
import uuid
from alembic.command import current
from google_crc32c import value
from sqlalchemy import func
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import selectinload
from app.api.reponse_model import Page
from app.core.firebase import send_firebase_message
from app.db.engine import get_session, get_session_context
from app.exceptions.http import create_400, create_404
from app.lib.datetime import calulate_remaining_time
from app.modules.businesses.models import LaundryBusiness
from app.modules.device_tokens.models import DeviceToken
from app.modules.drivers.models import DARole, DAStatus, Driver, DriverAssignment, DriverAssignmentHistory, DriverStatus
from app.modules.drivers.schema import (
    ActiveAssignmentResponse,
    DriverAssignmentCreate,
    DriverAssignmentRead,
    DriverAssignmentStatusUpdate,
    DriverRead,
    DriverWrite,
)
from app.modules.orders.models import DeliveryFeePaidBy, Order, OrderStatus
from app.modules.orders.service import get_order_by_id, update_order_status, update_order_status_api
from app.modules.orders.schema import  OrderReadV2, OrderStatusUpdate
from app.modules.payments.models import PaymentStatus, PaymentType
from app.modules.payments.service import collect_assignment_payments, create_delivery_payment, create_pending_settlement_payment, get_pending_payment_by_order_id, settle_shop_advance_payment, update_payment_for_pickup
from app.modules.users.models import User, UserStatus
from app.modules.realtime.manager import connection_manager
import asyncio

from app.shared.common import get_assignment_room, utc_now



logger  = logging.getLogger(__name__)
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


async def get_driver_by_user_id(session: AsyncSession, user_id: UUID) -> DriverRead:
    result = await session.exec(select(Driver).where(Driver.user_id == user_id).options(selectinload(Driver.user)))
    driver = result.one_or_none()
    # if not driver:
    #     raise create_404("Driver not found for this user")
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


# Create Assignment for driver 
async def create_assignment(session: AsyncSession, order_id: UUID,role:DARole,driver_id:UUID )-> DriverAssignment:
    select_asssignment_statement= select(DriverAssignment).where(DriverAssignment.order_id==order_id,DriverAssignment.role==role)
    ass_res = await session.exec(select_asssignment_statement)

    assignment = ass_res.one_or_none()

    if assignment is not None: 
            logger.info(f"Assignment already exists for order {order_id} and role {role}")
            return assignment
    

    logger.info(f"Creating assignment for order {order_id} and role {role}")
    order_statement= select(Order).where(Order.id==order_id);
    order_res = await session.exec(order_statement);
    order= order_res.one_or_none();
    if order is None:
            raise Exception("Order not found")
    
    assignment= DriverAssignment(
        order_id=order.id,
        role=role,
        driver_id=driver_id
    )
    session.add(assignment)
    await session.commit()
    await session.refresh(assignment)
    return assignment

async def get_assigned_order(session:AsyncSession, current_user:UUID)->ActiveAssignmentResponse:
    driver= await get_driver_by_user_id(session,current_user)
    statement = assignment_detail_query_builder().where(DriverAssignment.driver_id==driver.id,DriverAssignment.status==None)

    ass_res = await session.exec(statement)

    res= ass_res.one_or_none()

    if res is None:
        raise create_404("Assigned package is not found")

    time_remaining= calulate_remaining_time(assigned_time=res.assigned_at,expired_in_sec=60)
    logger.info(f"assigned order time remaining is {time_remaining}")
    active_ass= ActiveAssignmentResponse(assignment=res,timeout=time_remaining)
    return active_ass



async def list_assignments(
    session: AsyncSession,
    *,
    driver_id: UUID | None = None,
    order_id: UUID | None = None,
    role: DARole | None = None,
    status: DAStatus | None = None,
    status_not_in: list[DAStatus]=[],
    page: int = 1,
    size: int = 10,
    # user_id: uuid.UUID
) -> Page[DriverAssignmentRead]:
    

    # driver_statement=select(Driver).where(Driver.user_id==user_id)
    # driver_res= await session.exec(driver_statement)
    # driver = driver_res.one_or_none()
    # if driver is None:
    #     driver_id=driver.id
    
    offset = (page - 1) * size
    statement = select(DriverAssignment).offset(offset).limit(size).order_by(DriverAssignment.created_at.desc()).options(selectinload(DriverAssignment.order).selectinload(Order.items),
                                                                                                                         selectinload(DriverAssignment.order).selectinload(Order.customer),
                                                                                                                         selectinload(DriverAssignment.order).selectinload(Order.business),
                                                                                                                         selectinload(DriverAssignment.payment))
    count_statement = select(func.count(DriverAssignment.id))
    logger.info(f"status not in {status_not_in} and {len(status_not_in)}")
    if len(status_not_in)>0:
        statement = statement.where(DriverAssignment.status.notin_(status_not_in))
        count_statement = count_statement.where(DriverAssignment.status.notin_(status_not_in))
    if driver_id is not None:
        statement = statement.where(DriverAssignment.driver_id == driver_id)
        count_statement = count_statement.where(DriverAssignment.driver_id == driver_id)
    if order_id is not None:
        statement = statement.where(DriverAssignment.order_id == order_id)
        count_statement = count_statement.where(DriverAssignment.order_id == order_id)
    if role is not None:
        statement = statement.where(DriverAssignment.role == role)
        count_statement = count_statement.where(DriverAssignment.role == role)
    if status is not None:
        statement = statement.where(DriverAssignment.status == status)
        count_statement = count_statement.where(DriverAssignment.status == status)

    total = (await session.exec(count_statement)).one()
    assignments = (await session.exec(statement)).all()
    return Page[DriverAssignmentRead](
        items=assignments,
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size,
    )

async def create_assignment_history(session: AsyncSession, driver_id: UUID,order_id: UUID,assignment_id:UUID,role:DARole,reason: str=None) -> DriverAssignmentHistory:

    logger.info(f"calling to create assignment history with order id {order_id} driver id {driver_id} assignment id {assignment_id} role {role} reason {reason}")
    his_assignment = DriverAssignmentHistory(
        driver_id=driver_id,
        order_id=order_id,
        assignment_id=assignment_id,
        role=role,
        reason=reason
    )

    session.add(his_assignment)
    await session.commit()
    session.refresh(his_assignment)

    return his_assignment


async def get_assignment(session: AsyncSession,assignment_id)-> DriverAssignment:
    ass_statement= select(DriverAssignment).where(DriverAssignment.id==assignment_id)

    ass_res = await session.exec(ass_statement)
    assignment= ass_res.one_or_none()
    return assignment

async def get_assignment_with_details(session: AsyncSession,assignment_id)-> DriverAssignment:
    ass_statement= select(DriverAssignment).where(DriverAssignment.id==assignment_id).options(selectinload(DriverAssignment.order).selectinload(Order.items))

    ass_res = await session.exec(ass_statement)
    assignment= ass_res.first()

    logger.info(f"Retrieved assignment with details: {assignment}")
    return assignment



async def get_assignment_with_details_v2(session: AsyncSession,assignment_id)-> DriverAssignment:
    ass_statement= select(DriverAssignment).where(DriverAssignment.id==assignment_id).options(selectinload(DriverAssignment.order).selectinload(Order.items),
                                                                                              selectinload(DriverAssignment.order).selectinload(Order.business),
                                                                                              selectinload(DriverAssignment.order).selectinload(Order.customer).selectinload(User.driver),
                                                                                              selectinload(DriverAssignment.payment))

    ass_res = await session.exec(ass_statement)
    assignment= ass_res.first()

    logger.info(f"Retrieved assignment with details: {assignment}")
    return assignment



async def get_assignment_by_order_role(order_id: uuid.UUID, role: DARole, session: AsyncSession) -> DriverAssignment:
    statement= select(DriverAssignment).where(DriverAssignment.order_id==order_id, DriverAssignment.role==role)
    result = await session.exec(statement)
    return result.one_or_none()

def assignment_detail_query_builder():
    return (select(DriverAssignment).options(selectinload(DriverAssignment.order).selectinload(Order.items),
                                                                                              selectinload(DriverAssignment.order).selectinload(Order.business),
                                                                                              selectinload(DriverAssignment.order).selectinload(Order.customer).selectinload(User.driver),
                                                                                              selectinload(DriverAssignment.payment)))
async def get_assignment_by_id(session: AsyncSession, assignment_id: UUID) -> DriverAssignmentRead:
    assignment = await get_assignment_with_details_v2(session=session, assignment_id=assignment_id)
    if assignment is None:
        raise create_404("Driver assignment not found")
    return assignment


async def create_assignment_api(session: AsyncSession, data: DriverAssignmentCreate) -> DriverAssignmentRead:
    driver = await session.get(Driver, data.driver_id)
    if driver is None:
        raise create_404("Driver not found")
    if driver.driver_status != DriverStatus.ONLINE:
        raise create_400("Driver must be ONLINE before assignment")

    assignment = await create_assignment(
        session=session,
        order_id=data.order_id,
        role=data.role,
        driver_id=data.driver_id,
    )
    return assignment

async def get_driver_active_assignment(session: AsyncSession, driver_id: UUID) -> DriverAssignmentRead | None:
    statement = select(DriverAssignment).where(
        DriverAssignment.driver_id == driver_id,
        DriverAssignment.status == DAStatus.ACCEPTED,
    ).options(selectinload(DriverAssignment.order).selectinload(Order.items))
    result = await session.exec(statement)
    assignment = result.one_or_none()
    return assignment



# When Driver called accept assignment api, the order status will be updated to PICKUP_ASSIGNED if current order status is PENDING; if current order status is READY_FOR_DELIVERY, the order status will be updated to DELIVERY_ASSIGNED
async def accept_assignment_api(session: AsyncSession, assignment_id: UUID,user_id: UUID) -> DriverAssignmentRead:

    logger.info(f"called assignment accept api {assignment_id}")
    driver = await get_driver_by_user_id(session=session, user_id=user_id) # check if driver exist for this user id
    if driver is None:
        raise create_404("Driver not found for this user")
    
    # Validate if driver has active assignment or not, if has active assignment then cannot accept new assignment until the current assignment is completed
    current_assignment = await get_driver_active_assignment(session=session, driver_id=driver.id)
    if current_assignment is not None:
        raise create_400("Driver already has an active assignment")
    

    assignment = await get_assignment(session=session, assignment_id=assignment_id)
    if assignment is None:
        raise create_404("Driver assignment not found")
    if assignment.driver_id != driver.id:
        raise create_400("This assignment does not belong to the driver")
    order= await get_order_by_id(order_id=assignment.order_id,session=session)

    order_status=OrderStatus.PICKUP_ASSIGNED

    if order.status==OrderStatus.READY_FOR_DELIVERY:
        order_status=OrderStatus.DELIVERY_ASSIGNED

    if order.status==OrderStatus.DELIVERY_ASSIGNED:
        order_status=OrderStatus.OUT_FOR_DELIVERY

    order = await update_order_status(session=session, order_id=assignment.order_id,data=OrderStatusUpdate(status=order_status))
    
    logger.info(f"Updated order status to PICKUP_ASSIGNED for order {order.id} when accepting assignment {assignment_id}")

    assignment = await update_assignment_status_with_fee(
        session=session,
        assignment_id=assignment_id,
        data=DriverAssignmentStatusUpdate(status=DAStatus.ACCEPTED),
        cost=order.delivery_fee,
    )

    if order_status == OrderStatus.PICKUP_ASSIGNED:
        # Pickup: payment amount is pickup fee only
        payment = await get_pending_payment_by_order_id(assignment.order_id, session)
        if payment is not None:
            await update_payment_for_pickup(payment.id, ass_id=assignment.id, amount=order.pickup_fee, session=session)
    else:
        delivery_fee_amount = decimal.Decimal(str(order.delivery_fee if order.delivery_fee else order.pickup_fee))
        await create_delivery_payment(
            order_id=assignment.order_id,
            assignment_id=assignment_id,
            amount=delivery_fee_amount,
            payment_type=PaymentType.DELIVERY_FEE,
            session=session,
        )
        await create_delivery_payment(
            order_id=assignment.order_id,
            assignment_id=assignment_id,
            amount=decimal.Decimal(str(order.subtotal)),
            payment_type=PaymentType.WASHING_SERVICE_FEE,
            session=session,
        )

    assignment = await get_assignment_with_details_v2(session=session, assignment_id=assignment_id)
    print(f"accept assignment api with assignment data {assignment}")
    data = DriverAssignmentRead.model_validate(assignment).model_dump(mode="json")

    print(f"accept assignment api with assignment data {data}")
    
    return data

# when pickup order status is update to OrderStatus.PICKED_UP and assignment is PICKED_UP
async def pickup_assignment_api(
    session: AsyncSession,
    assignment_id: UUID,
    user_id: UUID = None,
    delivery_fee_paid_by: DeliveryFeePaidBy | None = None,
) -> DriverAssignmentRead:
    assignment = await get_assignment(session=session, assignment_id=assignment_id)

    if assignment is None:
        raise create_404("Assignment is not found")

    return await update_assignment_status_api(
        session=session,
        assignment_id=assignment_id,
        status=DAStatus.PICKED_UP,
        current_user=user_id,
        delivery_fee_paid_by=delivery_fee_paid_by,
    )

# when pickup order status is update to OrderStatus.DELIVERED_TO_SHOP and assignment is DELIVERED
def resolve_assignment_order_status(current_status: OrderStatus, assignment_status: DAStatus) -> OrderStatus:
    if assignment_status == DAStatus.PICKED_UP:
        if current_status == OrderStatus.PICKUP_ASSIGNED:
            return OrderStatus.PICKED_UP
        if current_status == OrderStatus.DELIVERY_ASSIGNED:
            return OrderStatus.OUT_FOR_DELIVERY
        if current_status == OrderStatus.OUT_FOR_DELIVERY:
            return OrderStatus.PICKED_UP_DELIVERY
    if assignment_status == DAStatus.DELIVERED:
        if current_status == OrderStatus.PICKED_UP:
            return OrderStatus.DELIVERED_TO_SHOP
        if current_status == OrderStatus.OUT_FOR_DELIVERY or current_status == OrderStatus.PICKED_UP_DELIVERY:
            return OrderStatus.DELIVERED

    raise create_400(
        f"Assignment status {assignment_status.value} is not allowed when order status is {current_status.value}"
    )


async def update_assignment_status_api(
    session: AsyncSession,
    assignment_id: UUID,
    status: DAStatus,
    current_user: UUID = None,
    delivery_fee_paid_by: DeliveryFeePaidBy | None = None,
) -> DriverAssignmentRead:

    assignment = await get_assignment_with_details_v2(session=session, assignment_id=assignment_id)
    logger.info(f"call for deliver assignment {assignment}")
    if assignment is None:
        raise create_404("Assignment is not found")

    next_order_status = resolve_assignment_order_status(assignment.order.status, status)
    order_status_data = OrderStatusUpdate(status=next_order_status)
    if status == DAStatus.PICKED_UP:
        order_status_data.delivery_fee_paid_by = delivery_fee_paid_by
        is_delivery_leg = next_order_status == OrderStatus.OUT_FOR_DELIVERY
        fee_amount = decimal.Decimal(str(
            assignment.order.delivery_fee if is_delivery_leg else assignment.order.pickup_fee
        ))
        payment_type = PaymentType.DELIVERY_FEE if is_delivery_leg else PaymentType.PICKUP_FEE
        if delivery_fee_paid_by == DeliveryFeePaidBy.SHOP:
            await create_pending_settlement_payment(
                order_id=assignment.order_id,
                assignment_id=assignment_id,
                amount=fee_amount,
                payment_type=payment_type,
                session=session,
            )
            assignment.order.has_advance_settlement = True
            assignment.order.updated_at = utc_now()
            session.add(assignment.order)
            await session.commit()
        else:
            await create_delivery_payment(
                order_id=assignment.order_id,
                assignment_id=assignment_id,
                amount=fee_amount,
                payment_type=payment_type,
                status=PaymentStatus.COLLECTED,
                session=session,
            )

    if next_order_status == OrderStatus.DELIVERED_TO_SHOP:
        await settle_shop_advance_payment(
            order_id=assignment.order_id,
            assignment_id=assignment_id,
            payment_type=PaymentType.PICKUP_FEE,
            session=session,
        )

    if next_order_status == OrderStatus.DELIVERED:
        await collect_assignment_payments(assignment_id=assignment_id, session=session)

    order = await update_order_status_api(
        session=session,
        order_id=assignment.order_id,
        data=order_status_data,
        current_user_id=current_user,
    )
    logger.info(f"Order after updated {order}")
    assignment = await update_assignment_status(
        session=session,
        assignment_id=assignment_id,
        data=DriverAssignmentStatusUpdate(status=status),
    )
    data = DriverAssignmentRead.model_validate(assignment).model_dump(mode="json")
    return data
# when pickup order status is update to OrderStatus.DELIVERED_TO_SHOP and assignment is DELIVERED
async def deliver_assignment_api(session: AsyncSession, assignment_id: UUID,current_user: UUID=None)->DriverAssignmentRead:
    return await update_assignment_status_api(
        session=session,
        assignment_id=assignment_id,
        status=DAStatus.DELIVERED,
        current_user=current_user,
    )

async def _apply_assignment_status(
    session: AsyncSession,
    assignment: DriverAssignment,
    status: DAStatus,
) -> None:
    assignment.status = status
    session.add(assignment)

    # Update driver status based on assignment status 
    driver = await session.get(Driver, assignment.driver_id)
    if driver is not None:
        if status in (DAStatus.ACCEPTED, DAStatus.PICKED_UP):
            driver.driver_status = DriverStatus.BUSY
        elif status in (DAStatus.DELIVERED, DAStatus.REJECTED):
            driver.driver_status = DriverStatus.ONLINE
        session.add(driver)

async def update_assignment_status(
    session: AsyncSession,
    assignment_id: UUID,
    data: DriverAssignmentStatusUpdate,
) -> DriverAssignmentRead:
    assignment = await get_assignment_with_details(session=session, assignment_id=assignment_id)
    if assignment is None:
        raise create_404("Driver assignment not found")
    logger.info(f"Updated assignment status for assignment {assignment.order}")
    assignment.status = data.status
    session.add(assignment)
    await _apply_assignment_status(session=session,assignment=assignment,status=data.status)

    await session.commit()

    assignment = await get_assignment_with_details_v2(session=session, assignment_id=assignment_id)
    return assignment


async def update_assignment_status_with_fee(
    session: AsyncSession,
    assignment_id: UUID,
    data: DriverAssignmentStatusUpdate,
    cost: decimal.Decimal
) -> DriverAssignmentRead:
    assignment = await get_assignment_with_details(session=session, assignment_id=assignment_id)
    if assignment is None:
        raise create_404("Driver assignment not found")
    logger.info(f"Updated assignment status for assignment {assignment.order}")
    assignment.status = data.status
    assignment.cost=cost

    # update driver assignment status 
    await _apply_assignment_status(session=session,assignment=assignment,status=data.status)

    await session.commit()
    assignment = await get_assignment_with_details_v2(session=session, assignment_id=assignment_id)
    return assignment

async def unset_driver_assignment(session: AsyncSession,assignment_id:UUID):
    assignment = await get_assignment(session=session,assignment_id=assignment_id)
    if assignment is None:
        raise create_404("Driver assignment not found")
    assignment.driver_id=None
    session.add(assignment)
    await session.commit()
    await session.refresh(assignment)
    return assignment

async def update_timout_history(session: AsyncSession,assignment_id:UUID,driver_id:UUID)-> DriverAssignmentHistory:
        his_statement= select(DriverAssignmentHistory).where(DriverAssignmentHistory.assignment_id==assignment_id,
                                                             DriverAssignmentHistory.driver_id==driver_id)
        his_res = await session.exec(his_statement)
        his= his_res.one_or_none()
        if his is None:
            logging.info("creating order history")
            assignment= await get_assignment(session=session,assignment_id=assignment_id)
            his= DriverAssignmentHistory(
                assignment_id=assignment_id,
                driver_id=driver_id,
                reason="TIMEOUT",
                order_id=assignment.order_id
            )

        his.reason="TIMEOUT"
        session.add(his)
        await session.commit()
        await session.refresh(his)
        return his


def _fallback_order_status(role: DARole) -> OrderStatus:
    return OrderStatus.PENDING if role == DARole.PICKUP else OrderStatus.READY_FOR_DELIVERY


async def _revert_order_to_fallback(session: AsyncSession, order_id: UUID, role: DARole) -> None:
    order_statement = select(Order).where(Order.id == order_id)
    order_res = await session.exec(order_statement)
    order = order_res.one_or_none()
    if order is None:
        return
    fallback = _fallback_order_status(role)
    logger.warning("No available drivers for order %s (%s), reverting to %s", order_id, role.value, fallback.value)
    order.status = fallback
    order.updated_at = utc_now()
    session.add(order)
    await session.commit()


# Auto assign to two types of delivery: PICKUP and DELIVERY
async def auto_assign_driver(session: AsyncSession, type: DARole,order_id:UUID) -> None:

    order_statement= select(Order).where(Order.id==order_id);
    order_res = await session.exec(order_statement);
    order= order_res.one_or_none();
    if order is None:
            raise Exception("Order not found")

    driver_statement=select(Driver).where(Driver.driver_status==DriverStatus.ONLINE)
    driver_res= await session.exec(driver_statement)
    drivers = driver_res.fetchall()
    logger.info(f"Fetching all drivers: {drivers}")
    if len(drivers)==0:
        await _revert_order_to_fallback(session=session, order_id=order_id, role=type)
        return

    if type == DARole.DELIVERY and order.status != OrderStatus.DELIVERY_ASSIGNED:
        await update_order_status(session=session, order_id=order_id, data=OrderStatusUpdate(status=OrderStatus.DELIVERY_ASSIGNED))

    # Create assignment if not exist, if exist then update driver assignment to new driver and update assignment history
    assignment= await get_assignment_by_order_role(order_id=order_id, role=type, session=session)
    logger.info(f"Existing assignment for order {order_id} and role {type}: {assignment}")
    if assignment is None:
        assignment= await create_assignment(session=session,order_id=order.id,role=type,driver_id=drivers[0].id)
    else: 
            assignment.driver_id=drivers[0].id
            assignment.assigned_at=utc_now()
            session.add(assignment)
            await session.commit()
            await session.refresh(assignment)
    await set_timeout_assign_driver(session=session,assignment_id=assignment.id)


async def set_timeout_assign_driver(session: AsyncSession,assignment_id: UUID):
    

    # Select driver assignment history to get list of driver that already assigned for this order and role, then exclude those driver in the next auto assignment
    his_ass_statement= select(DriverAssignmentHistory).where(DriverAssignmentHistory.assignment_id==assignment_id)

    his_res = await session.exec(his_ass_statement)
    histories= his_res.fetchall()
    # list drivers that are used to sent
    prev_driver_ids=[d.driver_id for d in histories if d.driver_id is not None ]

    driver_statement=select(Driver).where(Driver.driver_status==DriverStatus.ONLINE, Driver.id.notin_(prev_driver_ids))
    driver_res= await session.exec(driver_statement)
    drivers = driver_res.fetchall()
    logger.info(f"Fetching all drivers: {drivers}")
    if len(drivers) == 0:
        assignment = await get_assignment_with_details_v2(session=session, assignment_id=assignment_id)
        if assignment is not None:
            await _revert_order_to_fallback(session=session, order_id=assignment.order_id, role=assignment.role)
        return
    assignment = await get_assignment_with_details_v2(session=session,assignment_id=assignment_id)


    logger.info(f"Retrieved assignment with details: {assignment}")
    await create_assignment_history(session=session,driver_id=drivers[0].id,role= assignment.role,order_id=assignment.order_id,assignment_id=assignment.id)

    # Get customer and to be refactor later
    customer_statement= select(User).where(User.id==assignment.order.customer_id)
    customer_res =await session.exec(customer_statement)
    customer = customer_res.one_or_none()

    # Get Shop and to be refactor later
    shop_statement= select(LaundryBusiness).where(LaundryBusiness.id==assignment.order.business_id)
    shop_res =await session.exec(shop_statement)
    shop = shop_res.one_or_none()
    remaining_time = calulate_remaining_time(assigned_time=assignment.assigned_at,expired_in_sec=60)
    # Broadcast Websocket to driver

    order_data =OrderReadV2.model_validate(assignment.order).model_dump(mode="json")
    
    await connection_manager.send_json(
        room=get_assignment_room(str(drivers[0].id)),
        payload={"role": assignment.role, 
                 "id": str(assignment_id),
                 "order":order_data,
                "timeout":remaining_time
                 },
    )

    device_statement= select(DeviceToken).where(DeviceToken.driver_id==drivers[0].id)
    device_res = await session.exec(device_statement)
    device_tokens= device_res.fetchall()

    logger.info(f"Sending push notification to driver {drivers[0].id} with device tokens: {device_tokens}")
    for device in device_tokens:
        send_firebase_message(token=device.token,title="New Assignment",body=f"You have a new {assignment.role.value} assignment",data={"assignment_id": str(assignment_id)})

    # await 
    await asyncio.create_task(assignment_timeout(assignment_id))


# handle when driver dont accept assignment
async  def assignment_timeout(assignment_id: UUID,):
    try:
        async with get_session_context() as session:
            await asyncio.sleep(60) # wait for 1 minute before checking if the assignment is accepted or not
            logger.info("called assigned")
            assignment = await get_assignment(session,assignment_id)
            logger.info(f"Driver assigment: {assignment}")
            logger.info(f"Fetched assignment for timeout check: {assignment.status}")
            if assignment.status not in [DAStatus.ACCEPTED,DAStatus.PICKED_UP,DAStatus.DELIVERED]:
                logger.info(f"No driver pickup assignment {assignment_id}")
                # reassign next driver
                await update_timout_history(session=session,assignment_id=assignment_id,driver_id=assignment.driver_id)
                # logger.info(f"Assignment {assignment_id} timed out, unsetting driver assignment")
                logger.info(f"Assignment {assignment.driver_id} timed out, unsetting driver assignment")
                await connection_manager.send_json(
                    room=get_assignment_room(str(assignment.driver_id)),
                    payload={"role": "CANCELLED", 
                            "assignment_id": str(assignment_id)
                            },
                )
                await unset_driver_assignment(session=session,assignment_id=assignment_id)
                await set_timeout_assign_driver(session,assignment_id)
                
                # update_order_statement = 
                logger.info("Assignment timed out, reassigning...")
    except asyncio.CancelledError:
        raise
    except Exception as e:
        logger.error(f"Error in assignment timeout handling: {e}", exc_info=True)

    
