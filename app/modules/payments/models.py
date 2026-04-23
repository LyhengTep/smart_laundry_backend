
import decimal
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
import uuid

from sqlalchemy import Column, DateTime, Enum as SAEnum, Numeric, String
from sqlmodel import Field, Relationship, SQLModel

from app.lib.datetime import utc_now

if TYPE_CHECKING:
    from app.modules.orders.models import Order


class PaymentMethod(str, Enum):
    CASH = "CASH"
    CARD = "CARD"
    BANK_TRANSFER = "BANK_TRANSFER"
    E_WALLET = "E_WALLET"


class PaymentStatus(str, Enum):
    PENDING = "PENDING"
    COLLECTED = "COLLECTED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"
    PENDING_SETTLEMENT = "PENDING_SETTLEMENT"
    SETTLED = "SETTLED"
    


class CurrencyType(str, Enum):
    KHR = "KHR"
    USD = "USD"


class PaidByType(str, Enum):
    SHOP = "SHOP"
    CUSTOMER = "CUSTOMER"


class ConfirmedByType(str, Enum):
    DRIVER = "DRIVER"
    ADMIN = "ADMIN"


class PaymentType(str, Enum):
    PICKUP_FEE = "pickup_fee"
    DELIVERY_FEE = "delivery_fee"
    WASHING_SERVICE_FEE = "washing_service_fee"
    ADVANCE_SETTLEMENT = "advance_settlement"


class Payment(SQLModel, table=True):
    __tablename__ = "payments"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    method: PaymentMethod = Field(
        default=PaymentMethod.CASH,
        sa_column=Column(SAEnum(PaymentMethod, name="payment_method"), nullable=False),
    )
    status: PaymentStatus = Field(
        sa_column=Column(SAEnum(PaymentStatus, name="payment_status"), nullable=False),
    )
    amount: decimal.Decimal = Field(sa_column=Column(Numeric(10, 2), nullable=False, default=0))
    currency: CurrencyType = Field(
        sa_column=Column(SAEnum(CurrencyType, name="currency_type"), nullable=False),
    )
    provider_ref: str | None = Field(default=None, sa_column=Column(String(255), nullable=True))
    order_id: uuid.UUID = Field(foreign_key="orders.id", nullable=False, index=True)
    order: "Order" = Relationship(back_populates="payments")
    assignment_id: uuid.UUID | None = Field(default=None, foreign_key="driver_assignments.id", nullable=True, index=True)
    paid_by: PaidByType = Field(
        sa_column=Column(SAEnum(PaidByType, name="paid_by_type"), nullable=False),
    )
    paid_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    type: PaymentType | None = Field(
        default=None,
        sa_column=Column(SAEnum(PaymentType, name="payment_type"), nullable=True),
    )
    settled_by_payment_id: uuid.UUID | None = Field(default=None, foreign_key="payments.id", nullable=True, index=True)
    confirmed_by: ConfirmedByType | None = Field(
        default=None,
        sa_column=Column(SAEnum(ConfirmedByType, name="confirmed_by_type"), nullable=True),
    )
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
