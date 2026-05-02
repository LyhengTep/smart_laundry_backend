"""Integration tests — payments endpoints."""
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from app.tests.integration.conftest import (
    make_business,
    make_business_service,
    make_laundry_service,
    make_order,
    make_user,
)

pytestmark = pytest.mark.anyio


def _payment_payload(order_id) -> dict:
    return {
        "order_id": str(order_id),
        "method": "CASH",
        "status": "PENDING",
        "amount": "5.00",
        "currency": "USD",
        "type": "WASHING_SERVICE_FEE",
        "paid_by": "CUSTOMER",
    }


async def _setup_order(client: AsyncClient, db_session: AsyncSession) -> dict:
    customer, _ = await make_user(db_session, role="CUSTOMER")
    merchant, _ = await make_user(db_session, role="MERCHANT")
    business = await make_business(db_session, owner_id=merchant.id)
    laundry_svc = await make_laundry_service(db_session)
    biz_svc = await make_business_service(db_session, business.id, laundry_svc.id)
    return await make_order(client, customer.id, business.id, biz_svc.id)


async def test_list_payments_empty(client: AsyncClient) -> None:
    response = await client.get("/api/v1/payments/")

    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["total"] == 0


async def test_create_payment_success(client: AsyncClient, db_session: AsyncSession) -> None:
    order = await _setup_order(client, db_session)

    response = await client.post("/api/v1/payments/", json=_payment_payload(order["id"]))

    assert response.status_code == 200
    body = response.json()
    assert body["order_id"] == order["id"]
    assert body["status"] == "PENDING"
    assert body["type"] == "WASHING_SERVICE_FEE"


async def test_create_payment_order_not_found_returns_404(client: AsyncClient) -> None:
    response = await client.post("/api/v1/payments/", json=_payment_payload(uuid4()))
    assert response.status_code == 404


async def test_get_payment_by_id(client: AsyncClient, db_session: AsyncSession) -> None:
    order = await _setup_order(client, db_session)
    created = (await client.post("/api/v1/payments/", json=_payment_payload(order["id"]))).json()

    response = await client.get(f"/api/v1/payments/{created['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


async def test_get_payment_not_found_returns_404(client: AsyncClient) -> None:
    response = await client.get(f"/api/v1/payments/{uuid4()}")
    assert response.status_code == 404


async def test_update_payment_amount(client: AsyncClient, db_session: AsyncSession) -> None:
    order = await _setup_order(client, db_session)
    created = (await client.post("/api/v1/payments/", json=_payment_payload(order["id"]))).json()

    response = await client.patch(
        f"/api/v1/payments/{created['id']}",
        json={"amount": "12.50"},
    )

    assert response.status_code == 200
    assert float(response.json()["amount"]) == 12.50


async def test_confirm_payment(client: AsyncClient, db_session: AsyncSession) -> None:
    order = await _setup_order(client, db_session)
    created = (await client.post("/api/v1/payments/", json=_payment_payload(order["id"]))).json()

    response = await client.post(
        f"/api/v1/payments/{created['id']}/confirm",
        json={"confirmed_by": "ADMIN"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "COLLECTED"
    assert body["confirmed_by"] == "ADMIN"


async def test_confirm_non_pending_payment_returns_400(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    order = await _setup_order(client, db_session)
    created = (await client.post("/api/v1/payments/", json=_payment_payload(order["id"]))).json()
    await client.post(f"/api/v1/payments/{created['id']}/confirm", json={"confirmed_by": "ADMIN"})

    response = await client.post(
        f"/api/v1/payments/{created['id']}/confirm",
        json={"confirmed_by": "ADMIN"},
    )

    assert response.status_code == 400


async def test_delete_payment(client: AsyncClient, db_session: AsyncSession) -> None:
    order = await _setup_order(client, db_session)
    created = (await client.post("/api/v1/payments/", json=_payment_payload(order["id"]))).json()

    response = await client.delete(f"/api/v1/payments/{created['id']}")

    assert response.status_code == 200
    assert response.json() is True
    assert (await client.get(f"/api/v1/payments/{created['id']}")).status_code == 404


async def test_list_payments_filtered_by_order_id(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    customer, _ = await make_user(db_session, role="CUSTOMER")
    merchant, _ = await make_user(db_session, role="MERCHANT")
    business = await make_business(db_session, owner_id=merchant.id)
    laundry_svc = await make_laundry_service(db_session)
    biz_svc = await make_business_service(db_session, business.id, laundry_svc.id)

    order_a = await make_order(client, customer.id, business.id, biz_svc.id)
    order_b = await make_order(client, customer.id, business.id, biz_svc.id)

    await client.post("/api/v1/payments/", json=_payment_payload(order_a["id"]))
    await client.post("/api/v1/payments/", json=_payment_payload(order_b["id"]))

    response = await client.get(f"/api/v1/payments/?order_id={order_a['id']}")

    assert response.status_code == 200
    body = response.json()
    assert all(item["order_id"] == order_a["id"] for item in body["items"])
