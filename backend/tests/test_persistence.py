import asyncio
import json
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app import db
from app.main import app
from app.schemas import ChatRequest, DEFAULT_PREFERENCES
from app.services.chat import ChatError, chat
from app.services.groq import ProviderError, get_provider
from app.services.policy import _band, effective_sliders


def request(message, **extra):
    return ChatRequest(session_id=uuid4(), message=message, **extra)


class FakeProvider:
    def __init__(self, *outputs):
        self.outputs = list(outputs)
        self.calls = []

    async def complete(self, messages, *, json_mode=False, schema=None):
        self.calls.append((messages, json_mode))
        output = self.outputs.pop(0)
        if isinstance(output, Exception):
            raise output
        return output


def analysis_json(mode="LISTEN", sensitivity="normal", **changes):
    value = dict(
        mode=mode, topic="everyday life", user_intent="casual_chat", tone="neutral",
        emotional_intensity="low", sensitivity=sensitivity, confidence=0.95,
        response_style="conversational", humor_allowed=mode == "VIBE", flirt_allowed=False,
        follow_up_question_needed=False, reality_check_needed=mode == "REALITY_CHECK",
    )
    value.update(changes)
    return json.dumps(value)


def proposal_json(should_propose=True, content="Prefers direct feedback", category="communication_preference"):
    return json.dumps({"should_propose": should_propose, "content": content, "category": category})


# --- db.py -------------------------------------------------------------

def test_init_db_is_idempotent():
    db.init_db()
    db.init_db()


def test_hash_owner_token_is_deterministic_and_distinct():
    assert db.hash_owner_token("token-a") == db.hash_owner_token("token-a")
    assert db.hash_owner_token("token-a") != db.hash_owner_token("token-b")


def test_ensure_session_allows_same_owner_reuse():
    db.init_db()
    session_id = str(uuid4())
    db.ensure_session(session_id, "owner-1", "2026-01-01T00:00:00+00:00")
    db.ensure_session(session_id, "owner-1", "2026-01-01T00:00:01+00:00")  # no error on reuse


def test_ensure_session_rejects_different_owner():
    db.init_db()
    session_id = str(uuid4())
    db.ensure_session(session_id, "owner-1", "2026-01-01T00:00:00+00:00")
    with pytest.raises(db.SessionOwnerMismatch):
        db.ensure_session(session_id, "owner-2", "2026-01-01T00:00:01+00:00")


def test_preferences_absent_then_roundtrip():
    db.init_db()
    assert db.get_preferences("owner-x") is None
    db.save_preferences("owner-x", {"warmth": 80, "humour": 20, "sarcasm": 5, "directness": 90}, "2026-01-01T00:00:00+00:00")
    assert db.get_preferences("owner-x") == {"warmth": 80, "humour": 20, "sarcasm": 5, "directness": 90}


def test_preferences_upsert_overwrites():
    db.init_db()
    db.save_preferences("owner-x", {"warmth": 10, "humour": 10, "sarcasm": 10, "directness": 10}, "t1")
    db.save_preferences("owner-x", {"warmth": 90, "humour": 90, "sarcasm": 90, "directness": 90}, "t2")
    assert db.get_preferences("owner-x")["warmth"] == 90


def test_memory_candidate_lifecycle_approve():
    db.init_db()
    candidate_id = str(uuid4())
    db.create_memory_candidate(candidate_id, "owner-x", "Wants weekly check-ins", "goal", "t0", "t9")
    assert db.get_memory_candidate(candidate_id, "owner-x", "t0") is not None
    memory_id = db.approve_memory_candidate(candidate_id, "owner-x", "t1")
    assert memory_id == candidate_id
    assert db.get_memory_candidate(candidate_id, "owner-x", "t1") is None  # consumed
    memories = db.list_memories("owner-x")
    assert len(memories) == 1 and memories[0]["content"] == "Wants weekly check-ins"


