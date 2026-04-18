from datetime import datetime, timedelta, timezone
import logging

import bcrypt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.core.config import JWT_ALGORITHM, JWT_SECRET
from app.exceptions.http import create_401


security = HTTPBearer()


def get_current_user(token: HTTPAuthorizationCredentials = Depends(security)):
    print("called get current user")
    try:
        payload = jwt.decode(token.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        logging.info("Decoded JWT payload: %s", payload)
        if user_id is None:
            raise create_401("User is not found")
        return user_id
    except JWTError as e:
        raise create_401(f"error {e}")


def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


def verify_password(pw: str, hashed_pw: str) -> bool:
    return bcrypt.checkpw(pw.encode(), hashed_pw.encode())


def create_access_token(subject: str) -> str:
    expired_duration = datetime.now(timezone.utc) + timedelta(days=7)
    payload = {"sub": subject, "exp": expired_duration}
    token = jwt.encode(payload, JWT_SECRET, JWT_ALGORITHM)
    return token
