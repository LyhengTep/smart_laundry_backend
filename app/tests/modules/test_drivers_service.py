from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

from app.modules.drivers import service as driver_service
from app.modules.drivers.models import DAStatus, DARole, Driver, DriverAssignment, DriverAssignmentHistory, DriverStatus
from app.modules.drivers.schema import DriverAssignmentCreate, DriverAssignmentStatusUpdate, DriverWrite
from app.modules.orders.models import OrderStatus
from app.modules.users.models import RoleName, User, UserStatus
from app.modules.users.schema import UserEdit
from app.tests.modules.conftest import FakeAsyncSession, run_async


def build_driver() -> Driver:
    now = datetime.now(timezone.utc)
    user = User(
        id=uuid4(),
        full_name="Driver User",
        user_name="driver",
        email="driver@example.com",
        phone=None,
        password_hash="hashed",
        role=RoleName.DRIVER,
        status=UserStatus.INACTIVE,
        created_at=now,
        updated_at=now,
    )
    return Driver(
        id=uuid4(),
        user_id=user.id,
        plate_number="ABC123",
        id_card_number="ID123",
        vehicle_type="Bike",
        driver_status=DriverStatus.ONLINE,
        license_number=None,
        vehicle_color="Red",
        user=user,
    )


def build_assignment(driver_id: UUID | None = None) -> DriverAssignment:
    now = datetime.now(timezone.utc)
    return DriverAssignment(
        id=uuid4(),
        driver_id=driver_id or uuid4(),
        order_id=uuid4(),
        role=DARole.PICKUP,
        status=None,
        assignedAt=now,
        deliveryAt=None,
        created_at=now,
        updated_at=now,
    )


def test_approve_driver_sets_user_active() -> None:
    driver = build_driver()
    session = FakeAsyncSession(exec_results=[driver])

    result = run_async(driver_service.approve_driver(session, str(driver.id)))

    assert result.user.status == UserStatus.ACTIVE
    assert session.commits == 1


def test_get_driver_by_user_id_returns_driver() -> None:
    driver = build_driver()
    session = FakeAsyncSession(exec_results=[driver])

    result = run_async(driver_service.get_driver_by_user_id(session, driver.user_id))

    assert result.id == driver.id
    assert result.user_id == driver.user_id


def test_create_assignment_api_creates_assignment_for_online_driver(monkeypatch: pytest.MonkeyPatch) -> None:
    driver = build_driver()
    assignment = build_assignment(driver_id=driver.id)
    session = FakeAsyncSession(get_results=[driver])
    websocket_events: list[tuple[str, dict]] = []

    async def fake_create_assignment(**kwargs):
        return assignment

    async def fake_send_json(room: str, payload: dict) -> None:
        websocket_events.append((room, payload))

    monkeypatch.setattr(driver_service, "create_assignment", fake_create_assignment)
    monkeypatch.setattr(driver_service.connection_manager, "send_json", fake_send_json)

    result = run_async(
        driver_service.create_assignment_api(
            session=session,
            data=DriverAssignmentCreate(driver_id=driver.id, order_id=assignment.order_id, role=DARole.PICKUP),
        )
    )

    assert result.id == assignment.id
    assert websocket_events[0][0] == f"assignment:{driver.id}"
    assert websocket_events[0][1]["event"] == "driver_assignment_created"


def test_update_assignment_status_accepts_and_sets_driver_busy(monkeypatch: pytest.MonkeyPatch) -> None:
    driver = build_driver()
    assignment = build_assignment(driver_id=driver.id)
    session = FakeAsyncSession(exec_results=[assignment], get_results=[driver])
    websocket_events: list[dict] = []

    async def fake_send_json(_room: str, payload: dict) -> None:
        websocket_events.append(payload)

    monkeypatch.setattr(driver_service.connection_manager, "send_json", fake_send_json)

    result = run_async(
        driver_service.update_assignment_status(
            session=session,
            assignment_id=assignment.id,
            data=DriverAssignmentStatusUpdate(status=DAStatus.ACCEPTED),
        )
    )

    assert result.status == DAStatus.ACCEPTED
    assert driver.driver_status == DriverStatus.BUSY
    assert session.commits == 1
    assert websocket_events[0]["status"] == DAStatus.ACCEPTED.value


