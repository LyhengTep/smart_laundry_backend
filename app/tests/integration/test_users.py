"""Integration tests — users endpoints."""
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from app.tests.integration.conftest import make_user

pytestmark = pytest.mark.anyio


def _user_payload(**overrides) -> dict:
    uid = uuid4().hex[:8]
    payload = {
        "full_name": "New User",
        "user_name": f"newuser_{uid}",
        "password": "secret123",
        "email": f"{uid}@example.com",
        "phone": None,
        "role": "CUSTOMER",
    }
    payload.update(overrides)
    return payload


async def test_list_users_empty(client: AsyncClient) -> None:
    response = await client.get("/api/v1/users/")

    assert response.status_code == 200
    assert response.json() == []


async def test_list_users_with_data(client: AsyncClient, db_session: AsyncSession) -> None:
    await make_user(db_session, role="CUSTOMER")
    await make_user(db_session, role="MERCHANT")

    response = await client.get("/api/v1/users/")

    assert response.status_code == 200
    assert len(response.json()) == 2


async def test_create_user_success(client: AsyncClient) -> None:
    response = await client.post("/api/v1/users/", json=_user_payload())

    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "CUSTOMER"
    assert "password" not in body


async def test_get_user_by_id(client: AsyncClient, db_session: AsyncSession) -> None:
    user, _ = await make_user(db_session)

    response = await client.get(f"/api/v1/users/{user.id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(user.id)


async def test_get_user_not_found_returns_404(client: AsyncClient) -> None:
    response = await client.get(f"/api/v1/users/{uuid4()}")
    assert response.status_code == 404


async def test_delete_user(client: AsyncClient, db_session: AsyncSession) -> None:
    user, _ = await make_user(db_session)

    response = await client.delete(f"/api/v1/users/{user.id}")

    assert response.status_code == 200
    assert response.json() is True
    assert (await client.get(f"/api/v1/users/{user.id}")).status_code == 404


async def test_update_user_msg_token(client: AsyncClient, db_session: AsyncSession) -> None:
    user, _ = await make_user(db_session)

    response = await client.patch(
        f"/api/v1/users/{user.id}/msg-token",
        json={"msg_token": "fcm-device-token-abc123"},
    )

    assert response.status_code == 200
    assert response.json()["id"] == str(user.id)


async def test_clear_user_msg_token(client: AsyncClient, db_session: AsyncSession) -> None:
    user, _ = await make_user(db_session)
    await client.patch(f"/api/v1/users/{user.id}/msg-token", json={"msg_token": "token-xyz"})

    response = await client.patch(
        f"/api/v1/users/{user.id}/msg-token",
        json={"msg_token": None},
    )

    assert response.status_code == 200
