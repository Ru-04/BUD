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

# Holds references to in-flight background memory-extraction tasks so asyncio doesn't garbage
# collect (and silently cancel) them once the request that spawned them has already returned --
# a known asyncio pitfall for fire-and-forget tasks. Tests await this set to observe completion.
_background_tasks: set[asyncio.Task] = set()


class ChatError(ProviderError):
    """A request-level chat error (e.g. session ownership), sharing ProviderError's sanitized envelope."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run_in_background(coro) -> asyncio.Task:
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return task


async def _extract_and_store_memory(provider, message: str, reply: str, memories: list[dict], owner_token_hash: str) -> None:
    # Fire-and-forget, started only after the user's reply has already been sent -- a slow or
    # failed extraction here never adds to the reply's latency. Best-effort by design, same as
    # the old inline behaviour: a failure just means no memory gets proposed this turn.
    try:
        async with asyncio.timeout(8):
            proposal = await propose_memory(provider, message, reply, memories)
    except (TimeoutError, ProviderError):
        return
    if not proposal:
        return
    candidate_id = str(uuid4())
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
    db.create_memory_candidate(candidate_id, owner_token_hash, proposal.content, proposal.category, _now(), expires_at)


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
                        # Surface a candidate a previous turn's background extraction already
                        # found, if one's waiting; otherwise kick off this turn's extraction in
                        # the background so it never delays this reply -- it'll surface next turn.
                        pending = db.get_latest_pending_candidate(owner_token_hash, _now())
                        if pending:
                            memory_candidate = MemoryCandidate(id=pending["id"], content=pending["content"], category=pending["category"])
                        else:
                            _run_in_background(_extract_and_store_memory(provider, request.message, reply, memories, owner_token_hash))
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
