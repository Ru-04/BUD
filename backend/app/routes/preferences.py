from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app import db
from app.identity import require_owner
from app.schemas import DEFAULT_PREFERENCES, Preferences

router = APIRouter()


@router.get("/api/preferences", response_model=Preferences)
def get_preferences(owner_token_hash: str = Depends(require_owner)):
    saved = db.get_preferences(owner_token_hash)
    return Preferences(**(saved or DEFAULT_PREFERENCES))


@router.put("/api/preferences", response_model=Preferences)
def put_preferences(payload: Preferences, owner_token_hash: str = Depends(require_owner)):
    db.save_preferences(owner_token_hash, payload.model_dump(), datetime.now(timezone.utc).isoformat())
    return payload
