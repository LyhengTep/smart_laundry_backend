from fastapi import FastAPI
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.engine import URL
from sqlmodel import Field,SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession
from contextlib import asynccontextmanager
from app.db.init_db import init_db


class Hero(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    secret_name: str
    age: int | None = None




# async def insert_hero() -> None:
#     async with AsyncSession(engine) as session:
#         hero = Hero(name="Deadpond", secret_name="Dive Wilson", age=30)
#         session.add(hero)
#         await session.commit()




@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    # await insert_hero()
    yield




app = FastAPI(lifespan=lifespan)


@app.get("/")
def read_root() -> dict[str, str]:
    return {"Hello": "World"}


# @app.on_event("startup")
# async def startup_event():
#     async with engine.connect() as conn:
#         await conn.execute(text("SELECT 1"))

# @app.on_event("shutdown")
# async def shutdown_event():
#     print("Shutting down...")
