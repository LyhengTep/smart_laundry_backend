from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Body, Depends, Query
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.reponse_model import Page
from app.db.engine import get_session
from app.lib.security import get_current_user
from app.modules.drivers.models import DARole, DAStatus
from app.modules.drivers.schema import (
    ActiveAssignmentResponse,
    DriverAssignmentCreate,
    DriverAssignmentRead,
    DriverAssignmentStatusUpdate,
    DriverRead,
    DriverWrite,
    PickupStatusUpdate,
)
from app.modules.drivers import service as svc
from app.modules.payments import service as payment_svc
from app.modules.payments.schema import DriverRevenueRead
from app.modules.users.models import UserStatus
from app.modules.users.schema import UserRead, UserWrite

router = APIRouter(prefix="/drivers", tags=["drivers"])

@router.get("/", response_model=Page[DriverRead])
async def list_drivers(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    status: Optional[UserStatus] = Query(None),
    user_name: Optional[str] = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> Page[DriverRead]:
    return await svc.list_drivers(session, page, size, status=status, user_name=user_name)


@router.get("/assignments/", response_model=Page[DriverAssignmentRead])
async def list_assignments(
    driver_id: UUID | None = Query(default=None),
    order_id: UUID | None = Query(default=None),
    role: DARole | None = Query(default=None),
    status: DAStatus | None = Query(default=None),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    status_not_in: list[DAStatus]|None=Query(default=[]),
    # current_user: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Page[DriverAssignmentRead]:
    
    print(f"status not in is {status_not_in}")
    return await svc.list_assignments(
        session=session,
        driver_id=driver_id,
        order_id=order_id,
        role=role,
        status=status,
        page=page,
        size=size,
        status_not_in=status_not_in
    )


@router.get("/assignments/{assignment_id}", response_model=DriverAssignmentRead)
async def get_assignment(assignment_id: UUID, session: AsyncSession = Depends(get_session)) -> DriverAssignmentRead:
    return await svc.get_assignment_by_id(session=session, assignment_id=assignment_id)


@router.post("/assignments/", response_model=DriverAssignmentRead)
async def create_assignment(
    data: DriverAssignmentCreate,
    session: AsyncSession = Depends(get_session),
) -> DriverAssignmentRead:
    return await svc.create_assignment_api(session=session, data=data)


@router.patch("/assignments/{assignment_id}/accept", response_model=DriverAssignmentRead)
async def accept_assignment(
    assignment_id: UUID,
    current_user: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> DriverAssignmentRead:
    return await svc.accept_assignment_api(
        session=session,
        assignment_id=assignment_id,
        user_id=UUID(current_user),
    )


@router.patch("/assignments/{assignment_id}/reject", response_model=DriverAssignmentRead)
async def reject_assignment(
    assignment_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> DriverAssignmentRead:
    return await svc.update_assignment_status(
        session=session,
        assignment_id=assignment_id,
        data=DriverAssignmentStatusUpdate(status=DAStatus.REJECTED),
    )

@router.patch("/assignments/{assignment_id}/picked-up", response_model=DriverAssignmentRead)
async def picked_up_assignment(
    assignment_id: UUID,
    data: PickupStatusUpdate = Body(default=PickupStatusUpdate()),
    session: AsyncSession = Depends(get_session),
    current_user: str = Depends(get_current_user),
) -> DriverAssignmentRead:
    return await svc.update_assignment_status_api(
        session=session,
        assignment_id=assignment_id,
        current_user=UUID(current_user),
        status=DAStatus.PICKED_UP,
        delivery_fee_paid_by=data.delivery_fee_paid_by,
    )


@router.patch("/assignments/{assignment_id}/delivered", response_model=DriverAssignmentRead)
async def delivered_assignment(
    assignment_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: str = Depends(get_current_user),
) -> DriverAssignmentRead:
    return await svc.update_assignment_status_api(
        session=session,
        assignment_id=assignment_id,
        current_user=UUID(current_user),
        status=DAStatus.DELIVERED,
    )

@router.get("/by-user/{user_id}", response_model=DriverRead)
async def get_driver_by_user_id(user_id: UUID, session: AsyncSession = Depends(get_session)) -> DriverRead:
    return await svc.get_driver_by_user_id(session=session, user_id=user_id)

@router.get("/{driver_id}",response_model=DriverRead)
async def list_one_driver(driver_id: UUID,session: AsyncSession = Depends(get_session))->DriverRead:
    return await svc.list_one_driver(session,driver_id)

@router.put("/{driver_id}",response_model=DriverRead)
async def edit_driver(driver_id: UUID, data: DriverWrite, session: AsyncSession = Depends(get_session))->DriverRead:
    return await svc.edit_driver(session,driver_id,data)

@router.patch("/{driver_id}/approve",response_model=DriverRead)
async def approve_driver(driver_id: UUID,session: AsyncSession = Depends(get_session))->DriverRead:
    return await svc.approve_driver(session,driver_id)


@router.patch("/{driver_id}/reject",response_model=DriverRead)
async def reject_driver(driver_id: UUID,session: AsyncSession = Depends(get_session))->DriverRead:
    return await svc.reject_driver(session,driver_id)


@router.patch("/{driver_id}/suspend",response_model=DriverRead)
async def suspend_driver(driver_id: UUID,session: AsyncSession = Depends(get_session))->DriverRead:
    return await svc.suspend_driver(session,driver_id)


@router.get("/me/revenue", response_model=DriverRevenueRead)
async def get_my_revenue(
    session: AsyncSession = Depends(get_session),
    current_user: str = Depends(get_current_user),
) -> DriverRevenueRead:
    driver = await svc.get_driver_by_user_id(session=session, user_id=current_user)
    if driver is None:
        from app.exceptions.http import create_404
        raise create_404("Driver not found for this user")
    return await payment_svc.get_driver_revenue(driver_id=driver.id, session=session)


@router.get("/pending/get-current-assignment",response_model=ActiveAssignmentResponse)
async def get_assigned_order(session: AsyncSession = Depends(get_session), current_user: str = Depends(get_current_user))->ActiveAssignmentResponse:
    print("called get assigned order")
    return await svc.get_assigned_order(session,current_user)


# @router.get("/{user_id}")
# async def list_one_user(user_id: UUID,session: AsyncSession = Depends(get_session))->UserRead:
#     return await svc.list_one_user(user_id,session)


# @router.post("/")
# async def create_users(data:UserWrite,session: AsyncSession = Depends(get_session))-> UserRead:
#     return await svc.create_user(data=data,session=session)


# @router.delete("/{user_id}")
# async def delete_user(user_id: UUID,session: AsyncSession = Depends(get_session))->bool: 
#     return await svc.delete_user(user_id,session)
