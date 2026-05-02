"""Integration tests — orders endpoints."""
import pytest
from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from app.tests.integration.conftest import (
    make_business,
    make_business_service,
    make_laundry_service,
    make_user,
)

pytestmark = pytest.mark.anyio


async def _order_payload(customer_id, business_id, business_service_id) -> dict:
    return {
        "customer_id": str(customer_id),
        "business_id": str(business_id),
        "pickup_method": "PICKUP",
        "payment_method": "CASH",
        "payment_currency": "USD",
        "pickup_address": "123 Home St",
        "delivery_address": "123 Home St",
        "pickup_latitude": 11.5,
        "pickup_longitude": 104.9,
        "delivery_latitude": 11.5,
        "delivery_longitude": 104.9,
        "discount": 0,
        "items": [{"business_service_id": str(business_service_id), "quantity": 2.0}],
    }


async def test_list_orders_empty(client: AsyncClient) -> None:
    response = await client.get("/api/v1/orders/")

    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0


async def test_create_order_success(client: AsyncClient, db_session: AsyncSession) -> None:
    customer, _ = await make_user(db_session, role="CUSTOMER")
    merchant, _ = await make_user(db_session, role="MERCHANT")
    business = await make_business(db_session, owner_id=merchant.id)
    laundry_svc = await make_laundry_service(db_session)
    biz_svc = await make_business_service(db_session, business.id, laundry_svc.id)

    payload = await _order_payload(customer.id, business.id, biz_svc.id)
    response = await client.post("/api/v1/orders/", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "PENDING"
    assert body["customer_id"] == str(customer.id)
    assert len(body["items"]) == 1
    assert body["total"] == 10.0  # 5.0 base_price × 2.0 quantity


async def test_create_order_invalid_customer_returns_404(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    from uuid import uuid4

    merchant, _ = await make_user(db_session, role="MERCHANT")
    business = await make_business(db_session, owner_id=merchant.id)
    laundry_svc = await make_laundry_service(db_session)
    biz_svc = await make_business_service(db_session, business.id, laundry_svc.id)

    payload = await _order_payload(uuid4(), business.id, biz_svc.id)
    response = await client.post("/api/v1/orders/", json=payload)

    assert response.status_code == 404


async def test_create_order_invalid_business_returns_404(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    from uuid import uuid4

    customer, _ = await make_user(db_session, role="CUSTOMER")
    merchant, _ = await make_user(db_session, role="MERCHANT")
    business = await make_business(db_session, owner_id=merchant.id)
    laundry_svc = await make_laundry_service(db_session)
    biz_svc = await make_business_service(db_session, business.id, laundry_svc.id)

    payload = await _order_payload(customer.id, uuid4(), biz_svc.id)
    response = await client.post("/api/v1/orders/", json=payload)

    assert response.status_code == 404


async def test_get_order_by_id(client: AsyncClient, db_session: AsyncSession) -> None:
    customer, _ = await make_user(db_session, role="CUSTOMER")
    merchant, _ = await make_user(db_session, role="MERCHANT")
    business = await make_business(db_session, owner_id=merchant.id)
    laundry_svc = await make_laundry_service(db_session)
    biz_svc = await make_business_service(db_session, business.id, laundry_svc.id)

    payload = await _order_payload(customer.id, business.id, biz_svc.id)
    created = (await client.post("/api/v1/orders/", json=payload)).json()

    response = await client.get(f"/api/v1/orders/{created['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


async def test_get_order_not_found(client: AsyncClient) -> None:
    from uuid import uuid4
    response = await client.get(f"/api/v1/orders/{uuid4()}")
    assert response.status_code == 404


async def test_list_orders_pagination(client: AsyncClient, db_session: AsyncSession) -> None:
    customer, _ = await make_user(db_session, role="CUSTOMER")
    merchant, _ = await make_user(db_session, role="MERCHANT")
    business = await make_business(db_session, owner_id=merchant.id)
    laundry_svc = await make_laundry_service(db_session)
    biz_svc = await make_business_service(db_session, business.id, laundry_svc.id)

    payload = await _order_payload(customer.id, business.id, biz_svc.id)
    for _ in range(3):
        await client.post("/api/v1/orders/", json=payload)

    response = await client.get("/api/v1/orders/?page=1&size=2")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert len(body["items"]) == 2
    assert body["pages"] == 2


async def test_update_order_status_confirm(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    customer, _ = await make_user(db_session, role="CUSTOMER")
    merchant, token = await make_user(db_session, role="MERCHANT")
    business = await make_business(db_session, owner_id=merchant.id)
    laundry_svc = await make_laundry_service(db_session)
    biz_svc = await make_business_service(db_session, business.id, laundry_svc.id)

    payload = await _order_payload(customer.id, business.id, biz_svc.id)
    order = (await client.post("/api/v1/orders/", json=payload)).json()

    response = await client.patch(
        f"/api/v1/orders/{order['id']}/status",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "CONFIRMED"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "CONFIRMED"


async def test_update_order_status_invalid_transition_returns_400(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    customer, _ = await make_user(db_session, role="CUSTOMER")
    merchant, token = await make_user(db_session, role="MERCHANT")
    business = await make_business(db_session, owner_id=merchant.id)
    laundry_svc = await make_laundry_service(db_session)
    biz_svc = await make_business_service(db_session, business.id, laundry_svc.id)

    payload = await _order_payload(customer.id, business.id, biz_svc.id)
    order = (await client.post("/api/v1/orders/", json=payload)).json()

    response = await client.patch(
        f"/api/v1/orders/{order['id']}/status",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "DELIVERED"},
    )

    assert response.status_code == 400


async def test_update_order_status_confirm_with_pickup_fee(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    customer, _ = await make_user(db_session, role="CUSTOMER")
    merchant, token = await make_user(db_session, role="MERCHANT")
    business = await make_business(db_session, owner_id=merchant.id)
    laundry_svc = await make_laundry_service(db_session)
    biz_svc = await make_business_service(db_session, business.id, laundry_svc.id)

    payload = await _order_payload(customer.id, business.id, biz_svc.id)
    order = (await client.post("/api/v1/orders/", json=payload)).json()

    response = await client.patch(
        f"/api/v1/orders/{order['id']}/status",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "CONFIRMED", "pickup_fee": 2.0},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["pickup_fee"] == 2.0
    assert body["delivery_fee"] == 2.0
    assert body["total"] == 14.0  # subtotal 10 + pickup_fee 2 + delivery_fee 2


async def _advance_order_to(client: AsyncClient, order_id: str, token: str, *statuses: str) -> None:
    for status in statuses:
        await client.patch(
            f"/api/v1/orders/{order_id}/status",
            headers={"Authorization": f"Bearer {token}"},
            json={"status": status},
        )


async def test_search_order_by_exact_order_no(client: AsyncClient, db_session: AsyncSession) -> None:
    customer, _ = await make_user(db_session, role="CUSTOMER")
    merchant, _ = await make_user(db_session, role="MERCHANT")
    business = await make_business(db_session, owner_id=merchant.id)
    laundry_svc = await make_laundry_service(db_session)
    biz_svc = await make_business_service(db_session, business.id, laundry_svc.id)

    from app.tests.integration.conftest import make_order
    order = await make_order(client, customer.id, business.id, biz_svc.id)

    response = await client.get(f"/api/v1/orders/search?order_no={order['order_no']}")

    assert response.status_code == 200
    body = response.json()
    assert body["order_no"] == order["order_no"]
    assert body["status"] == "PENDING"


async def test_search_order_returns_404_for_unknown_order_no(client: AsyncClient) -> None:
    response = await client.get("/api/v1/orders/search?order_no=ORD-DOESNOTEXIST")
    assert response.status_code == 404


async def test_update_order_pricing_after_delivery_to_shop(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    customer, _ = await make_user(db_session, role="CUSTOMER")
    merchant, token = await make_user(db_session, role="MERCHANT")
    business = await make_business(db_session, owner_id=merchant.id)
    laundry_svc = await make_laundry_service(db_session)
    biz_svc = await make_business_service(db_session, business.id, laundry_svc.id)

    from app.tests.integration.conftest import make_order
    order = await make_order(client, customer.id, business.id, biz_svc.id)
    order_id = order["id"]

    await _advance_order_to(
        client, order_id, token,
        "CONFIRMED", "PICKUP_ASSIGNED", "PICKED_UP", "DELIVERED_TO_SHOP",
    )

    item_id = order["items"][0]["id"]
    response = await client.patch(
        f"/api/v1/orders/{order_id}/pricing",
        json={"items": [{"order_item_id": item_id, "quantity": 3.0}]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["items"][0]["quantity"] == 3.0
    assert body["total"] == 15.0  # 5.0 price × 3.0 qty
