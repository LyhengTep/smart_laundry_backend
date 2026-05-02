"""Integration tests — business-services endpoints."""
import pytest
from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from app.tests.integration.conftest import (
    make_business,
    make_laundry_service,
    make_user,
)

pytestmark = pytest.mark.anyio


async def _setup(db_session: AsyncSession):
    merchant, _ = await make_user(db_session, role="MERCHANT")
    business = await make_business(db_session, owner_id=merchant.id)
    laundry_svc = await make_laundry_service(db_session)
    return business, laundry_svc


async def test_list_business_services_empty(client: AsyncClient) -> None:
    response = await client.get("/api/v1/business-services/")

    assert response.status_code == 200
    assert response.json() == []


async def test_create_business_service(client: AsyncClient, db_session: AsyncSession) -> None:
    business, laundry_svc = await _setup(db_session)

    response = await client.post(
        "/api/v1/business-services/",
        json={
            "business_id": str(business.id),
            "service_id": laundry_svc.id,
            "base_price": 8.0,
            "pricing_type": "per_kg",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["business_id"] == str(business.id)
    assert body["base_price"] == 8.0
    assert body["pricing_type"] == "per_kg"


async def test_create_business_service_list_reflects_new_entry(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    business, laundry_svc = await _setup(db_session)

    await client.post(
        "/api/v1/business-services/",
        json={
            "business_id": str(business.id),
            "service_id": laundry_svc.id,
            "base_price": 4.0,
            "pricing_type": "per_item",
        },
    )

    response = await client.get("/api/v1/business-services/")

    assert response.status_code == 200
    assert len(response.json()) == 1


async def test_bulk_create_business_services(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    business, laundry_svc = await _setup(db_session)

    # Need a second distinct laundry service for bulk creation (unique service_id per business)
    from app.lib.datetime import utc_now
    from app.modules.laundry_services.model import LaundryService, ServiceEnum

    laundry_svc_2 = LaundryService(
        name=ServiceEnum.IRON,
        code="IRON",
        description="Iron service",
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    db_session.add(laundry_svc_2)
    await db_session.commit()
    await db_session.refresh(laundry_svc_2)

    response = await client.post(
        "/api/v1/business-services/bulk",
        json=[
            {"business_id": str(business.id), "service_id": laundry_svc.id, "base_price": 5.0, "pricing_type": "per_kg"},
            {"business_id": str(business.id), "service_id": laundry_svc_2.id, "base_price": 3.0, "pricing_type": "per_item"},
        ],
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    prices = {item["base_price"] for item in body}
    assert prices == {5.0, 3.0}