def test_expired_memory_candidate_cannot_be_approved_or_read():
    db.init_db()
    candidate_id = str(uuid4())
    db.create_memory_candidate(candidate_id, "owner-x", "Stale suggestion", None, "t0", "t1")
    assert db.get_memory_candidate(candidate_id, "owner-x", "t2") is None  # t2 > expires_at t1
    assert db.approve_memory_candidate(candidate_id, "owner-x", "t2") is None
    assert db.list_memories("owner-x") == []


def test_memory_candidate_reject_does_not_create_memory():
    db.init_db()
    candidate_id = str(uuid4())
    db.create_memory_candidate(candidate_id, "owner-x", "Some candidate", None, "t0", "t9")
    assert db.reject_memory_candidate(candidate_id, "owner-x") is True
    assert db.list_memories("owner-x") == []
    assert db.reject_memory_candidate(candidate_id, "owner-x") is False  # already gone


def test_delete_memory_only_removes_owned():
    db.init_db()
    candidate_id = str(uuid4())
    db.create_memory_candidate(candidate_id, "owner-x", "Some memory", None, "t0", "t9")
    db.approve_memory_candidate(candidate_id, "owner-x", "t1")
    assert db.delete_memory(candidate_id, "owner-y") is False  # wrong owner
    assert db.delete_memory(candidate_id, "owner-x") is True
    assert db.list_memories("owner-x") == []


def test_two_owners_are_isolated():
    db.init_db()
    db.save_preferences("owner-a", {"warmth": 1, "humour": 1, "sarcasm": 1, "directness": 1}, "t")
    candidate_id = str(uuid4())
    db.create_memory_candidate(candidate_id, "owner-a", "Owner A's memory", None, "t0", "t9")
    db.approve_memory_candidate(candidate_id, "owner-a", "t1")

    assert db.get_preferences("owner-b") is None
    assert db.list_memories("owner-b") == []
    assert db.list_memories("owner-a") != []


def test_data_survives_a_simulated_restart():
    db.init_db()
    db.save_preferences("owner-restart", {"warmth": 42, "humour": 42, "sarcasm": 42, "directness": 42}, "t")
    db.init_db()  # simulates the app calling init_db() again on process restart
    assert db.get_preferences("owner-restart")["warmth"] == 42


# --- effective_sliders() -------------------------------------------------

def test_effective_sliders_defaults_to_proposed_defaults_when_unset():
    assert effective_sliders(None, "LISTEN", "normal") == DEFAULT_PREFERENCES


def test_effective_sliders_sensitive_clamp():
    base = {"warmth": 20, "humour": 90, "sarcasm": 90, "directness": 60}
    result = effective_sliders(base, "LISTEN", "sensitive")
    assert result["warmth"] >= 65 and result["humour"] <= 15 and result["sarcasm"] == 0


def test_effective_sliders_urgent_clamp():
    base = {"warmth": 20, "humour": 90, "sarcasm": 90, "directness": 60}
    result = effective_sliders(base, "LISTEN", "urgent")
    assert result["warmth"] >= 70 and result["humour"] == 0 and result["sarcasm"] == 0


def test_effective_sliders_reality_check_clamp():
    base = {"warmth": 20, "humour": 50, "sarcasm": 50, "directness": 10}
    result = effective_sliders(base, "REALITY_CHECK", "normal")
    assert result["directness"] >= 60 and result["warmth"] >= 50


@pytest.mark.parametrize("value,band", [(0, 0), (24, 0), (25, 1), (49, 1), (50, 2), (74, 2), (75, 3), (100, 3)])
def test_band_boundaries(value, band):
    assert _band(value) == band


# --- chat.py persistence wiring ------------------------------------------

def test_chat_persists_messages_when_owner_token_present():
    db.init_db()
    provider = FakeProvider(analysis_json("VIBE"), "A reply", proposal_json(should_propose=False))
    req = request("Bro guess what happened today!")
    asyncio.run(chat(req, provider, owner_token_hash="owner-1"))
    with db.connection() as conn:
        rows = conn.execute("SELECT role, content FROM messages WHERE session_id = ?", (str(req.session_id),)).fetchall()
    assert [dict(r) for r in rows] == [
        {"role": "user", "content": "Bro guess what happened today!"},
        {"role": "assistant", "content": "A reply"},
    ]


