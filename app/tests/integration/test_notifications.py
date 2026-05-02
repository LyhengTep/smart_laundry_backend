"""Integration tests — notifications endpoints."""
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from app.tests.integration.conftest import make_user

pytestmark = pytest.mark.anyio


def _notification_payload(user_id) -> dict:
    return {
        "user_id": str(user_id),
        "type": "SYSTEM",
        "title": "Test Title",
        "message": "Test message body",
        "channel": "IN_APP",
        "status": "PENDING",
    }


async def test_list_notifications_empty(client: AsyncClient) -> None:
    response = await client.get("/api/v1/notifications/")

    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0


async def test_create_notification(client: AsyncClient, db_session: AsyncSession) -> None:
    user, _ = await make_user(db_session)

    response = await client.post("/api/v1/notifications/", json=_notification_payload(user.id))

    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == str(user.id)
    assert body["title"] == "Test Title"
    assert body["is_read"] is False


async def test_get_notification_by_id(client: AsyncClient, db_session: AsyncSession) -> None:
    user, _ = await make_user(db_session)
    created = (
        await client.post("/api/v1/notifications/", json=_notification_payload(user.id))
    ).json()

    response = await client.get(f"/api/v1/notifications/{created['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


async def test_get_notification_not_found_returns_404(client: AsyncClient) -> None:
    response = await client.get(f"/api/v1/notifications/{uuid4()}")
    assert response.status_code == 404


async def test_mark_notification_as_read(client: AsyncClient, db_session: AsyncSession) -> None:
    user, _ = await make_user(db_session)
    created = (
        await client.post("/api/v1/notifications/", json=_notification_payload(user.id))
    ).json()

    response = await client.patch(f"/api/v1/notifications/{created['id']}/read")

    assert response.status_code == 200
    body = response.json()
    assert body["is_read"] is True
    assert body["status"] == "READ"
    assert body["read_at"] is not None


async def test_list_notifications_filtered_by_user_id(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user_a, _ = await make_user(db_session)
    user_b, _ = await make_user(db_session)
    await client.post("/api/v1/notifications/", json=_notification_payload(user_a.id))
    await client.post("/api/v1/notifications/", json=_notification_payload(user_b.id))

    response = await client.get(f"/api/v1/notifications/?user_id={user_a.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["user_id"] == str(user_a.id)


async def test_list_my_notifications_returns_only_own(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user_a, token_a = await make_user(db_session)
    user_b, _ = await make_user(db_session)
    await client.post("/api/v1/notifications/", json=_notification_payload(user_a.id))
    await client.post("/api/v1/notifications/", json=_notification_payload(user_b.id))

    response = await client.get(
        "/api/v1/notifications/mine",
        headers={"Authorization": f"Bearer {token_a}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["user_id"] == str(user_a.id)


async def test_list_my_notifications_requires_auth(client: AsyncClient) -> None:
    response = await client.get("/api/v1/notifications/mine")
    assert response.status_code == 401
