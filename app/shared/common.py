
from datetime import datetime, timezone


def is_email(str_value: str) -> bool:
    return "@" in str_value


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
