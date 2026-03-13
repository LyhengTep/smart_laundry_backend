from datetime import datetime

from sqlmodel import SQLModel

from app.modules.laundry_services.model import ServiceEnum


class LaundryServiceRead(SQLModel):
    id: int
    name: ServiceEnum
    code: str
    description: str
    created_at: datetime
    updated_at: datetime



class LaundryServiceWrite(SQLModel):
    name: ServiceEnum
    code: str
    description: str
    