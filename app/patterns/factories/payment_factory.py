



from app.modules.payments.models import Payment, PaymentType
from app.modules.payments.schema import PaymentCreate


def create_initial_payment_factory(data:PaymentCreate)->dict:
        return Payment(
                method=data.method,
                order_id= data.order_id,
                status= data.status,
                amount= data.amount,
                currency=data.currency,
                type="pickup_fee",
                provider_ref= data.provider_ref,
                paid_by= data.paid_by,
                paid_at=data.paid_at
        )
