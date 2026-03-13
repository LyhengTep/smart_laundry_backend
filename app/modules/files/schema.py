



from sqlmodel import SQLModel


class FileRead(SQLModel):
    url: str
    filename: str
    