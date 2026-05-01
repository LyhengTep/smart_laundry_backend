"""Integration tests — auth endpoints."""
import pytest
from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from app.tests.integration.conftest import make_user

pytestmark = pytest.mark.anyio


async def test_signup_customer_success(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auths/signup",
        json={
            "full_name": "Alice",
            "user_name": "alice",
            "password": "pass1234",
            "email": "alice@example.com",
            "phone": None,
            "role": "CUSTOMER",
        },
    )
    assert response.status_code == 200
    assert response.json() == {"msg": "World"}


async def test_signup_duplicate_user_returns_400(client: AsyncClient) -> None:
    payload = {
        "full_name": "Bob",
        "user_name": "bob",
        "password": "pass1234",
        "email": "bob@example.com",
        "phone": None,
        "role": "CUSTOMER",
    }
    await client.post("/api/v1/auths/signup", json=payload)
    response = await client.post("/api/v1/auths/signup", json=payload)

    assert response.status_code == 400


async def test_login_returns_token(client: AsyncClient, db_session: AsyncSession) -> None:
    user, _ = await make_user(db_session, role="CUSTOMER")

    response = await client.post(
        "/api/v1/auths/login",
        json={"login": user.user_name, "password": "secret123", "role": "CUSTOMER"},
    )

    assert response.status_code == 200
    body = response.json()
    assert "token" in body
    assert body["user_name"] == user.user_name


async def test_login_wrong_password_returns_404(client: AsyncClient, db_session: AsyncSession) -> None:
    user, _ = await make_user(db_session, role="CUSTOMER")

    response = await client.post(
        "/api/v1/auths/login",
        json={"login": user.user_name, "password": "wrong-password", "role": "CUSTOMER"},
    )

    assert response.status_code == 404


async def test_login_nonexistent_user_returns_404(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auths/login",
        json={"login": "nobody", "password": "secret", "role": "CUSTOMER"},
    )

    assert response.status_code == 404


async def test_logout_clears_session(client: AsyncClient, db_session: AsyncSession) -> None:
    user, token = await make_user(db_session, role="CUSTOMER")

    response = await client.post(
        "/api/v1/auths/logout",
        json={"user_id": str(user.id), "role": "CUSTOMER"},
    )

    assert response.status_code == 200
    assert response.json() == {"message": "Logout successful"}
