from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator

Mode = Literal["LISTEN", "HELP", "REALITY_CHECK", "LEARN", "VIBE"]
Sensitivity = Literal["normal", "sensitive", "urgent"]
Intent = Literal["vent", "advice", "information", "distraction", "banter", "reassurance", "flirting", "reality_check", "casual_chat", "other"]
Tone = Literal["neutral", "playful", "excited", "sad", "frustrated", "anxious", "affectionate", "serious", "sarcastic", "curious", "flirty"]
Intensity = Literal["low", "medium", "high"]
ResponseStyle = Literal["short_reaction", "conversational", "detailed"]


class Turn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    session_id: UUID
    message: str = Field(min_length=1, max_length=4000)
    history: list[Turn] = Field(default_factory=list, max_length=12)

    @field_validator("history")
    @classmethod
    def validate_history(cls, turns):
        if len(turns) % 2 or any(
            turn.role != ("user" if index % 2 == 0 else "assistant")
            for index, turn in enumerate(turns)
        ):
            raise ValueError("History must contain completed user/assistant pairs")
        if sum(len(turn.content) for turn in turns) > 24000:
            raise ValueError("History is too long")
        return turns


class Analysis(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    mode: Mode
    topic: str = Field(min_length=1, max_length=160)
    user_intent: Intent
    tone: Tone
    emotional_intensity: Intensity
    sensitivity: Sensitivity
    confidence: float = Field(ge=0, le=1, allow_inf_nan=False)
    response_style: ResponseStyle
    humor_allowed: StrictBool
    flirt_allowed: StrictBool
    follow_up_question_needed: StrictBool
    reality_check_needed: StrictBool


class MemoryProposal(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    should_propose: StrictBool
    content: str = Field(max_length=300)
    category: str = Field(max_length=60)


class MemoryCandidate(BaseModel):
    id: UUID
    content: str
    category: str | None = None


class ChatResponse(BaseModel):
    reply: str
    mode: Mode
    sensitivity: Sensitivity
    memory_candidate: MemoryCandidate | None = None


class Preferences(BaseModel):
    model_config = ConfigDict(extra="forbid")
    warmth: int = Field(ge=0, le=100)
    humour: int = Field(ge=0, le=100)
    sarcasm: int = Field(ge=0, le=100)
    directness: int = Field(ge=0, le=100)


DEFAULT_PREFERENCES = {"warmth": 70, "humour": 35, "sarcasm": 10, "directness": 60}


class MemoryItem(BaseModel):
    id: UUID
    content: str
    category: str | None = None
    approved_at: str


class ApproveResponse(BaseModel):
    memory_id: UUID
    approved: bool = True


class RejectResponse(BaseModel):
    rejected: bool = True


class TranscribeResponse(BaseModel):
    transcript: str
    language: str


class SpeakRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    text: str = Field(min_length=1, max_length=4000)
