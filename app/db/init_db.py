import os

from app.db.engine import engine
from sqlmodel import SQLModel
from app.db import base


async def init_db() -> None:
    if os.getenv("DB_INIT_STRATEGY", "migrate") != "create_all":
        return

    print("Calling initdb")
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
