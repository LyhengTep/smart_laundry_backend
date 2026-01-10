from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.db.init_db import init_db
from app.api.v1.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(lifespan=lifespan,title="Smart Laundry API")


app.include_router(api_router, prefix="/api/v1")
@app.get("/")
def read_root() -> dict[str, str]:
    return {"Hello": "World"}