def test_chat_skips_persistence_without_owner_token():
    db.init_db()
    provider = FakeProvider(analysis_json("VIBE"), "A reply")
    req = request("Bro guess what happened today!")
    asyncio.run(chat(req, provider))
    with db.connection() as conn:
        rows = conn.execute("SELECT * FROM messages WHERE session_id = ?", (str(req.session_id),)).fetchall()
    assert rows == []


def test_chat_rejects_session_reused_by_a_different_owner():
    db.init_db()
    session_id = uuid4()
    provider = FakeProvider(analysis_json("VIBE"), "A reply", proposal_json(should_propose=False))
    req = ChatRequest(session_id=session_id, message="Hello")
    asyncio.run(chat(req, provider, owner_token_hash="owner-1"))

    provider2 = FakeProvider()
    req2 = ChatRequest(session_id=session_id, message="Hello again")
    with pytest.raises(ChatError) as error:
        asyncio.run(chat(req2, provider2, owner_token_hash="owner-2"))
    assert error.value.code == "SESSION_OWNER_MISMATCH"
    assert error.value.status == 403
    assert provider2.calls == []  # rejected before any provider call


def test_chat_uses_saved_slider_preferences_in_prompt():
    db.init_db()
    db.save_preferences("owner-1", {"warmth": 90, "humour": 90, "sarcasm": 90, "directness": 90}, "t")
    provider = FakeProvider(analysis_json("VIBE", humor_allowed=True), "A reply", proposal_json(should_propose=False))
    asyncio.run(chat(request("Bro guess what happened today!"), provider, owner_token_hash="owner-1"))
    system = provider.calls[1][0][0]["content"]  # calls[0] is the analyzer; calls[1] is the generator
    assert "HUMOUR: VERY HIGH" in system


def test_chat_includes_approved_memories_in_prompt():
    db.init_db()
    candidate_id = str(uuid4())
    db.create_memory_candidate(candidate_id, "owner-1", "Prefers short, direct answers", "communication_preference", "t0", "t9")
    db.approve_memory_candidate(candidate_id, "owner-1", "t1")
    provider = FakeProvider(analysis_json("LISTEN"), "A reply", proposal_json(should_propose=False))
    asyncio.run(chat(request("Just checking in."), provider, owner_token_hash="owner-1"))
    system = provider.calls[1][0][0]["content"]  # calls[0] is the analyzer; calls[1] is the generator
    assert "Prefers short, direct answers" in system


def test_chat_proposes_memory_candidate_when_extractor_agrees():
    db.init_db()
    provider = FakeProvider(analysis_json("LISTEN"), "Good to know.", proposal_json())
    result = asyncio.run(chat(request("I really prefer direct feedback."), provider, owner_token_hash="owner-1"))
    assert result.memory_candidate is not None
    assert result.memory_candidate.content == "Prefers direct feedback"
    assert db.get_memory_candidate(str(result.memory_candidate.id), "owner-1", "2020-01-01T00:00:00+00:00") is not None


def test_chat_skips_memory_extraction_when_sensitivity_is_not_normal():
    db.init_db()
    provider = FakeProvider(analysis_json("LISTEN", sensitivity="sensitive"), "A gentle reply")
    result = asyncio.run(chat(request("My mother died."), provider, owner_token_hash="owner-1"))
    assert result.memory_candidate is None
    assert len(provider.calls) == 2  # analyzer + generator only, no extractor call


def test_chat_memory_extraction_failure_does_not_break_reply():
    db.init_db()
    provider = FakeProvider(analysis_json("LISTEN"), "A reply", ProviderError("PROVIDER_ERROR", "boom"))
    result = asyncio.run(chat(request("Just checking in."), provider, owner_token_hash="owner-1"))
    assert result.reply == "A reply"
    assert result.memory_candidate is None


# --- preferences routes ---------------------------------------------------

@pytest.fixture
def client():
    with TestClient(app) as value:
        yield value
    app.dependency_overrides.clear()


