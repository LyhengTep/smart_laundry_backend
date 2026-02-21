from app.modules.drivers.models import Driver
from app.modules.users.models import User
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from sqlmodel import Session, select

from app.shared.passwords import hash_password



VEHICLE_COLORS = ["Rot", "Blau", "Schwarz", "Weiß"]
VEHICLE_TYPES = ["MOTORCYCLE", "TUK_TUK","E_BIKE"]
async def seed_drivers(session: AsyncSession, n: int = 200) -> int:
    # ✅ prevent seeding twice (simple check)
    existing = (await session.execute(select(Driver).limit(1))).first()
    if existing:
        return 0

    created = 0
    now = datetime.now(timezone.utc)

    for i in range(1, n + 1):
        user = User(
            full_name=f"Driver {i}",
            email=f"driver{i}@example.com",
            user_name=f"driver{i}",
            phone=f"+85596{9000000 + i}",
            status="INACTIVE" if i % 3 == 0 else "ACTIVE",
            password_hash=hash_password("123"),
            role="DRIVER",
            created_at=now,
            updated_at=now,

        )
        session.add(user)
        await session.flush()  # gets user.id

        driver = Driver(
            user_id=user.id,
            id_card_number=str(100000 + i),
            license_number=None if i % 5 == 0 else f"LIC-{i:05d}",
            plate_number=f"PLT-{i:04d}",
            vehicle_color=VEHICLE_COLORS[i % len(VEHICLE_COLORS)],
            vehicle_type=VEHICLE_TYPES[i % len(VEHICLE_TYPES)],
        )
        session.add(driver)
        created += 1

    await session.commit()
    return created