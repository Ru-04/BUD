import re

from app.schemas import Sensitivity

# Conservative contextual backstop, not a diagnostic classifier. The structured
# analyzer can raise sensitivity further; it cannot lower these local findings.
URGENT = [
    r"\b(?:i(?:'m| am)?|i will|i want to|i plan to|i might|i am going to)\s+(?:going to\s+)?(?:kill|hurt|harm) myself\b",
    r"\b(?:end my life|take my own life|want to die|planning suicide)\b",
    r"\b(?:i|i've|i have)\s+(?:just\s+)?(?:taken|took|swallowed)\s+(?:too many|a bottle of|all (?:of )?my)\s+(?:pills|tablets|medication)\b",
    r"\b(?:someone|he|she|my partner)\s+(?:is\s+)?(?:attacking|threatening to kill) me\b",
    r"\b(?:i|i'm|i am)\s+(?:cannot breathe|can't breathe|having (?:a heart attack|severe chest pain))\b",
    r"\b(?:main|mai|mujhe)\b.{0,35}\b(?:khud ko maar|jaan dena|marna chahta|marna chahti)\b",
]
SENSITIVE = [
    r"\b(?:my|our)\s+\w+\s+(?:died|passed away)\b",
    r"\b(?:i(?:'m| am| feel)|feeling)\b.{0,15}\b(?:depressed|hopeless|unsafe|overwhelmed|worthless)\b",
    r"\b(?:i was|i've been|i am being|i'm being)\s+(?:abused|assaulted|raped|bullied)\b",
    r"\b(?:my partner|my husband|my wife)\s+(?:hits|hit|hurts|threatens) me\b",
    r"\b(?:self[- ]harm|suicidal|grieving|miscarriage|trauma)\b",
]


def safety_route(message: str) -> Sensitivity:
    text = message.lower().replace("’", "'")
    # Explicit negation alone is not imminent intent. Keep the disclosure sensitive.
    text = re.sub(r"\bi (?:don't|do not) want to (?:die|kill myself)\b", "self-harm disclosure", text)
    if any(re.search(pattern, text) for pattern in URGENT):
        return "urgent"
    if any(re.search(pattern, text) for pattern in SENSITIVE):
        return "sensitive"
    return "normal"


def strongest(*levels: Sensitivity) -> Sensitivity:
    return max(levels, key=("normal", "sensitive", "urgent").index)


URGENT_REPLY = (
    "I'm sorry you're facing this. If you may act on thoughts of harming yourself, "
    "or you are in immediate danger or a medical emergency, call your local emergency number "
    "or go to the nearest emergency department now. If you can, move away from anything "
    "you could use to hurt yourself and contact someone you trust to stay with you. "
    "I'm an AI and can't provide emergency care. Are you safe right now?"
)
