from app.modules.laundry_services import service as laundry_service
from app.modules.laundry_services.model import ServiceEnum
from app.modules.laundry_services.schema import LaundryServiceWrite
from app.tests.modules.conftest import FakeAsyncSession, run_async


def test_create_laundry_service_persists_service() -> None:
    session = FakeAsyncSession()
    data = LaundryServiceWrite(
        name=ServiceEnum.WASH,
        code="WASH",
        description="Wash service",
    )

    created = run_async(laundry_service.create_laundry_service(data, session))

    assert created.name == ServiceEnum.WASH
    assert created.code == "WASH"
    assert session.commits == 1


def test_list_laundry_services_returns_exec_results() -> None:
    expected = [{"name": "WASH"}]
    session = FakeAsyncSession(exec_results=[expected])

    result = run_async(laundry_service.list_laundry_services(session))

    assert result == expected

