"""Integration tests — drivers endpoints."""
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from app.tests.integration.conftest import (
    make_business,
    make_business_service,
    make_driver,
    make_laundry_service,
    make_order,
    make_user,
)

pytestmark = pytest.mark.anyio


async def test_list_drivers_empty(client: AsyncClient) -> None:
    response = await client.get("/api/v1/drivers/")

    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0


async def test_list_drivers_with_data(client: AsyncClient, db_session: AsyncSession) -> None:
    driver_user, _ = await make_user(db_session, role="DRIVER")
    await make_driver(db_session, driver_user.id)

    response = await client.get("/api/v1/drivers/")

    assert response.status_code == 200
    assert response.json()["total"] == 1


async def test_get_driver_by_id(client: AsyncClient, db_session: AsyncSession) -> None:
    driver_user, _ = await make_user(db_session, role="DRIVER")
    driver = await make_driver(db_session, driver_user.id)

    response = await client.get(f"/api/v1/drivers/{driver.id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(driver.id)


async def test_get_driver_not_found_returns_404(client: AsyncClient) -> None:
    response = await client.get(f"/api/v1/drivers/{uuid4()}")
    assert response.status_code == 404


async def test_get_driver_by_user_id(client: AsyncClient, db_session: AsyncSession) -> None:
    driver_user, _ = await make_user(db_session, role="DRIVER")
    driver = await make_driver(db_session, driver_user.id)

    response = await client.get(f"/api/v1/drivers/by-user/{driver_user.id}")

    assert response.status_code == 200
    assert response.json()["user_id"] == str(driver_user.id)


async def test_approve_driver(client: AsyncClient, db_session: AsyncSession) -> None:
    driver_user, _ = await make_user(db_session, role="DRIVER", status="INACTIVE")
    driver = await make_driver(db_session, driver_user.id)

    response = await client.patch(f"/api/v1/drivers/{driver.id}/approve")

    assert response.status_code == 200
    assert response.json()["user"]["status"] == "ACTIVE"


async def test_reject_driver(client: AsyncClient, db_session: AsyncSession) -> None:
    driver_user, _ = await make_user(db_session, role="DRIVER")
    driver = await make_driver(db_session, driver_user.id)

    response = await client.patch(f"/api/v1/drivers/{driver.id}/reject")

    assert response.status_code == 200
    assert response.json()["user"]["status"] == "REJECTED"


async def test_suspend_driver(client: AsyncClient, db_session: AsyncSession) -> None:
    driver_user, _ = await make_user(db_session, role="DRIVER")
    driver = await make_driver(db_session, driver_user.id)

    response = await client.patch(f"/api/v1/drivers/{driver.id}/suspend")

    assert response.status_code == 200
    assert response.json()["user"]["status"] == "SUSPENDED"


async def test_list_assignments_empty(client: AsyncClient) -> None:
    response = await client.get("/api/v1/drivers/assignments/")

    assert response.status_code == 200
    assert response.json()["total"] == 0


async def test_create_assignment_success(client: AsyncClient, db_session: AsyncSession) -> None:
    customer, _ = await make_user(db_session, role="CUSTOMER")
    merchant, _ = await make_user(db_session, role="MERCHANT")
    business = await make_business(db_session, owner_id=merchant.id)
    laundry_svc = await make_laundry_service(db_session)
    biz_svc = await make_business_service(db_session, business.id, laundry_svc.id)
    order = await make_order(client, customer.id, business.id, biz_svc.id)

    driver_user, _ = await make_user(db_session, role="DRIVER")
    driver = await make_driver(db_session, driver_user.id)

    response = await client.post(
        "/api/v1/drivers/assignments/",
        json={"driver_id": str(driver.id), "order_id": order["id"], "role": "PICKUP"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["driver_id"] == str(driver.id)
    assert body["role"] == "PICKUP"


async def test_create_assignment_driver_not_online_returns_400(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    from app.modules.drivers.models import DriverStatus
    from sqlmodel import select
    from app.modules.drivers.models import Driver

    customer, _ = await make_user(db_session, role="CUSTOMER")
    merchant, _ = await make_user(db_session, role="MERCHANT")
    business = await make_business(db_session, owner_id=merchant.id)
    laundry_svc = await make_laundry_service(db_session)
    biz_svc = await make_business_service(db_session, business.id, laundry_svc.id)
    order = await make_order(client, customer.id, business.id, biz_svc.id)

    driver_user, _ = await make_user(db_session, role="DRIVER")
    driver = await make_driver(db_session, driver_user.id)
    driver.driver_status = DriverStatus.OFFLINE
    db_session.add(driver)
    await db_session.commit()

    response = await client.post(
        "/api/v1/drivers/assignments/",
        json={"driver_id": str(driver.id), "order_id": order["id"], "role": "PICKUP"},
    )

    assert response.status_code == 400


async def test_create_assignment_driver_not_found_returns_404(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    customer, _ = await make_user(db_session, role="CUSTOMER")
    merchant, _ = await make_user(db_session, role="MERCHANT")
    business = await make_business(db_session, owner_id=merchant.id)
    laundry_svc = await make_laundry_service(db_session)
    biz_svc = await make_business_service(db_session, business.id, laundry_svc.id)
    order = await make_order(client, customer.id, business.id, biz_svc.id)

    response = await client.post(
        "/api/v1/drivers/assignments/",
        json={"driver_id": str(uuid4()), "order_id": order["id"], "role": "PICKUP"},
    )

    assert response.status_code == 404


async def test_get_assignment_by_id(client: AsyncClient, db_session: AsyncSession) -> None:
    customer, _ = await make_user(db_session, role="CUSTOMER")
    merchant, _ = await make_user(db_session, role="MERCHANT")
    business = await make_business(db_session, owner_id=merchant.id)
    laundry_svc = await make_laundry_service(db_session)
    biz_svc = await make_business_service(db_session, business.id, laundry_svc.id)
    order = await make_order(client, customer.id, business.id, biz_svc.id)
    driver_user, _ = await make_user(db_session, role="DRIVER")
    driver = await make_driver(db_session, driver_user.id)

    assignment = (
        await client.post(
            "/api/v1/drivers/assignments/",
            json={"driver_id": str(driver.id), "order_id": order["id"], "role": "PICKUP"},
        )
    ).json()

    response = await client.get(f"/api/v1/drivers/assignments/{assignment['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == assignment["id"]


async def test_reject_assignment(client: AsyncClient, db_session: AsyncSession) -> None:
    customer, _ = await make_user(db_session, role="CUSTOMER")
    merchant, _ = await make_user(db_session, role="MERCHANT")
    business = await make_business(db_session, owner_id=merchant.id)
    laundry_svc = await make_laundry_service(db_session)
    biz_svc = await make_business_service(db_session, business.id, laundry_svc.id)
    order = await make_order(client, customer.id, business.id, biz_svc.id)
    driver_user, _ = await make_user(db_session, role="DRIVER")
    driver = await make_driver(db_session, driver_user.id)

    assignment = (
        await client.post(
            "/api/v1/drivers/assignments/",
            json={"driver_id": str(driver.id), "order_id": order["id"], "role": "PICKUP"},
        )
    ).json()

    response = await client.patch(f"/api/v1/drivers/assignments/{assignment['id']}/reject")

    assert response.status_code == 200
    assert response.json()["status"] == "REJECTED"


async def test_accept_assignment(client: AsyncClient, db_session: AsyncSession) -> None:
    customer, _ = await make_user(db_session, role="CUSTOMER")
    merchant, token = await make_user(db_session, role="MERCHANT")
    business = await make_business(db_session, owner_id=merchant.id)
    laundry_svc = await make_laundry_service(db_session)
    biz_svc = await make_business_service(db_session, business.id, laundry_svc.id)
    order = await make_order(client, customer.id, business.id, biz_svc.id)

    # Confirm the order so CONFIRMED → PICKUP_ASSIGNED transition is valid
    await client.patch(
        f"/api/v1/orders/{order['id']}/status",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "CONFIRMED"},
    )

    driver_user, driver_token = await make_user(db_session, role="DRIVER")
    driver = await make_driver(db_session, driver_user.id)

    assignment = (
        await client.post(
            "/api/v1/drivers/assignments/",
            json={"driver_id": str(driver.id), "order_id": order["id"], "role": "PICKUP"},
        )
    ).json()

    response = await client.patch(
        f"/api/v1/drivers/assignments/{assignment['id']}/accept",
        headers={"Authorization": f"Bearer {driver_token}"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "ACCEPTED"
