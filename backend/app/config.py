import os
from pathlib import Path

from dotenv import load_dotenv

# Explicit local paths; process environment, then backend.env, then backend/.env.
ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / "backend.env", override=False)
load_dotenv(ROOT / "backend" / ".env", override=False)


def groq_config() -> tuple[str, str]:
    return os.getenv("GROQ_API_KEY", "").strip(), os.getenv("GROQ_CHAT_MODEL", "").strip()


def groq_whisper_config() -> tuple[str, str]:
    return os.getenv("GROQ_API_KEY", "").strip(), os.getenv("GROQ_WHISPER_MODEL", "").strip()


def groq_tts_config() -> tuple[str, str]:
    return os.getenv("GROQ_API_KEY", "").strip(), os.getenv("GROQ_TTS_MODEL", "").strip()
