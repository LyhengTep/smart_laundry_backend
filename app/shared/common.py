from enum import Enum
from uuid import uuid4
from datetime import datetime
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


def get_notification_template(status: "OrderStatus",order_no:str):
    from app.modules.orders.models import OrderStatus

    if status==OrderStatus.CANCELLED:
        return f"Your order no {order_no} was cancelled"
    if status==OrderStatus.DELIVERED_TO_SHOP:
        return f"Your order no {order_no} was delivered to shop successfully"
    

    return "Uknown notification"



def get_notification_title(status: "OrderStatus"):
    from app.modules.orders.models import OrderStatus

    if status==OrderStatus.CANCELLED:
        return "Order Cancelled"
    if status==OrderStatus.DELIVERED_TO_SHOP:
        return f"Laundry Received by Shop"
    

    return "Uknown Title"


def generate_order_no() -> str:
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    suffix = uuid4().hex[:6].upper()
    return f"ORD-{timestamp}-{suffix}"