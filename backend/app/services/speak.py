import io
import re
import wave

import httpx

from app.config import groq_tts_config
from app.services.groq import ProviderError

MAX_CHARS = 200  # Groq's documented Orpheus input limit; longer text must be split.
DEFAULT_VOICE = "autumn"


def split_for_speech(text: str) -> list[str]:
    """Greedily groups sentences into <=200-char chunks, splitting long sentences on words."""
    text = text.strip()
    if not text:
        return []
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        candidate = f"{current} {sentence}".strip() if current else sentence
        if len(candidate) <= MAX_CHARS:
            current = candidate
            continue
        if current:
            chunks.append(current)
        if len(sentence) <= MAX_CHARS:
            current = sentence
            continue
        current = ""
        for word in sentence.split(" "):
            candidate = f"{current} {word}".strip() if current else word
            if len(candidate) <= MAX_CHARS:
                current = candidate
            else:
                if current:
                    chunks.append(current)
                current = word
    if current:
        chunks.append(current)
    return chunks


async def _speak_chunk(client: httpx.AsyncClient, key: str, model: str, text: str) -> bytes:
    try:
        response = await client.post(
            "https://api.groq.com/openai/v1/audio/speech",
            headers={"Authorization": f"Bearer {key}"},
            json={"model": model, "input": text, "voice": DEFAULT_VOICE, "response_format": "wav"},
        )
    except httpx.TimeoutException:
        raise ProviderError("PROVIDER_TIMEOUT", "BUD's provider took too long. Please try again.", 504) from None
    except httpx.RequestError:
        raise ProviderError("PROVIDER_UNAVAILABLE", "BUD could not reach its provider. Please try again.", 502) from None
    if response.status_code == 429:
        raise ProviderError("PROVIDER_RATE_LIMIT", "The provider is busy or its quota is reached. Try again later.", 429)
    if response.status_code in (401, 403):
        raise ProviderError("PROVIDER_AUTH", "The backend Groq credentials need checking.", 503)
    if response.status_code == 400:
        try:
            code = response.json().get("error", {}).get("code")
        except (ValueError, AttributeError):
            code = None
        if code == "model_terms_required":
            raise ProviderError(
                "MODEL_TERMS_REQUIRED",
                "The TTS model needs one-time terms acceptance in the Groq console "
                "(console.groq.com/playground) before it can be used.",
                503,
            )
    if response.status_code >= 400:
        # Never expose the provider response: it may echo request content or configuration.
        raise ProviderError("PROVIDER_ERROR", "The provider rejected the request. Please try again.")
    return response.content


def _concatenate_wav(clips: list[bytes]) -> bytes:
    if len(clips) == 1:
        return clips[0]
    readers = [wave.open(io.BytesIO(clip), "rb") for clip in clips]
    try:
        out = io.BytesIO()
        writer = wave.open(out, "wb")
        writer.setparams(readers[0].getparams())
        for reader in readers:
            writer.writeframes(reader.readframes(reader.getnframes()))
        writer.close()
        return out.getvalue()
    finally:
        for reader in readers:
            reader.close()


async def speak(text: str, *, transport=None) -> bytes:
    """Splits text into Orpheus's 200-char limit, synthesizes each chunk, and stitches one WAV."""
    key, model = groq_tts_config()
    if not key or not model or model.startswith("SELECT_"):
        raise ProviderError("NOT_CONFIGURED", "Set the backend Groq key and TTS model before speaking.", 503)
    chunks = split_for_speech(text)
    if not chunks:
        raise ProviderError("INVALID_REQUEST", "No text to speak.", 422)
    async with httpx.AsyncClient(timeout=httpx.Timeout(20, connect=5), transport=transport) as client:
        clips = [await _speak_chunk(client, key, model, chunk) for chunk in chunks]
    try:
        return _concatenate_wav(clips)
    except wave.Error:
        raise ProviderError("PROVIDER_INVALID_RESPONSE", "The provider returned an unusable audio clip.") from None
