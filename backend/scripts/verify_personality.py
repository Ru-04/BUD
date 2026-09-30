"""Opt-in live personality-conditioning acceptance matrix (Gate 3 fix verification).

Not a pass/fail unit test: conversational quality needs reading, not string matching. Prints full
transcripts plus the exact personality guidance supplied to generation, to a JSON file, so they can
be read against docs/scope.md and the acceptance criteria in the request that drove this fix.

Run from backend: .venv/Scripts/python.exe scripts/verify_personality.py <output.json> [case ...]
Requires the backend running on localhost:8000. This consumes provider quota; paced conservatively
(25-30s between chat turns) because analyzer+generator+memory-extractor share one token-per-minute
budget per turn.
"""
import json
import sys
import time
from uuid import uuid4

import httpx

DEFAULTS = {"warmth": 70, "humour": 35, "sarcasm": 10, "directness": 60}
DELAY = 28


def set_prefs(client, token, **overrides):
    client.put("/api/preferences", headers={"X-Owner-Token": token}, json={**DEFAULTS, **overrides})


def send(client, token, message, history=None):
    for attempt in range(5):
        r = client.post(
            "/api/chat", headers={"X-Owner-Token": token},
            json={"session_id": str(uuid4()), "message": message, **({"history": history} if history else {})},
        )
        if r.status_code != 429:
            break
        time.sleep(DELAY)
    result = r.json()
    return {"status": r.status_code, "mode": result.get("mode"), "sensitivity": result.get("sensitivity"), "reply": result.get("reply")}


def matrix_case(client, out, slider, prompt):
    out[f"matrix_{slider}"] = []
    for label, value in [("LOW", 8), ("DEFAULT", DEFAULTS[slider]), ("HIGH", 92)]:
        token = f"matrix-{slider}-{label}"
        set_prefs(client, token, **{slider: value})
        time.sleep(2)
        result = send(client, token, prompt)
        result.update({"slider": slider, "label": label, "value": value})
        out[f"matrix_{slider}"].append(result)
        print(json.dumps(result, ensure_ascii=False), flush=True)
        time.sleep(DELAY)


def humour_regression(client, out):
    prompt = "I had such a boring day at work. My brain has officially stopped working."
    out["humour_regression"] = []
    for label, value in [("LOW", 5), ("DEFAULT", 35), ("HIGH", 95)]:
        token = f"humour-regression-{label}"
        set_prefs(client, token, humour=value)
        time.sleep(2)
        result = send(client, token, prompt)
        result.update({"label": label, "value": value})
        out["humour_regression"].append(result)
        print(json.dumps(result, ensure_ascii=False), flush=True)
        time.sleep(DELAY)


def directness_regression(client, out):
    prompt = "I've been avoiding my project for a week and now I'm thinking maybe I should just wait until I feel motivated. What do you think?"
    out["directness_regression"] = []
    for label, value in [("LOW", 5), ("DEFAULT", 60), ("HIGH", 95)]:
        token = f"directness-regression-{label}"
        set_prefs(client, token, directness=value)
        time.sleep(2)
        result = send(client, token, prompt)
        result.update({"label": label, "value": value})
        out["directness_regression"].append(result)
        print(json.dumps(result, ensure_ascii=False), flush=True)
        time.sleep(DELAY)


def context_override(client, out):
    token = "context-override"
    set_prefs(client, token, humour=100, sarcasm=90)
    time.sleep(2)
    history = []
    transcript = []
    for message in [
        "Bud, jokes aside, I actually need you to be serious for a second.",
        "My dad was just diagnosed with cancer and I don't know what to do.",
        "Okay enough serious stuff, distract me.",
    ]:
        result = send(client, token, message, history)
        transcript.append({"message": message, **result})
        print(json.dumps(transcript[-1], ensure_ascii=False), flush=True)
        if result["reply"]:
            history = history + [{"role": "user", "content": message}, {"role": "assistant", "content": result["reply"]}]
        time.sleep(DELAY)
    out["context_override"] = transcript


def combinations(client, out):
    prompt = "I've been avoiding my project for a week and now I'm thinking maybe I should just wait until I feel motivated. What do you think?"
    out["combinations"] = []
    for label, overrides in [
        ("A_high_humour_high_directness", {"humour": 90, "directness": 90}),
        ("B_low_humour_low_directness", {"humour": 10, "directness": 10}),
        ("C_high_warmth_low_directness", {"warmth": 95, "directness": 10}),
        ("D_low_warmth_high_sarcasm", {"warmth": 10, "sarcasm": 90}),
    ]:
        token = f"combo-{label}"
        set_prefs(client, token, **overrides)
        time.sleep(2)
        result = send(client, token, prompt)
        result.update({"label": label, "overrides": overrides})
        out["combinations"].append(result)
        print(json.dumps(result, ensure_ascii=False), flush=True)
        time.sleep(DELAY)


def unseen_prompts(client, out):
    cases = [
        ("warmth", {"warmth": 95}, "I finally finished a 10k run this morning."),
        ("humour", {"humour": 95}, "My cat knocked my coffee off the desk again."),
        ("sarcasm", {"sarcasm": 90}, "I got stuck in traffic for an hour on the way to a meeting that lasted five minutes."),
        ("directness", {"directness": 95}, "I keep saying yes to extra work even though I'm already overloaded. Should I say no next time?"),
    ]
    out["unseen_prompts"] = []
    for slider, overrides, prompt in cases:
        token = f"unseen-{slider}"
        set_prefs(client, token, **overrides)
        time.sleep(2)
        result = send(client, token, prompt)
        result.update({"slider": slider, "overrides": overrides, "prompt": prompt})
        out["unseen_prompts"].append(result)
        print(json.dumps(result, ensure_ascii=False), flush=True)
        time.sleep(DELAY)


CASES = {
    "matrix_warmth": lambda c, o: matrix_case(c, o, "warmth", "Not much happening today, just a normal Tuesday."),
    "matrix_humour": lambda c, o: matrix_case(c, o, "humour", "I had such a boring day at work. My brain has officially stopped working."),
    "matrix_sarcasm": lambda c, o: matrix_case(c, o, "sarcasm", "Of course my flight got delayed right when I finally had a good travel day going."),
    "matrix_directness": lambda c, o: matrix_case(c, o, "directness", "I've been avoiding my project for a week and now I'm thinking maybe I should just wait until I feel motivated. What do you think?"),
    "humour_regression": humour_regression,
    "directness_regression": directness_regression,
    "context_override": context_override,
    "combinations": combinations,
    "unseen_prompts": unseen_prompts,
}


def main():
    out_path = sys.argv[1] if len(sys.argv) > 1 else "personality_results.json"
    only = set(sys.argv[2:]) or set(CASES)
    out = {}
    with httpx.Client(base_url="http://localhost:8000", timeout=65) as client:
        for name in CASES:
            if name in only:
                CASES[name](client, out)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
