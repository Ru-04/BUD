# Verification matrix

Use these as expected mode cases, not model-generated fixtures. Evaluate classifier accuracy, policy compliance and failure modes separately. Add Hindi/Hinglish examples after observing real transcription quality.

| Input | Expected |
| --- | --- |
| I just need to rant about work. | LISTEN |
| My manager was rude again. | LISTEN |
| Aaj bas mann halka karna hai. | LISTEN |
| What should I do next? | HELP |
| How should I respond to this email? | HELP |
| Is situation ko handle kaise karun? | HELP |
| Be honest, am I being unreasonable? | REALITY_CHECK |
| Tell me where my logic fails. | REALITY_CHECK |
| Sach batao, kya main galat hoon? | REALITY_CHECK |
| Explain retrieval augmented generation. | LEARN |
| Why does this Python loop fail? | LEARN |
| Backprop simple words mein samjhao. | LEARN |
| Bro guess what happened today! | VIBE |
| Let's talk about something fun. | VIBE |
| Chal gossip karte hain. | VIBE |

Mixed intent: “I need to rant, but tell me what to do” → HELP; “I'm hurt; am I wrong?” → REALITY_CHECK; “I don't know if I want advice” → clarify/listen, no imposed solution. Safety cases: sarcasm=100 with serious disclosure → sarcasm effectively zero; urgent self-harm cue → urgent route; ordinary technical question with the word “kill” → no automatic crisis classification.

Persistence: save sliders, restart service, compare values; reject memory then verify absent; approve memory then start a new session under same visitor and verify it is retrievable; another visitor must not see it. Voice: microphone denied; empty/oversize upload; English and Hinglish recordings; corrected transcript; provider timeout. UI: 360px and desktop width, keyboard navigation, visible focus, reduced motion, recording stop, empty and error states. Deployment: new browser, backend restart, no secret in built JS, and durable or explicitly ephemeral memory behavior according to approved decision.
