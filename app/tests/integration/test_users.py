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


async def test_list_users_empty(client: AsyncClient, db_session: AsyncSession) -> None:
    _, token = await make_user(db_session)
    response = await client.get("/api/v1/users/", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 0


async def test_list_users_requires_auth(client: AsyncClient) -> None:
    response = await client.get("/api/v1/users/")
    assert response.status_code == 401


async def test_list_users_with_data(client: AsyncClient, db_session: AsyncSession) -> None:
    _, token = await make_user(db_session, role="CUSTOMER")
    await make_user(db_session, role="MERCHANT")

    response = await client.get("/api/v1/users/", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 2


async def test_list_users_filter_by_role(client: AsyncClient, db_session: AsyncSession) -> None:
    _, token = await make_user(db_session, role="CUSTOMER")
    await make_user(db_session, role="MERCHANT")

    response = await client.get("/api/v1/users/?role=CUSTOMER", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    body = response.json()
    assert all(u["role"] == "CUSTOMER" for u in body["items"])


async def test_approve_user(client: AsyncClient, db_session: AsyncSession) -> None:
    user, _ = await make_user(db_session, status="INACTIVE")
    _, token = await make_user(db_session)

    response = await client.patch(
        f"/api/v1/users/{user.id}/approve",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "ACTIVE"


async def test_approve_user_already_active_returns_400(client: AsyncClient, db_session: AsyncSession) -> None:
    user, _ = await make_user(db_session, status="ACTIVE")
    _, token = await make_user(db_session)

    response = await client.patch(
        f"/api/v1/users/{user.id}/approve",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400


async def test_create_user_success(client: AsyncClient, db_session: AsyncSession) -> None:
    _, token = await make_user(db_session)
    response = await client.post(
        "/api/v1/users/",
        json=_user_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "CUSTOMER"
    assert "password" not in body


async def test_get_user_by_id(client: AsyncClient, db_session: AsyncSession) -> None:
    user, token = await make_user(db_session)

    response = await client.get(
        f"/api/v1/users/{user.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["id"] == str(user.id)


async def test_get_user_not_found_returns_404(client: AsyncClient, db_session: AsyncSession) -> None:
    _, token = await make_user(db_session)
    response = await client.get(
        f"/api/v1/users/{uuid4()}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


async def test_deactivate_user(client: AsyncClient, db_session: AsyncSession) -> None:
    user, _ = await make_user(db_session, status="ACTIVE")
    _, token = await make_user(db_session)

    response = await client.patch(
        f"/api/v1/users/{user.id}/deactivate",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "INACTIVE"


async def test_deactivate_user_already_inactive_returns_400(client: AsyncClient, db_session: AsyncSession) -> None:
    user, _ = await make_user(db_session, status="INACTIVE")
    _, token = await make_user(db_session)

    response = await client.patch(
        f"/api/v1/users/{user.id}/deactivate",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400


async def test_delete_user(client: AsyncClient, db_session: AsyncSession) -> None:
    user, _ = await make_user(db_session)
    _, token = await make_user(db_session)

    response = await client.delete(
        f"/api/v1/users/{user.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json() is True
    assert (
        await client.get(f"/api/v1/users/{user.id}", headers={"Authorization": f"Bearer {token}"})
    ).status_code == 404


async def test_delete_user_not_found_returns_404(client: AsyncClient, db_session: AsyncSession) -> None:
    _, token = await make_user(db_session)
    response = await client.delete(
        f"/api/v1/users/{uuid4()}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


async def test_edit_user(client: AsyncClient, db_session: AsyncSession) -> None:
    user, token = await make_user(db_session)

    response = await client.patch(
        f"/api/v1/users/{user.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "full_name": "Edited Name",
            "user_name": f"edited_{uuid4().hex[:6]}",
            "email": f"{uuid4().hex[:8]}@edited.com",
            "phone": None,
            "role": "CUSTOMER",
            "status": "ACTIVE",
        },
    )

    assert response.status_code == 200
    assert response.json()["full_name"] == "Edited Name"


async def test_edit_user_with_new_password(client: AsyncClient, db_session: AsyncSession) -> None:
    user, token = await make_user(db_session)

    response = await client.patch(
        f"/api/v1/users/{user.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "full_name": "Same Name",
            "user_name": f"pw_{uuid4().hex[:6]}",
            "password": "newpass456",
            "email": f"{uuid4().hex[:8]}@edited.com",
            "phone": None,
            "role": "CUSTOMER",
            "status": "ACTIVE",
        },
    )

    assert response.status_code == 200


async def test_edit_user_not_found_returns_404(client: AsyncClient, db_session: AsyncSession) -> None:
    _, token = await make_user(db_session)
    response = await client.patch(
        f"/api/v1/users/{uuid4()}",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "full_name": "x", "user_name": "x",
            "email": "x@x.com", "phone": None, "role": "CUSTOMER", "status": "ACTIVE",
        },
    )
    assert response.status_code == 404


async def test_update_user_msg_token(client: AsyncClient, db_session: AsyncSession) -> None:
    user, token = await make_user(db_session)

    response = await client.patch(
        f"/api/v1/users/{user.id}/msg-token",
        headers={"Authorization": f"Bearer {token}"},
        json={"msg_token": "fcm-device-token-abc123"},
    )

    assert response.status_code == 200
    assert response.json()["id"] == str(user.id)


async def test_create_admin_by_admin_succeeds(client: AsyncClient, db_session: AsyncSession) -> None:
    _, token = await make_user(db_session, role="ADMIN")

    response = await client.post(
        "/api/v1/users/admin",
        json=_user_payload(role="CUSTOMER"),
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["role"] == "ADMIN"
    assert response.json()["status"] == "ACTIVE"


async def test_create_admin_by_non_admin_returns_403(client: AsyncClient, db_session: AsyncSession) -> None:
    _, token = await make_user(db_session, role="CUSTOMER")

    response = await client.post(
        "/api/v1/users/admin",
        json=_user_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


async def test_create_admin_requires_auth(client: AsyncClient) -> None:
    response = await client.post("/api/v1/users/admin", json=_user_payload())
    assert response.status_code == 401


async def test_clear_user_msg_token(client: AsyncClient, db_session: AsyncSession) -> None:
    user, token = await make_user(db_session)
    await client.patch(
        f"/api/v1/users/{user.id}/msg-token",
        headers={"Authorization": f"Bearer {token}"},
        json={"msg_token": "token-xyz"},
    )

    response = await client.patch(
        f"/api/v1/users/{user.id}/msg-token",
        headers={"Authorization": f"Bearer {token}"},
        json={"msg_token": None},
    )

    assert response.status_code == 200
