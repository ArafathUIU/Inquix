import os
import uuid
import aiofiles
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.config import settings
from app.services.extraction import extract_from_audio

router = APIRouter()


@router.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    content_type = file.content_type or ""
    if not (content_type.startswith("audio/") or content_type == "application/octet-stream"):
        raise HTTPException(status_code=400, detail=f"Audio file required, got: {content_type}")

    filename = file.filename or "recording.webm"
    ext = os.path.splitext(filename)[1] or ".webm"
    file_id = str(uuid.uuid4())
    tmp_dir = os.path.join(settings.upload_dir, "tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    file_path = os.path.join(tmp_dir, f"{file_id}{ext}")

    file_bytes = await file.read()
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(file_bytes)

    try:
        text, metadata = await extract_from_audio(file_path)
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

    return {"text": text, "language": metadata.get("language", "en")}
