from datetime import datetime, time, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.modules.businesses.models import LaundryBusiness, ShopStatus
from app.modules.users.models import User
from app.shared.common import RoleName, UserStatus
from app.shared.passwords import hash_password


SHOP_NAME_PREFIXES = [
    "FreshSpin",
    "QuickFoam",
    "CloudCare",
    "BlueBubble",
    "CleanNest",
    "BrightWash",
    "UrbanRinse",
    "SnowDrop",
    "PrimePress",
    "DailySteam",
]

SHOP_NAME_SUFFIXES = [
    "Laundry",
    "Express",
    "Care",
    "Hub",
    "Center",
    "Station",
]

SHOP_STREETS = [
    "Street 271",
    "Russian Blvd",
    "Street 2004",
    "Monivong Blvd",
    "Mao Tse Toung Blvd",
    "Street 51",
    "Street 360",
    "Norodom Blvd",
    "Street 310",
    "Hun Sen Blvd",
]

SHOP_DISTRICTS = [
    "Chamkar Mon",
    "Tuol Kork",
    "Sen Sok",
    "Boeng Keng Kang",
    "Russey Keo",
    "Dangkao",
]

SHOP_STATUSES = [
    ShopStatus.OPEN,
    ShopStatus.OPEN,
    ShopStatus.OPEN,
    ShopStatus.APPROVED,
    ShopStatus.CLOSED,
]


def build_mock_businesses(count: int = 60) -> list[dict]:
    businesses: list[dict] = []
    base_lat = 11.5564
    base_lng = 104.9282

    for index in range(1, count + 1):
        prefix = SHOP_NAME_PREFIXES[(index - 1) % len(SHOP_NAME_PREFIXES)]
        suffix = SHOP_NAME_SUFFIXES[(index - 1) % len(SHOP_NAME_SUFFIXES)]
        street = SHOP_STREETS[(index - 1) % len(SHOP_STREETS)]
        district = SHOP_DISTRICTS[(index - 1) % len(SHOP_DISTRICTS)]
        status = SHOP_STATUSES[(index - 1) % len(SHOP_STATUSES)]

        businesses.append(
            {
                "name": f"{prefix} {suffix} {index}",
                "address": f"{street}, {district}, Phnom Penh",
                "phone": f"+8552390{1000 + index:04d}",
                "latitude": round(base_lat + ((index % 12) * 0.0043), 6),
                "longitude": round(base_lng - ((index % 10) * 0.0061), 6),
                "profile_image_url": None,
                "cover_image_url": None,
                "business_license_number": f"BL-PP-{index:04d}",
                "open_time": time(6 + (index % 3), 0 if index % 2 == 0 else 30),
                "close_time": time(20 + (index % 3), 0 if index % 4 else 30),
                "status": status,
                "rating_avg": round(3.8 + ((index % 12) * 0.1), 1),
            }
        )

    return businesses


MOCK_BUSINESSES = build_mock_businesses()


async def seed_businesses(session: AsyncSession) -> int:
    existing = (await session.execute(select(LaundryBusiness).limit(1))).first()
    if existing:
        return 0

    created = 0
    now = datetime.now(timezone.utc)

    for index, business_data in enumerate(MOCK_BUSINESSES, start=1):
        owner = User(
            full_name=f"Merchant {index}",
            email=f"merchant{index}@example.com",
            user_name=f"merchant{index}",
            phone=f"+85597{8000000 + index}",
            status=UserStatus.ACTIVE,
            password_hash=hash_password("123"),
            role=RoleName.MERCHANT,
            created_at=now,
            updated_at=now,
        )
        session.add(owner)
        await session.flush()

        business = LaundryBusiness(
            owner_id=owner.id,
            name=business_data["name"],
            address=business_data["address"],
            phone=business_data["phone"],
            latitude=business_data["latitude"],
            longitude=business_data["longitude"],
            profile_image_url=business_data["profile_image_url"],
            cover_image_url=business_data["cover_image_url"],
            business_license_number=business_data["business_license_number"],
            open_time=business_data["open_time"],
            close_time=business_data["close_time"],
            status=business_data["status"],
            rating_avg=business_data["rating_avg"],
            created_at=now,
            updated_at=now,
        )
        session.add(business)
        created += 1

    await session.commit()
    print(f"{created} laundry businesses has auto created")
    return created
