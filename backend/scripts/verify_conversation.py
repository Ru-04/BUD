"""Opt-in live conversational regression check for BUD's personality/behaviour rules.

This is not a pass/fail unit test: conversational quality needs human (or reviewer-model)
judgement, not just string matching. It prints full transcripts to a JSON file so they can
be read and assessed against docs/scope.md section 1-9 (personality, curiosity, humour,
flirting, seriousness, repair, length). A few cheap automated red flags are still checked
(banned generic-AI phrases, repeated identical BUD questions across turns).

Run from backend: .venv/Scripts/python.exe scripts/verify_conversation.py <output.json>
Requires the backend running on localhost:8000. This consumes provider quota.
"""
import json
import sys
import time
from uuid import uuid4

import httpx

BANNED_PHRASES = [
    "i'm here to support you",
    "is there anything else on your mind",
    "how does that make you feel",
    "i understand that must be",
]


def turn(client, session_id, message, history):
    for attempt in range(4):
        response = client.post("/api/chat", json={"session_id": session_id, "message": message, "history": history})
        if response.status_code != 429:
            break
        time.sleep(20 * (attempt + 1))
    result = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
    reply = result.get("reply") or ""
    record = {
        "status": response.status_code, "message": message, "reply": reply,
        "mode": result.get("mode"), "sensitivity": result.get("sensitivity"),
        "flags": [p for p in BANNED_PHRASES if p in reply.lower()],
    }
    if response.status_code != 200 or not reply:
        return record, None  # signal the caller to stop this conversation, not poison history
    return record, history + [{"role": "user", "content": message}, {"role": "assistant", "content": reply}]


CONVERSATIONS = {
    "greeting": ["Hey"],
    "casual_conversation": ["Not much, just chilling at home today."],
    "distraction_request": ["I don't want to think about work right now, distract me."],
    "joke_banter": ["Tell me a joke.", "That was such a dad joke."],
    "teasing_bud": ["Ngl you're kind of a nerd for an AI."],
    "flirting": ["Can you flirt with me?"],
    "hinglish": ["Yaar aaj bohot bore ho raha hoon, kuch interesting bata na."],
    "curiosity": ["BUD, I hate sea, I'm scared of the ocean."],
    "criticizing_bud_then_repeat_check": [
        "I don't know, just a normal day I guess.",
        "Stop asking what's on my mind all the time, you're being weird.",
        "Anyway. Whatever.",
    ],
    "vulnerable_disclosure": ["I've been feeling really overwhelmed and honestly worthless lately."],
    "explicit_opinion_request": ["Honestly, what do you think, should I quit my job over this mess with my manager?"],
    "playful_to_serious": [
        "Yo BUD what's the most unhinged thing you'd do if you had a body for a day?",
        "Okay but for real, my dad was just diagnosed with cancer and I don't know what to do.",
    ],
    "serious_to_casual": [
        "My dad was just diagnosed with cancer and I don't know what to do.",
        "Thanks for listening. Anyway, guess what, I got a new puppy today!",
    ],
}


def main():
    out_path = sys.argv[1] if len(sys.argv) > 1 else "conversation_results.json"
    only = set(sys.argv[2:]) or None
    results = {}
    with httpx.Client(base_url="http://localhost:8000", timeout=65) as client:
        for label, messages in CONVERSATIONS.items():
            if only and label not in only:
                continue
            session_id = str(uuid4())
            history = []
            transcript = []
            for message in messages:
                result, next_history = turn(client, session_id, message, history)
                transcript.append(result)
                if next_history is None:
                    break
                history = next_history
                time.sleep(12)
            results[label] = transcript
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    flagged = {label: t for label, t in results.items() if any(r["flags"] for r in t)}
    print(f"Wrote {out_path}. Conversations with banned-phrase hits: {list(flagged) or 'none'}")


if __name__ == "__main__":
    main()
