"""Integration tests — businesses endpoints."""
import pytest
from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from app.tests.integration.conftest import make_business, make_user

pytestmark = pytest.mark.anyio


async def test_list_businesses_returns_empty_page(client: AsyncClient) -> None:
    response = await client.get("/api/v1/businesses/")

    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0
    assert body["page"] == 1


async def test_list_businesses_returns_created_business(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    merchant, _ = await make_user(db_session, role="MERCHANT")
    await make_business(db_session, owner_id=merchant.id)

    response = await client.get("/api/v1/businesses/")

    assert response.status_code == 200
    assert response.json()["total"] == 1


async def test_create_business_requires_auth(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/businesses/",
        json={
            "name": "Laundry Co",
            "address": "1 Main St",
            "phone": "555",
            "latitude": 11.0,
            "longitude": 104.0,
            "profile_image_url": None,
            "cover_image_url": None,
            "open_time": "08:00:00",
            "close_time": "20:00:00",
        },
    )
    assert response.status_code == 401


async def test_create_business_as_merchant(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    merchant, token = await make_user(db_session, role="MERCHANT")

    response = await client.post(
        "/api/v1/businesses/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Fresh Clean",
            "address": "2 Market St",
            "phone": "123456",
            "latitude": 11.5,
            "longitude": 104.9,
            "profile_image_url": None,
            "cover_image_url": None,
            "open_time": "08:00:00",
            "close_time": "20:00:00",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Fresh Clean"
    assert body["owner_id"] == str(merchant.id)


async def test_get_business_by_id(client: AsyncClient, db_session: AsyncSession) -> None:
    merchant, _ = await make_user(db_session, role="MERCHANT")
    business = await make_business(db_session, owner_id=merchant.id)

    response = await client.get(f"/api/v1/businesses/{business.id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(business.id)


async def test_get_business_not_found(client: AsyncClient) -> None:
    from uuid import uuid4
    response = await client.get(f"/api/v1/businesses/{uuid4()}")
    assert response.status_code == 404


async def test_list_my_businesses_returns_only_own_shops(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    owner, token = await make_user(db_session, role="MERCHANT")
    other, _ = await make_user(db_session, role="MERCHANT")

    await make_business(db_session, owner_id=owner.id)
    await make_business(db_session, owner_id=other.id)

    response = await client.get(
        "/api/v1/businesses/mine",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["owner_id"] == str(owner.id)


async def test_toggle_shop_status_close_open(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    owner, token = await make_user(db_session, role="MERCHANT")
    business = await make_business(db_session, owner_id=owner.id)
    headers = {"Authorization": f"Bearer {token}"}

    close_resp = await client.patch(
        f"/api/v1/businesses/{business.id}/shop-status",
        headers=headers,
        json={"action": "CLOSE", "force": True},
    )
    assert close_resp.status_code == 200
    assert close_resp.json()["status"] == "CLOSED"

    open_resp = await client.patch(
        f"/api/v1/businesses/{business.id}/shop-status",
        headers=headers,
        json={"action": "OPEN"},
    )
    assert open_resp.status_code == 200
    assert open_resp.json()["status"] == "OPEN"


async def test_toggle_shop_status_already_closed_returns_409(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    from app.modules.businesses.models import ShopStatus

    owner, token = await make_user(db_session, role="MERCHANT")
    business = await make_business(db_session, owner_id=owner.id)
    business.status = ShopStatus.CLOSED
    db_session.add(business)
    await db_session.commit()

    response = await client.patch(
        f"/api/v1/businesses/{business.id}/shop-status",
        headers={"Authorization": f"Bearer {token}"},
        json={"action": "CLOSE"},
    )
    assert response.status_code == 409


async def test_toggle_shop_status_unauthorized_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    owner, _ = await make_user(db_session, role="MERCHANT")
    other, token = await make_user(db_session, role="MERCHANT")
    business = await make_business(db_session, owner_id=owner.id)

    response = await client.patch(
        f"/api/v1/businesses/{business.id}/shop-status",
        headers={"Authorization": f"Bearer {token}"},
        json={"action": "CLOSE"},
    )
    assert response.status_code == 403
