import httpx

from app.config import groq_whisper_config
from app.services.groq import ProviderError

MAX_AUDIO_BYTES = 10 * 1024 * 1024  # 10MB: comfortably under Groq's own 25MB Whisper limit
ALLOWED_CONTENT_TYPES = {
    "audio/webm", "audio/ogg", "audio/wav", "audio/x-wav", "audio/mp4", "audio/x-m4a", "audio/mpeg",
}

# A short style/context hint, not a vocabulary list -- Groq's transcription `prompt` (<=224 tokens)
# biases the decoder's expectations, which helps with short/ambiguous code-switched audio, a known
# Whisper hallucination trigger. It must never instruct the model to invent or "clean up" words;
# `language` is deliberately left unset so Hinglish isn't forced into a single language.
TRANSCRIPTION_CONTEXT_PROMPT = (
    "This is a casual, natural conversation that may mix English and Hindi (Hinglish) or include "
    "Indian-accented English. Transcribe exactly what is spoken, preserving code-switching and "
    "Romanized Hindi as spoken, without translating or paraphrasing."
)


def _content_type_allowed(content_type: str) -> bool:
    return content_type.split(";")[0].strip().lower() in ALLOWED_CONTENT_TYPES


async def transcribe(audio_bytes: bytes, filename: str, content_type: str, *, transport=None) -> tuple[str, str]:
    """Sends audio straight through to Groq Whisper in memory; never written to disk."""
    key, model = groq_whisper_config()
    if not key or not model or model.startswith("SELECT_"):
        raise ProviderError("NOT_CONFIGURED", "Set the backend Groq key and Whisper model before transcribing.", 503)
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(20, connect=5), transport=transport) as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {key}"},
                data={"model": model, "response_format": "verbose_json", "prompt": TRANSCRIPTION_CONTEXT_PROMPT},
                files={"file": (filename, audio_bytes, content_type)},
            )
    except httpx.TimeoutException:
        raise ProviderError("PROVIDER_TIMEOUT", "BUD's provider took too long. Please try again.", 504) from None
    except httpx.RequestError:
        raise ProviderError("PROVIDER_UNAVAILABLE", "BUD could not reach its provider. Please try again.", 502) from None
    if response.status_code == 429:
        raise ProviderError("PROVIDER_RATE_LIMIT", "The provider is busy or its quota is reached. Try again later.", 429)
    if response.status_code in (401, 403):
        raise ProviderError("PROVIDER_AUTH", "The backend Groq credentials need checking.", 503)
    if response.status_code >= 400:
        # Never expose the provider response: it may echo request content or configuration.
        raise ProviderError("PROVIDER_ERROR", "The provider rejected the audio. Please try again.")
    try:
        body = response.json()
        text = body["text"].strip()
        language = body.get("language") or "unknown"
        if not text:
            raise ValueError()
        return text, language
    except (ValueError, KeyError, TypeError):
        raise ProviderError("PROVIDER_INVALID_RESPONSE", "The provider returned an incomplete response. Please try again.") from None
