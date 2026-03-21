from uuid import uuid4

from app.modules.business_services import service as business_service_service
from app.modules.business_services.model import PriceType
from app.modules.business_services.schema import BusinessServiceWrite
from app.tests.modules.conftest import FakeAsyncSession, run_async


def test_create_business_service_sets_core_fields() -> None:
    session = FakeAsyncSession()
    data = BusinessServiceWrite(
        business_id=uuid4(),
        service_id=1,
        base_price=2.5,
        pricing_type=PriceType.PER_WEIGHT,
    )

    created = run_async(business_service_service.create_business_service(session, data))

    assert created.business_id == data.business_id
    assert created.service_id == data.service_id
    assert created.base_price == data.base_price
    assert session.commits == 1


def test_create_business_service_bulk_returns_query_result() -> None:
    business_id = uuid4()
    data = [
        BusinessServiceWrite(
            business_id=business_id,
            service_id=1,
            base_price=2.0,
            pricing_type=PriceType.PER_WEIGHT,
        ),
        BusinessServiceWrite(
            business_id=business_id,
            service_id=2,
            base_price=3.0,
            pricing_type=PriceType.PER_ITEM,
        ),
    ]
    session = FakeAsyncSession(exec_results=[[{"service": "result"}]])

    result = run_async(business_service_service.create_business_service_bulk(session, data))

    assert result == [{"service": "result"}]
    assert session.commits == 1
    assert len(session.added) == 2

