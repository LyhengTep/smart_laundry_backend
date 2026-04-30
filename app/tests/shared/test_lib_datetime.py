from datetime import datetime, timezone

from app.lib.datetime import calulate_remaining_time, utc_now


def test_utc_now_returns_utc_aware_datetime() -> None:
    now = utc_now()
    assert isinstance(now, datetime)
    assert now.tzinfo is not None
    assert now.tzinfo == timezone.utc


def test_calulate_remaining_time_returns_positive_for_future() -> None:
    future = utc_now()
    remaining = calulate_remaining_time(future, expired_in_sec=300)
    assert remaining > 0
    assert remaining <= 300


def test_calulate_remaining_time_returns_zero_for_past() -> None:
    from datetime import timedelta
    past = utc_now() - timedelta(seconds=600)
    remaining = calulate_remaining_time(past, expired_in_sec=300)
    assert remaining == 0
