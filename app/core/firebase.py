from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

import firebase_admin
from firebase_admin import credentials, messaging

from app.core.config import FIREBASE_CREDENTIALS_PATH, FIREBASE_PROJECT_ID

logger = logging.getLogger(__name__)


def _load_firebase_credentials() -> credentials.Base | None:
    credentials_path = FIREBASE_CREDENTIALS_PATH or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    credentials_json = os.getenv("FIREBASE_CREDENTIALS_JSON")

    if credentials_json:
        return credentials.Certificate(json.loads(credentials_json))

    if credentials_path:
        path = Path(credentials_path)
        if not path.exists():
            logger.warning("Firebase credentials file not found at %s", path)
            return None
        return credentials.Certificate(str(path))

    logger.info("Firebase Admin credentials are not configured")
    return None


def initialize_firebase() -> bool:
    if firebase_admin._apps:
        return True

    credential = _load_firebase_credentials()
    if credential is None:
        return False

    app_options: dict[str, Any] = {}
    if FIREBASE_PROJECT_ID:
        app_options["projectId"] = FIREBASE_PROJECT_ID

    firebase_admin.initialize_app(credential, options=app_options or None)
    logger.info("Firebase Admin initialized")
    return True


def is_firebase_ready() -> bool:
    return bool(firebase_admin._apps)


def send_firebase_message(
    *,
    token: str,
    title: str,
    body: str,
    data: dict[str, str] | None = None,
) -> str:
    if not is_firebase_ready():
        raise RuntimeError("Firebase Admin is not initialized")

    message = messaging.Message(
        token=token,
        notification=messaging.Notification(title=title, body=body),
        data=data or {},
    )
    return messaging.send(message)


def send_firebase_multicast(
    *,
    tokens: list[str],
    title: str,
    body: str,
    data: dict[str, str] | None = None,
) -> messaging.BatchResponse:
    if not is_firebase_ready():
        raise RuntimeError("Firebase Admin is not initialized")
    if not tokens:
        raise ValueError("tokens cannot be empty")

    message = messaging.MulticastMessage(
        tokens=tokens,
        notification=messaging.Notification(title=title, body=body),
        data=data or {},
    )
    return messaging.send_each_for_multicast(message)
