from datetime import date, datetime, timedelta, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc)



def calulate_remaining_time(assigned_time:date,expired_in_sec:int)->int:
    expire_at = assigned_time+timedelta(seconds=expired_in_sec)

    now = datetime.now(timezone.utc)
    plain_remaining= expire_at - now
    print(f"original timer before {plain_remaining}")
    return round(max(plain_remaining.total_seconds(), 0))
