



import shutil

from fastapi import  UploadFile
from pathlib import Path

from app.exceptions.http import create_500
from app.modules.files.schema import FileRead

async def upload_file(file: UploadFile)  -> FileRead:
    try:

        BASE_DIR = Path(__file__).resolve().parent.parent.parent
        print(BASE_DIR)
        file_location = f"{BASE_DIR}/uploads/{file.filename}"
        with open(file_location, "wb+") as buffer:
            shutil.copyfileobj(file.file, buffer)

        url = f"/public/uploads/{file.filename}"
        return FileRead(url=url, filename=file.filename)    
    except Exception as e:
        raise create_500(f"Failed to upload file: {str(e)}")

    