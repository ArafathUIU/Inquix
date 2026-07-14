from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from app.services.tts import text_to_speech

router = APIRouter()


class TTSRequest(BaseModel):
    text: str
    voice: str = ""


@router.post("/tts")
async def synthesize_speech(req: TTSRequest):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Text is required")

    audio = await text_to_speech(req.text)
    if not audio:
        raise HTTPException(status_code=500, detail="TTS generation failed")

    return Response(content=audio, media_type="audio/wav")
