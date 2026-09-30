"""Deterministic tests for slider -> band -> prompt-text conditioning (see tasks.md Gate 3 personality fix).

These exist because persistence tests alone don't prove sliders influence generation -- see the bug
this fix addresses: humour/sarcasm text used to be gated entirely behind a per-turn contextual flag
that was independent of the slider value, silently erasing the slider regardless of its setting.
"""
import asyncio
import json
from uuid import uuid4

import pytest

from app import db
from app.schemas import Analysis, ChatRequest, DEFAULT_PREFERENCES
from app.services.chat import chat
from app.services.policy import (
    DIRECTNESS_TEXT, HUMOUR_TEXT, MODE_RULES, SARCASM_TEXT, WARMTH_TEXT, _band, response_policy,
)


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
        response_style="conversational", humor_allowed=True, flirt_allowed=False,
        follow_up_question_needed=False, reality_check_needed=mode == "REALITY_CHECK",
    )
    value.update(changes)
    return json.dumps(value)


def analysis(mode="LISTEN", sensitivity="normal", **changes):
    return Analysis.model_validate_json(analysis_json(mode, sensitivity, **changes))


def proposal_json(should_propose=False):
    return json.dumps({"should_propose": should_propose, "content": "", "category": ""})


# --- band assignment is a pure function of the slider value -----------------

@pytest.mark.parametrize("value,band", [(0, 0), (10, 0), (24, 0), (25, 1), (35, 1), (49, 1), (50, 2), (60, 2), (74, 2), (75, 3), (90, 3), (100, 3)])
def test_band_assignment(value, band):
    assert _band(value) == band


def test_each_dimension_has_four_distinct_band_texts():
    for texts in (WARMTH_TEXT, HUMOUR_TEXT, SARCASM_TEXT, DIRECTNESS_TEXT):
        assert len(texts) == 4
        assert len(set(texts)) == 4  # no accidental duplicates


# --- the actual bug: humour/sarcasm must reach the prompt regardless of the --
# --- analyzer's per-turn "is this moment playful" contextual guess ----------

@pytest.mark.parametrize("humor_allowed", [True, False])
def test_humour_band_text_always_reaches_the_prompt_on_normal_sensitivity(humor_allowed):
    prefs = {"warmth": 70, "humour": 90, "sarcasm": 10, "directness": 60}  # HIGH humour slider
    prompt = response_policy("LISTEN", "normal", analysis("LISTEN", humor_allowed=humor_allowed), prefs, [])
    # This is the crux of the fix: the HIGH-humour band text must be present whether or not the
    # analyzer thought this specific turn was already "playful" -- that flag now only adds a
    # hold-back note, it no longer deletes the slider's own instruction.
    assert HUMOUR_TEXT[3] in prompt
    if not humor_allowed:
        assert "hold back on humour" in prompt


def test_humour_slider_low_vs_high_produce_different_prompt_text():
    a = analysis("LISTEN")
    low = response_policy("LISTEN", "normal", a, {"warmth": 70, "humour": 5, "sarcasm": 10, "directness": 60}, [])
    high = response_policy("LISTEN", "normal", a, {"warmth": 70, "humour": 95, "sarcasm": 10, "directness": 60}, [])
    assert HUMOUR_TEXT[0] in low and HUMOUR_TEXT[0] not in high
    assert HUMOUR_TEXT[3] in high and HUMOUR_TEXT[3] not in low


def test_directness_slider_low_vs_high_produce_different_prompt_text():
    a = analysis("HELP")
    low = response_policy("HELP", "normal", a, {"warmth": 70, "humour": 35, "sarcasm": 10, "directness": 5}, [])
    high = response_policy("HELP", "normal", a, {"warmth": 70, "humour": 35, "sarcasm": 10, "directness": 95}, [])
    assert DIRECTNESS_TEXT[0] in low and DIRECTNESS_TEXT[0] not in high
    assert DIRECTNESS_TEXT[3] in high and DIRECTNESS_TEXT[3] not in low


def test_warmth_and_sarcasm_sliders_are_independently_observable():
    """Changing one slider should not silently change another dimension's band text."""
    a = analysis("LISTEN")
    baseline = response_policy("LISTEN", "normal", a, dict(DEFAULT_PREFERENCES), [])
    only_sarcasm_high = response_policy("LISTEN", "normal", a, {**DEFAULT_PREFERENCES, "sarcasm": 95}, [])
    assert WARMTH_TEXT[_band(DEFAULT_PREFERENCES["warmth"])] in only_sarcasm_high  # warmth text unchanged
    assert DIRECTNESS_TEXT[_band(DEFAULT_PREFERENCES["directness"])] in only_sarcasm_high  # directness unchanged
    assert SARCASM_TEXT[3] in only_sarcasm_high and SARCASM_TEXT[3] not in baseline


# --- safety still fully overrides every slider, at any extreme value --------

@pytest.mark.parametrize("sensitivity", ["sensitive", "urgent"])
def test_safety_fully_suppresses_humour_even_at_maximum_sliders(sensitivity):
    a = analysis("LISTEN", sensitivity=sensitivity, humor_allowed=True)
    prefs = {"warmth": 100, "humour": 100, "sarcasm": 100, "directness": 100}
    prompt = response_policy("LISTEN", sensitivity, a, prefs, [])
    for band_text in (HUMOUR_TEXT[3], SARCASM_TEXT[3]):
        assert band_text not in prompt
    assert "No humour, sarcasm, flirting or emoji this reply" in prompt


# --- mode rules bridge to the relevant personality dimension instead of -----
# --- silently overriding it --------------------------------------------------

def test_listen_and_vibe_mode_rules_reference_humour():
    assert "HUMOUR" in MODE_RULES["LISTEN"]
    assert "HUMOUR" in MODE_RULES["VIBE"]


def test_help_and_reality_check_mode_rules_reference_directness():
    assert "DIRECTNESS" in MODE_RULES["HELP"]
    assert "DIRECTNESS" in MODE_RULES["REALITY_CHECK"]


def test_contextual_override_instruction_is_present():
    prompt = response_policy("VIBE", "normal", analysis("VIBE"), {**DEFAULT_PREFERENCES, "humour": 100}, [])
    assert "immediately comply regardless of your humour/sarcasm/directness" in prompt


# --- end-to-end through chat(): saved preferences really do reach the ------
# --- generator system prompt for a fresh, unseen prompt ---------------------

def test_end_to_end_high_humour_preference_reaches_generation_for_an_unseen_prompt():
    db.init_db()
    db.save_preferences("owner-personality", {"warmth": 70, "humour": 95, "sarcasm": 80, "directness": 60}, "t")
    provider = FakeProvider(analysis_json("LISTEN", humor_allowed=True), "reply", proposal_json())
    asyncio.run(chat(request("My internet has been so slow all week, it's driving me up the wall."), provider, owner_token_hash="owner-personality"))
    system = provider.calls[1][0][0]["content"]
    assert HUMOUR_TEXT[3] in system and SARCASM_TEXT[3] in system


def test_end_to_end_low_directness_preference_reaches_generation_for_an_unseen_prompt():
    db.init_db()
    db.save_preferences("owner-personality-2", {"warmth": 70, "humour": 35, "sarcasm": 10, "directness": 5}, "t")
    provider = FakeProvider(analysis_json("HELP"), "reply", proposal_json())
    asyncio.run(chat(request("Should I text my landlord about the noisy neighbours or just let it go?"), provider, owner_token_hash="owner-personality-2"))
    system = provider.calls[1][0][0]["content"]
    assert DIRECTNESS_TEXT[0] in system
