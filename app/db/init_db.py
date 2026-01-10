
from app.db.engine import engine
from sqlmodel import SQLModel
from app.db import base 

async def init_db() -> None:
    print("Calling initdb")
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)