def test_preferences_requires_owner_token(client):
    response = client.get("/api/preferences")
    assert response.status_code == 422


def test_preferences_get_returns_defaults_when_unset(client):
    response = client.get("/api/preferences", headers={"X-Owner-Token": "visitor-1"})
    assert response.status_code == 200
    assert response.json() == DEFAULT_PREFERENCES


def test_preferences_put_validates_range(client):
    response = client.put(
        "/api/preferences", headers={"X-Owner-Token": "visitor-1"},
        json={"warmth": 101, "humour": 10, "sarcasm": 10, "directness": 10},
    )
    assert response.status_code == 422


def test_preferences_put_then_get_roundtrip(client):
    body = {"warmth": 12, "humour": 34, "sarcasm": 56, "directness": 78}
    put_response = client.put("/api/preferences", headers={"X-Owner-Token": "visitor-1"}, json=body)
    assert put_response.status_code == 200 and put_response.json() == body
    get_response = client.get("/api/preferences", headers={"X-Owner-Token": "visitor-1"})
    assert get_response.json() == body


def test_preferences_are_isolated_between_owners(client):
    client.put("/api/preferences", headers={"X-Owner-Token": "visitor-1"}, json={"warmth": 1, "humour": 1, "sarcasm": 1, "directness": 1})
    response = client.get("/api/preferences", headers={"X-Owner-Token": "visitor-2"})
    assert response.json() == DEFAULT_PREFERENCES


# --- memory routes ---------------------------------------------------------

def test_memory_routes_require_owner_token(client):
    assert client.get("/api/memories").status_code == 422
    assert client.post(f"/api/memory-candidates/{uuid4()}/approve").status_code == 422


def test_approve_unknown_candidate_is_not_found(client):
    response = client.post(f"/api/memory-candidates/{uuid4()}/approve", headers={"X-Owner-Token": "visitor-1"})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_approve_then_list_then_delete_flow(client):
    candidate_id = str(uuid4())
    db.create_memory_candidate(candidate_id, db.hash_owner_token("visitor-1"), "Likes concise answers", "communication_preference", "t0", "t9")

    approve = client.post(f"/api/memory-candidates/{candidate_id}/approve", headers={"X-Owner-Token": "visitor-1"})
    assert approve.status_code == 200 and approve.json()["approved"] is True

    listed = client.get("/api/memories", headers={"X-Owner-Token": "visitor-1"})
    assert len(listed.json()) == 1 and listed.json()[0]["content"] == "Likes concise answers"

    # a different visitor must not see or be able to delete it
    assert client.get("/api/memories", headers={"X-Owner-Token": "visitor-2"}).json() == []
    assert client.delete(f"/api/memories/{candidate_id}", headers={"X-Owner-Token": "visitor-2"}).status_code == 404

    deleted = client.delete(f"/api/memories/{candidate_id}", headers={"X-Owner-Token": "visitor-1"})
    assert deleted.status_code == 204
    assert client.get("/api/memories", headers={"X-Owner-Token": "visitor-1"}).json() == []


def test_reject_removes_candidate_without_creating_memory(client):
    candidate_id = str(uuid4())
    db.create_memory_candidate(candidate_id, db.hash_owner_token("visitor-1"), "Something", None, "t0", "t9")
    response = client.post(f"/api/memory-candidates/{candidate_id}/reject", headers={"X-Owner-Token": "visitor-1"})
    assert response.status_code == 200 and response.json()["rejected"] is True
    assert client.get("/api/memories", headers={"X-Owner-Token": "visitor-1"}).json() == []


def test_chat_route_accepts_owner_token_header(client):
    app.dependency_overrides[get_provider] = lambda: FakeProvider(analysis_json("LISTEN"), "Hi there", proposal_json(should_propose=False))
    response = client.post(
        "/api/chat", headers={"X-Owner-Token": "visitor-1"},
        json={"session_id": str(uuid4()), "message": "Hello"},
    )
    assert response.status_code == 200
    assert response.json()["reply"] == "Hi there"