def test_update_assignment_status_picked_up_keeps_driver_busy(monkeypatch: pytest.MonkeyPatch) -> None:
    driver = build_driver()
    assignment = build_assignment(driver_id=driver.id)
    session = FakeAsyncSession(exec_results=[assignment], get_results=[driver])

    async def fake_send_json(_room: str, _payload: dict) -> None:
        return None

    monkeypatch.setattr(driver_service.connection_manager, "send_json", fake_send_json)

    result = run_async(
        driver_service.update_assignment_status(
            session=session,
            assignment_id=assignment.id,
            data=DriverAssignmentStatusUpdate(status=DAStatus.PICKED_UP),
        )
    )

    assert result.status == DAStatus.PICKED_UP
    assert driver.driver_status == DriverStatus.BUSY


def test_update_assignment_status_delivered_sets_driver_online(monkeypatch: pytest.MonkeyPatch) -> None:
    driver = build_driver()
    driver.driver_status = DriverStatus.BUSY
    assignment = build_assignment(driver_id=driver.id)
    session = FakeAsyncSession(exec_results=[assignment], get_results=[driver])

    async def fake_send_json(_room: str, _payload: dict) -> None:
        return None

    monkeypatch.setattr(driver_service.connection_manager, "send_json", fake_send_json)

    result = run_async(
        driver_service.update_assignment_status(
            session=session,
            assignment_id=assignment.id,
            data=DriverAssignmentStatusUpdate(status=DAStatus.DELIVERED),
        )
    )

    assert result.status == DAStatus.DELIVERED
    assert driver.driver_status == DriverStatus.ONLINE


def test_update_assignment_status_rejects_missing_assignment() -> None:
    session = FakeAsyncSession(exec_results=[None])

    with pytest.raises(HTTPException) as exc:
        run_async(
            driver_service.update_assignment_status(
                session=session,
                assignment_id=uuid4(),
                data=DriverAssignmentStatusUpdate(status=DAStatus.REJECTED),
            )
        )

    assert exc.value.status_code == 404


def test_resolve_assignment_order_status_for_picked_up() -> None:
    assert (
        driver_service.resolve_assignment_order_status(OrderStatus.PICKUP_ASSIGNED, DAStatus.PICKED_UP)
        == OrderStatus.PICKED_UP
    )
    assert (
        driver_service.resolve_assignment_order_status(OrderStatus.DELIVERY_ASSIGNED, DAStatus.PICKED_UP)
        == OrderStatus.OUT_FOR_DELIVERY
    )


def test_resolve_assignment_order_status_for_delivered() -> None:
    assert (
        driver_service.resolve_assignment_order_status(OrderStatus.PICKED_UP, DAStatus.DELIVERED)
        == OrderStatus.DELIVERED_TO_SHOP
    )
    assert (
        driver_service.resolve_assignment_order_status(OrderStatus.OUT_FOR_DELIVERY, DAStatus.DELIVERED)
        == OrderStatus.DELIVERED
    )



def test_update_timout_history()-> None:
    driver_history = DriverAssignmentHistory(
        driver_id=uuid4(),
        order_id=uuid4(),
        assignment_id=uuid4(),
    )
    session= FakeAsyncSession(exec_results=[driver_history])

    result = run_async(driver_service.update_timout_history(session=session,assignment_id=str(driver_history.assignment_id),driver_id=(driver_history.driver_id)))

    assert result.driver_id == driver_history.driver_id
    assert result.assignment_id == driver_history.assignment_id
    assert result.reason == "TIMEOUT"
    assert len(session.added) == 1
    assert session.commits == 1
   


def test_list_one_driver_raises_not_found() -> None:
    session = FakeAsyncSession(exec_results=[None])

    with pytest.raises(HTTPException) as exc:
        run_async(driver_service.list_one_driver(session, str(uuid4())))

    assert exc.value.status_code == 404


def test_edit_driver_updates_driver_and_user_fields() -> None:
    driver = build_driver()
    session = FakeAsyncSession(exec_results=[driver])
    data = DriverWrite(
        plate_number="NEW123",
        id_card_number="NEWID",
        vehicle_type="Car",
        license_number="LIC123",
        vehicle_color="Blue",
        user=UserEdit(
            full_name="Updated Driver",
            user_name="updated_driver",
            password="secret",
            email="updated@example.com",
            phone="555",
            role=RoleName.DRIVER,
            status=UserStatus.ACTIVE,
        ),
    )

    updated = run_async(driver_service.edit_driver(session, driver.id, data))

    assert updated.plate_number == "NEW123"
    assert updated.user.full_name == "Updated Driver"
    assert session.commits == 1
