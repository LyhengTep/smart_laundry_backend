from unittest.mock import MagicMock

import pytest
from fastapi.security import HTTPAuthorizationCredentials
from jose import jwt

from app.lib import security
from app.core.config import JWT_ALGORITHM, JWT_SECRET


def test_hash_password_produces_bcrypt_hash() -> None:
    hashed = security.hash_password("my-secret")
    assert hashed.startswith("$2b$") or hashed.startswith("$2a$")


def test_verify_password_returns_true_for_correct_password() -> None:
    hashed = security.hash_password("correct")
    assert security.verify_password("correct", hashed) is True


def test_verify_password_returns_false_for_wrong_password() -> None:
    hashed = security.hash_password("correct")
    assert security.verify_password("wrong", hashed) is False


def test_create_access_token_encodes_subject() -> None:
    token = security.create_access_token("user-abc")
    payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    assert payload["sub"] == "user-abc"


def test_create_access_token_sets_expiry() -> None:
    token = security.create_access_token("user-xyz")
    payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    assert "exp" in payload


def test_get_current_user_returns_subject_from_valid_token() -> None:
    token = security.create_access_token("user-123")
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    result = security.get_current_user(credentials)
    assert result == "user-123"


def test_get_current_user_raises_401_for_invalid_token() -> None:
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="not.a.token")
    with pytest.raises(Exception) as exc:
        security.get_current_user(credentials)
    assert getattr(exc.value, "status_code", None) == 401


def test_get_current_user_raises_401_when_sub_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    token_no_sub = jwt.encode({"exp": 9999999999}, JWT_SECRET, algorithm=JWT_ALGORITHM)
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token_no_sub)
    with pytest.raises(Exception) as exc:
        security.get_current_user(credentials)
    assert getattr(exc.value, "status_code", None) == 401
