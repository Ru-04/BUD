from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Response

from app import db
from app.identity import require_owner
from app.schemas import ApproveResponse, MemoryItem, RejectResponse
from app.services.groq import ProviderError

router = APIRouter()


@router.post("/api/memory-candidates/{candidate_id}/approve", response_model=ApproveResponse)
def approve(candidate_id: UUID, owner_token_hash: str = Depends(require_owner)):
    memory_id = db.approve_memory_candidate(str(candidate_id), owner_token_hash, datetime.now(timezone.utc).isoformat())
    if memory_id is None:
        raise ProviderError("NOT_FOUND", "Memory candidate not found.", 404)
    return ApproveResponse(memory_id=memory_id)


@router.post("/api/memory-candidates/{candidate_id}/reject", response_model=RejectResponse)
def reject(candidate_id: UUID, owner_token_hash: str = Depends(require_owner)):
    removed = db.reject_memory_candidate(str(candidate_id), owner_token_hash)
    if not removed:
        raise ProviderError("NOT_FOUND", "Memory candidate not found.", 404)
    return RejectResponse()


@router.get("/api/memories", response_model=list[MemoryItem])
def list_memories(owner_token_hash: str = Depends(require_owner)):
    return db.list_memories(owner_token_hash)


@router.delete("/api/memories/{memory_id}", status_code=204, response_class=Response)
def delete_memory(memory_id: UUID, owner_token_hash: str = Depends(require_owner)):
    removed = db.delete_memory(str(memory_id), owner_token_hash)
    if not removed:
        raise ProviderError("NOT_FOUND", "Memory not found.", 404)
    return Response(status_code=204)
