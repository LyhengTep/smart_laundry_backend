import os
from fastapi import FastAPI
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from sqlmodel import Session
from starlette.staticfiles import StaticFiles
from app.db import engine
from app.db.init_db import init_db
from app.api.v1.router import api_router
from fastapi.middleware.cors import CORSMiddleware
import logging
from pathlib import Path
from app.seeds.driver import seed_drivers
from app.seeds.laundry_serivces import seed_laundry_service


load_dotenv()  # Load environment variables from .env file


logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)



@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    if os.getenv("ENV") == "DEV":
        async with engine.async_session() as session:
            await seed_drivers(session, n=200)
            await seed_laundry_service(session)
    yield


app = FastAPI(lifespan=lifespan,title="Smart Laundry API")
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://ec2-13-229-201-188.ap-southeast-1.compute.amazonaws.com:3000",
]


BASE_DIR = Path(__file__).resolve().parent
PUBLIC_DIR = BASE_DIR / "uploads"

app.mount("/public/uploads", StaticFiles(directory=PUBLIC_DIR), name="public")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")
@app.get("/")
def read_root() -> dict[str, str]:
    return {"Hello": "World"}