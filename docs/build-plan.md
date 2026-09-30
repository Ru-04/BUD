# Build plan (IST, target: ready before 1 October 2026)

The available build windows depend on the user's work schedule. Use gate completion, not assumed clock availability; reserve 1 October for verification/submission. Confirm the challenge's actual submission time in the current portal.

| Date | Gate | Time box | Exit evidence |
| --- | --- | --- | --- |
| 29 Sep | G1 foundation | 1–2 h | `/health` from UI; browser console clean |
| 29 Sep | G2 text brain | 3–4 h | Groq text turn; mode/safety/policy test matrix |
| 29 Sep–30 Sep | G3 persistence | 2–3 h | preferences and approved memory survive restart |
| 30 Sep | G4 voice input | 2–3 h | recorded English/Hinglish turn transcribes and replies |
| 30 Sep | G5 premium UI | 2–3 h | desktop/mobile screenshots; active ripple; reduced-motion check |
| 30 Sep | G6 deploy | 2–3 h | clean-browser public link, persistence and isolation checks |
| 1 Oct | Final QA/demo | reserve | recorded walkthrough and submission, no new core features |

At each gate: run tests; start the app; list changed files, actual output and unresolved issues. If delayed, protect text brain, voice input, preferences, approved memory, and UI. Cut librosa first, then Piper. Never cut deployment validation for a promised public link.

Demo script: open a fresh session; vent to show LISTEN; ask “Am I being unreasonable?” to show REALITY_CHECK; adjust directness/humour; approve a proposed preference memory; start a second session in the same owner context; show recall. Record a voice turn and the UI state changes. Avoid scripted claims about unimplemented components.
