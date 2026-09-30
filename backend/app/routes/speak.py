from fastapi import APIRouter, Response

from app.schemas import SpeakRequest
from app.services.speak import speak

router = APIRouter()


@router.post("/api/speak")
async def post_speak(payload: SpeakRequest):
    audio = await speak(payload.text)
    return Response(content=audio, media_type="audio/wav")
