import os
import uuid
import hashlib
import re
import aiofiles
from datetime import datetime
import fitz
from PIL import Image
import pytesseract

from app.config import settings


SOURCE_MIME_MAP = {
    "text/plain": "text",
    "text/markdown": "text",
    "text/x-python": "text",
    "text/html": "text",
    "text/css": "text",
    "text/javascript": "text",
    "text/csv": "text",
    "application/json": "text",
    "application/pdf": "pdf",
    "image/png": "image",
    "image/jpeg": "image",
    "image/jpg": "image",
    "image/gif": "image",
    "image/webp": "image",
    "image/bmp": "image",
    "audio/mpeg": "audio",
    "audio/mp3": "audio",
    "audio/wav": "audio",
    "audio/wave": "audio",
    "audio/x-wav": "audio",
    "audio/mp4": "audio",
    "audio/m4a": "audio",
    "audio/ogg": "audio",
    "audio/webm": "audio",
    "audio/x-m4a": "audio",
}


def detect_source_type(mime_type: str) -> str:
    if mime_type in SOURCE_MIME_MAP:
        return SOURCE_MIME_MAP[mime_type]
    if mime_type.startswith("text/"):
        return "text"
    if mime_type.startswith("image/"):
        return "image"
    if mime_type.startswith("audio/"):
        return "audio"
    return "text"


async def save_upload(kb_id: str, file_content: bytes, filename: str) -> tuple[str, str]:
    file_id = str(uuid.uuid4())
    ext = os.path.splitext(filename)[1] or ""
    safe_filename = f"{file_id}{ext}"
    kb_dir = os.path.join(settings.upload_dir, kb_id)
    os.makedirs(kb_dir, exist_ok=True)
    file_path = os.path.join(kb_dir, safe_filename)

    async with aiofiles.open(file_path, "wb") as f:
        await f.write(file_content)

    return file_path, safe_filename


async def extract_text(file_path: str, source_type: str, filename: str) -> tuple[str, dict]:
    metadata = {"source_type": source_type, "filename": filename}

    if source_type == "text":
        text = await extract_from_text(file_path)
    elif source_type == "pdf":
        text, extra = await extract_from_pdf(file_path)
        metadata.update(extra)
    elif source_type == "image":
        text = await extract_from_image(file_path)
    elif source_type == "audio":
        text, extra = await extract_from_audio(file_path)
        metadata.update(extra)
    else:
        raise ValueError(f"Unsupported source type: {source_type}")

    return text.strip(), metadata


async def extract_from_text(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


async def extract_from_pdf(file_path: str) -> tuple[str, dict]:
    text_parts = []
    page_count = 0

    doc = fitz.open(file_path)
    for page_num, page in enumerate(doc):
        page_text = page.get_text()
        if page_text.strip():
            text_parts.append(page_text)
        page_count += 1
    doc.close()

    return "\n\n".join(text_parts), {"pages": page_count}


async def extract_from_image(file_path: str) -> str:
    image = Image.open(file_path)
    text = pytesseract.image_to_string(image)
    return text


async def extract_from_audio(file_path: str) -> tuple[str, dict]:
    from faster_whisper import WhisperModel

    model = WhisperModel("base", device="cpu", compute_type="int8")
    segments, info = model.transcribe(file_path)

    text_parts = []
    segment_data = []

    for segment in segments:
        text_parts.append(segment.text)
        segment_data.append({
            "start": round(segment.start, 2),
            "end": round(segment.end, 2),
            "text": segment.text.strip(),
        })

    return " ".join(text_parts), {"segments": segment_data, "language": info.language}


def compute_content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
