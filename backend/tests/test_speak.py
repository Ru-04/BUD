import asyncio
import io
import struct
import wave

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.groq import ProviderError
from app.services.speak import MAX_CHARS, speak, split_for_speech


def make_wav(seconds_of_silence=1, framerate=8000):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(framerate)
        writer.writeframes(b"\x00\x00" * framerate * seconds_of_silence)
    return buf.getvalue()


def make_streaming_wav(seconds_of_silence=1, framerate=8000):
    """Mimics Groq's real Orpheus responses: the data-chunk size in the header is a placeholder
    (2**31 - 1, a streaming-response sentinel), not the real length -- the audio bytes themselves
    are complete and correct, only the declared size lies. Byte offset 40 is the data-chunk size
    field in the canonical 44-byte PCM header `wave` writes (no extra chunks)."""
    clip = bytearray(make_wav(seconds_of_silence, framerate))
    struct.pack_into("<L", clip, 40, 2**31 - 1)
    return bytes(clip)


@pytest.fixture
def client():
    with TestClient(app) as value:
        yield value


@pytest.fixture
def configured(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key-not-real")
    monkeypatch.setenv("GROQ_TTS_MODEL", "canopylabs/orpheus-v1-english")


# --- split_for_speech: pure chunking logic -----------------------------------

def test_short_text_is_a_single_chunk():
    assert split_for_speech("Hello there.") == ["Hello there."]


def test_empty_text_produces_no_chunks():
    assert split_for_speech("   ") == []


def test_chunks_never_exceed_the_character_limit():
    long_text = " ".join(f"This is sentence number {i} with some extra words to pad it out." for i in range(20))
    chunks = split_for_speech(long_text)
    assert len(chunks) > 1
    assert all(len(chunk) <= MAX_CHARS for chunk in chunks)


def test_a_single_sentence_longer_than_the_limit_is_split_on_words():
    long_sentence = "word " * 80  # ~400 chars, no sentence-ending punctuation at all
    chunks = split_for_speech(long_sentence.strip() + ".")
    assert len(chunks) > 1
    assert all(len(chunk) <= MAX_CHARS for chunk in chunks)
    # Rejoining should reproduce the original words in order, nothing dropped.
    assert " ".join(chunks).split() == (long_sentence.strip() + ".").split()


def test_sentences_are_packed_together_up_to_the_limit_not_one_per_chunk():
    text = "Hi. How are you? I am fine."
    chunks = split_for_speech(text)
    assert chunks == ["Hi. How are you? I am fine."]


# --- speak(): provider call, chunking, and WAV concatenation ----------------

def test_missing_configuration_does_not_call_network(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_TTS_MODEL", raising=False)
    with pytest.raises(ProviderError) as error:
        asyncio.run(speak("Hello"))
    assert error.value.code == "NOT_CONFIGURED"


def test_single_chunk_reply_is_returned_as_is(configured):
    clip = make_wav()

    def respond(req):
        assert req.url.path == "/openai/v1/audio/speech"
        body = req.content
        assert b"canopylabs/orpheus-v1-english" in body
        return httpx.Response(200, content=clip, headers={"content-type": "audio/wav"})

    result = asyncio.run(speak("Hello there.", transport=httpx.MockTransport(respond)))
    assert result == clip


def test_multi_chunk_reply_is_stitched_into_one_playable_wav(configured):
    calls = []

    def respond(req):
        calls.append(req.content)
        return httpx.Response(200, content=make_wav(seconds_of_silence=1), headers={"content-type": "audio/wav"})

    long_text = " ".join(f"This is sentence number {i} with a bit of padding text." for i in range(10))
    result = asyncio.run(speak(long_text, transport=httpx.MockTransport(respond)))
    assert len(calls) > 1  # confirms it was actually split into multiple provider calls

    with wave.open(io.BytesIO(result), "rb") as combined:
        # Each chunk contributed 1 second of audio at 8000Hz; concatenation must sum the frames,
        # not just return the first/last clip.
        assert combined.getnframes() == 8000 * len(calls)


def test_concatenation_survives_orpheus_placeholder_length_header(configured):
    # Regression test for a real bug found via live testing: Groq's actual Orpheus responses
    # declare a placeholder data size (2**31 - 1) rather than the real length. The old code
    # carried that straight into the output header via writer.setparams(first.getparams()),
    # which overflowed the final RIFF size calculation once real multi-chunk data was written --
    # every BUD reply over 200 characters was silently crashing /api/speak. Mocked tests never
    # caught this because they used correctly-sized synthetic WAVs, not this real quirk.
    clip = make_streaming_wav(seconds_of_silence=1)

    def respond(req):
        return httpx.Response(200, content=clip, headers={"content-type": "audio/wav"})

    long_text = " ".join(f"This is sentence number {i} with a bit of padding text." for i in range(10))
    result = asyncio.run(speak(long_text, transport=httpx.MockTransport(respond)))

    with wave.open(io.BytesIO(result), "rb") as combined:
        assert 0 < combined.getnframes() < 2**31, "the placeholder length must not carry through to the output header"


def test_chunks_are_synthesized_concurrently_not_one_at_a_time(configured):
    # Regression test: chunk requests used to be awaited sequentially in a loop, so a multi-chunk
    # reply paid N full network round-trips back to back. Confirms they now overlap in flight.
    in_flight = 0
    max_in_flight = 0

    async def respond(req):
        nonlocal in_flight, max_in_flight
        in_flight += 1
        max_in_flight = max(max_in_flight, in_flight)
        await asyncio.sleep(0.05)
        in_flight -= 1
        return httpx.Response(200, content=make_wav(), headers={"content-type": "audio/wav"})

    long_text = " ".join(f"This is sentence number {i} with a bit of padding text." for i in range(10))
    asyncio.run(speak(long_text, transport=httpx.MockTransport(respond)))
    assert max_in_flight > 1, "chunk requests must overlap in flight, not run one at a time"


@pytest.mark.parametrize("status,code", [(401, "PROVIDER_AUTH"), (403, "PROVIDER_AUTH"), (429, "PROVIDER_RATE_LIMIT"), (500, "PROVIDER_ERROR")])
def test_adapter_sanitizes_provider_errors(configured, status, code):
    transport = httpx.MockTransport(lambda req: httpx.Response(status, text="private provider data"))
    with pytest.raises(ProviderError) as error:
        asyncio.run(speak("Hello", transport=transport))
    assert error.value.code == code
    assert "private" not in error.value.message


def test_adapter_surfaces_model_terms_required_as_an_actionable_error(configured):
    body = {"error": {"message": "The model requires terms acceptance...", "code": "model_terms_required"}}
    transport = httpx.MockTransport(lambda req: httpx.Response(400, json=body))
    with pytest.raises(ProviderError) as error:
        asyncio.run(speak("Hello", transport=transport))
    assert error.value.code == "MODEL_TERMS_REQUIRED"
    assert "console.groq.com" in error.value.message


def test_adapter_timeout(configured):
    def fail(req):
        raise httpx.ReadTimeout("private details", request=req)
    with pytest.raises(ProviderError) as error:
        asyncio.run(speak("Hello", transport=httpx.MockTransport(fail)))
    assert error.value.code == "PROVIDER_TIMEOUT"


# --- route ------------------------------------------------------------------

def test_route_rejects_empty_text(client):
    response = client.post("/api/speak", json={"text": ""})
    assert response.status_code == 422


def test_route_returns_audio_wav(client, configured, monkeypatch):
    clip = make_wav()

    async def fake_speak(text, *, transport=None):
        assert text == "Hi there."
        return clip

    monkeypatch.setattr("app.routes.speak.speak", fake_speak)
    response = client.post("/api/speak", json={"text": "Hi there."})
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"
    assert response.content == clip
