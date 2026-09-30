import asyncio
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app import db
from app.schemas import ChatResponse, MemoryCandidate
from app.services.groq import ProviderError
from app.services.memory import propose_memory
from app.services.policy import response_policy
from app.services.safety import URGENT_REPLY, safety_route, strongest
from app.services.state import analyze, explicit_mode, unclear

CLARIFY = "Would you like me to just listen, or help you think through what to do next?"


class ChatError(ProviderError):
    """A request-level chat error (e.g. session ownership), sharing ProviderError's sanitized envelope."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def chat(request, provider, owner_token_hash: str | None = None) -> ChatResponse:
    if owner_token_hash:
        try:
            db.ensure_session(str(request.session_id), owner_token_hash, _now())
        except db.SessionOwnerMismatch:
            raise ChatError(
                "SESSION_OWNER_MISMATCH", "This conversation belongs to a different visitor.", 403
            ) from None

    sensitivity = safety_route(request.message)
    memories = db.list_memories(owner_token_hash) if owner_token_hash else []
    preferences = db.get_preferences(owner_token_hash) if owner_token_hash else None

    if sensitivity == "urgent":
        result = ChatResponse(reply=URGENT_REPLY, mode="LISTEN", sensitivity="urgent")
    else:
        history = [turn.model_dump() for turn in request.history]
        try:
            async with asyncio.timeout(55):
                analysis = await analyze(provider, request.message, history)
                if analysis is not None:
                    sensitivity = strongest(sensitivity, analysis.sensitivity)
                if sensitivity == "urgent":
                    result = ChatResponse(reply=URGENT_REPLY, mode="LISTEN", sensitivity="urgent")
                elif analysis is None or analysis.confidence < 0.6 or unclear(request.message):
                    result = ChatResponse(reply=CLARIFY, mode="LISTEN", sensitivity=sensitivity)
                else:
                    mode = explicit_mode(request.message) or analysis.mode
                    reply = await provider.complete([
                        {"role": "system", "content": response_policy(mode, sensitivity, analysis, preferences, memories)},
                        *history,
                        {"role": "user", "content": request.message},
                    ])
                    memory_candidate = None
                    if owner_token_hash and sensitivity == "normal":
                        try:
                            async with asyncio.timeout(8):
                                proposal = await propose_memory(provider, request.message, reply, memories)
                        except TimeoutError:
                            proposal = None
                        if proposal:
                            candidate_id = str(uuid4())
                            expires_at = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
                            db.create_memory_candidate(candidate_id, owner_token_hash, proposal.content, proposal.category, _now(), expires_at)
                            memory_candidate = MemoryCandidate(id=candidate_id, content=proposal.content, category=proposal.category)
                    result = ChatResponse(reply=reply, mode=mode, sensitivity=sensitivity, memory_candidate=memory_candidate)
        except TimeoutError:
            raise ProviderError("PROVIDER_TIMEOUT", "BUD's provider took too long. Please try again.", 504) from None

    if owner_token_hash:
        persisted_at = _now()
        db.save_turns(str(request.session_id), [
            {"id": str(uuid4()), "role": "user", "content": request.message, "mode": None, "created_at": persisted_at},
            {"id": str(uuid4()), "role": "assistant", "content": result.reply, "mode": result.mode, "created_at": persisted_at},
        ])
    return result
