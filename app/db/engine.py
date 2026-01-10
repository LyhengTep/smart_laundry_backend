
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.engine import URL

url = URL.create(
    drivername="postgresql+asyncpg",
    username="smart_laundry",
    password="p_JI7F7!|3x>",
    host="localhost",
    port=5432,
    database="smart_laundry",
)


engine = create_async_engine(url, echo=True)