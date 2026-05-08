from fastapi import UploadFile

from app.lib.aws import upload_upload_file_to_s3
from app.modules.files.schema import FileRead


async def upload_file(file: UploadFile) -> FileRead:
    result = await upload_upload_file_to_s3(file, folder="public", bucket="smart-laundry-198170202285-ap-southeast-1-an")
    return FileRead(url=result["url"], filename=file.filename, path=result["key"])
