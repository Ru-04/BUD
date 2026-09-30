import asyncio

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.groq import ProviderError
from app.services.transcribe import MAX_AUDIO_BYTES, transcribe


@pytest.fixture
def client():
    with TestClient(app) as value:
        yield value


@pytest.fixture
def configured(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key-not-real")
    monkeypatch.setenv("GROQ_WHISPER_MODEL", "whisper-large-v3")


def test_rejects_unsupported_content_type(client):
    response = client.post("/api/transcribe", files={"audio": ("clip.txt", b"not audio", "text/plain")})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_REQUEST"


def test_rejects_empty_recording(client):
    response = client.post("/api/transcribe", files={"audio": ("clip.webm", b"", "audio/webm")})
    assert response.status_code == 422


def test_rejects_oversize_recording(client):
    oversized = b"0" * (MAX_AUDIO_BYTES + 1)
    response = client.post("/api/transcribe", files={"audio": ("clip.webm", oversized, "audio/webm")})
    assert response.status_code == 413


def test_missing_file_is_rejected(client):
    response = client.post("/api/transcribe")
    assert response.status_code == 422


def test_missing_configuration_does_not_call_network(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_WHISPER_MODEL", raising=False)
    with pytest.raises(ProviderError) as error:
        asyncio.run(transcribe(b"fake audio bytes", "clip.webm", "audio/webm"))
    assert error.value.code == "NOT_CONFIGURED"


@pytest.mark.parametrize("status,code", [(401, "PROVIDER_AUTH"), (403, "PROVIDER_AUTH"), (429, "PROVIDER_RATE_LIMIT"), (500, "PROVIDER_ERROR")])
def test_adapter_sanitizes_provider_errors(configured, status, code):
    transport = httpx.MockTransport(lambda req: httpx.Response(status, text="private provider data"))
    with pytest.raises(ProviderError) as error:
        asyncio.run(transcribe(b"fake audio bytes", "clip.webm", "audio/webm", transport=transport))
    assert error.value.code == code
    assert "private" not in error.value.message


def test_adapter_timeout(configured):
    def fail(req):
        raise httpx.ReadTimeout("private details", request=req)
    with pytest.raises(ProviderError) as error:
        asyncio.run(transcribe(b"fake audio bytes", "clip.webm", "audio/webm", transport=httpx.MockTransport(fail)))
    assert error.value.code == "PROVIDER_TIMEOUT"


def test_requests_code_switching_context_without_forcing_a_single_language(configured):
    from urllib.parse import parse_qs

    def respond(req):
        body = req.content.decode("utf-8", errors="ignore")
        assert "Hinglish" in body  # the context prompt is present
        assert "language" not in parse_qs(req.url.query.decode()) and b'name="language"' not in req.content
        return httpx.Response(200, json={"text": "Hi, how are you, ki haal chaal?", "language": "english"})
    text, _ = asyncio.run(transcribe(b"fake audio bytes", "clip.webm", "audio/webm", transport=httpx.MockTransport(respond)))
    assert text == "Hi, how are you, ki haal chaal?"


def test_successful_transcription_returns_text_and_language(configured):
    def respond(req):
        assert req.url.path == "/openai/v1/audio/transcriptions"
        return httpx.Response(200, json={"text": "Hello, how are you?", "language": "english"})
    text, language = asyncio.run(transcribe(b"fake audio bytes", "clip.webm", "audio/webm", transport=httpx.MockTransport(respond)))
    assert text == "Hello, how are you?"
    assert language == "english"


def test_empty_transcript_is_rejected(configured):
    transport = httpx.MockTransport(lambda req: httpx.Response(200, json={"text": "  ", "language": "english"}))
    with pytest.raises(ProviderError, match="incomplete"):
        asyncio.run(transcribe(b"fake audio bytes", "clip.webm", "audio/webm", transport=transport))


def test_route_end_to_end_with_fake_provider(client, monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key-not-real")
    monkeypatch.setenv("GROQ_WHISPER_MODEL", "whisper-large-v3")

    async def fake_transcribe(audio_bytes, filename, content_type, *, transport=None):
        return "Mujhe ek chai chahiye.", "hindi"

    monkeypatch.setattr("app.routes.transcribe.transcribe", fake_transcribe)
    response = client.post("/api/transcribe", files={"audio": ("clip.webm", b"fake audio bytes", "audio/webm")})
    assert response.status_code == 200
    assert response.json() == {"transcript": "Mujhe ek chai chahiye.", "language": "hindi"}
