from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlmodel import SQLModel

from app.modules.payments.models import ConfirmedByType, CurrencyType, PaidByType, PaymentMethod, PaymentStatus, PaymentType


class PaymentCreate(SQLModel):
    order_id: UUID
    method: PaymentMethod = PaymentMethod.CASH
    status: PaymentStatus = PaymentStatus.PENDING
    amount: Decimal
    currency: CurrencyType = CurrencyType.USD
    provider_ref: str | None = None
    paid_by: PaidByType
    paid_at: datetime | None = None


class PaymentUpdate(SQLModel):
    method: PaymentMethod | None = None
    status: PaymentStatus | None = None
    amount: Decimal | None = None
    currency: CurrencyType | None = None
    provider_ref: str | None = None
    paid_by: PaidByType | None = None
    paid_at: datetime | None = None

class PaymentRead(SQLModel):
    id: UUID
    method: PaymentMethod
    status: PaymentStatus
    type: PaymentType | None
    amount: Decimal
    currency: CurrencyType
    provider_ref: str | None
    order_id: UUID
    assignment_id: UUID | None
    paid_by: PaidByType
    paid_at: datetime | None
    confirmed_by: ConfirmedByType | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PaymentConfirm(SQLModel):
    confirmed_by: ConfirmedByType
