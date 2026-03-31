from enum import Enum

from app.lib.datetime import utc_now
from app.lib.identity import is_email


class RoleName(str, Enum):
    ADMIN = "ADMIN"
    MERCHANT = "MERCHANT"
    DRIVER = "DRIVER"
    CUSTOMER = "CUSTOMER"


class UserStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"
    REJECTED = "REJECTED"



# WEBSOCKET ROOMS 
def get_assignment_room(driver_id: str) -> str:
    return f"assignment:{driver_id}"