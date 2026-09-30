from fastapi import APIRouter, UploadFile

from app.schemas import TranscribeResponse
from app.services.groq import ProviderError
from app.services.transcribe import MAX_AUDIO_BYTES, _content_type_allowed, transcribe

router = APIRouter()


@router.post("/api/transcribe", response_model=TranscribeResponse)
async def post_transcribe(audio: UploadFile):
    content_type = audio.content_type or ""
    if not _content_type_allowed(content_type):
        raise ProviderError("INVALID_REQUEST", "Unsupported audio format. Record from the browser microphone and try again.", 422)
    body = await audio.read()
    if not body:
        raise ProviderError("INVALID_REQUEST", "The recording was empty. Please try again.", 422)
    if len(body) > MAX_AUDIO_BYTES:
        raise ProviderError("INVALID_REQUEST", "The recording is too long. Keep it under a couple of minutes.", 413)
    transcript, language = await transcribe(body, audio.filename or "recording", content_type)
    return TranscribeResponse(transcript=transcript, language=language)
