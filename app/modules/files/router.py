
from fastapi import APIRouter,UploadFile

from app.modules.files import service as svc
from app.modules.files.schema import FileRead

router = APIRouter(prefix="/files", tags=["files"])

@router.post("/", response_model=FileRead)
async def upload_file(file: UploadFile)-> FileRead:
    file = await svc.upload_file(file)

    return file