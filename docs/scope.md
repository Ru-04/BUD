# Scope and decisions

## Product
BUD is a private-feeling, nonjudgmental conversational companion that responds according to what the user needs: listening, practical help, an honest reality check, explanation, or casual chat. It supports typed messages and recorded voice in English/Hinglish. It is not a therapist or crisis service.

## Confirmed
- React/Vite frontend; FastAPI backend; SQLite for sessions, messages, preferences and approved memories; Groq for chat and Whisper transcription; public demo link.
- Five modes: `LISTEN`, `HELP`, `REALITY_CHECK`, `LEARN`, `VIBE`.
- BUD has one consistent personality across every mode: warm, friendly, emotionally perceptive, casual, curious, and capable of humour, teasing and light banter, including user-invited/reciprocal flirting -- never BUD-initiated, and immediately dropped the moment a topic turns serious or sensitivity leaves `normal`. This is a deliberate product decision (user-directed), not scope creep; see `docs/prompts.md` for the mechanism. Modes shape response strategy, not this personality.
- Personality controls: warmth, humour, sarcasm, directness on 0–100 scales. A fifth verbosity slider is postponed. These sliders are Gate 3 scope and layer on top of the per-turn behaviour above once preferences persist; they do not replace it.
- An explicit **Remember this** action is required before a memory becomes long-term.
- Animated voice orb/ripple and polished responsive UI are in scope.
- BUD speaks its replies aloud (Gate 4, user-directed, moved up from stretch goal): Groq's hosted `canopylabs/orpheus-v1-english` (Orpheus), confirmed with the user over the browser's built-in `SpeechSynthesis` and over self-hosting Piper, for expressive human-like speech without new infrastructure. Requires one-time Groq-console terms acceptance by the account owner before it works; not yet live-verified. Piper remains documented as a possible future self-hosted alternative, not the active choice. librosa audio cues remain a stretch goal. Do not describe unverified pieces as shipped.

## Boundaries
- No account linking, model training, diagnosis, emotion certainty, avatars, vector database, RAG, payment, or mobile app.
- Keep raw recording only during transcription/analysis; do not persist it by default. Avoid storing raw transcripts in logs.
- A public link does not establish privacy. The demo must disclose where messages go (Groq) and how long stored data survives.

## Open decisions — ask before implementing dependent work
1. ~~Which public host and storage arrangement?~~ **Resolved (Gate 6, 30 Sep 2026)**: Render, as two services — a Python Web Service for the backend with a persistent disk for the SQLite file, and a Static Site for the built frontend. See `docs/deploy.md` for the exact setup and env vars.
2. ~~Is the demo single-user or separate visitor sessions?~~ **Resolved (Gate 6, 30 Sep 2026)**: the existing `X-Owner-Token` per-visitor isolation (Gate 3) ships as the real production access policy, confirmed by the user rather than replaced with a login/shared-account scheme.
3. ~~Should conversations persist indefinitely, for a fixed period, or only through the demo?~~ **Resolved, then corrected (Gate 6, 30 Sep 2026)**: originally decided as indefinite, matching local behaviour. During actual Render setup it turned out the free Web Service tier doesn't support persistent disks (confirmed live, not assumed) — a paid plan would fix this, but the user explicitly chose to stay free rather than pay. Final policy for this deployment: **best-effort, not guaranteed across restarts** — server-stored preferences/memories may be cleared whenever the free instance restarts or spins down. The in-UI disclosure (`ChatWindow.jsx`'s `.local-note`) was updated to say this plainly rather than the earlier "kept indefinitely" claim, which would have been inaccurate on this hosting tier. See `docs/deploy.md` for the full reasoning and how to upgrade later if durable retention is ever needed.
4. ~~Exact Groq chat and Whisper model IDs and account limits; verify at setup.~~ **Resolved**: chat `openai/gpt-oss-120b` (Gate 2), Whisper `whisper-large-v3` (Gate 4, chosen over `whisper-large-v3-turbo` for better Hindi/Hinglish code-switching accuracy; both confirmed active via `/openai/v1/models`). Account daily token limits were hit during heavy live testing in Gates 2-3 (200k TPD on this tier) — see `tasks.md` Gate 3 for the diagnostic; relevant if usage is heavy during the public demo too.
5. ~~Provide an image of the exact Dribbble reference to specify visual placement precisely.~~ **Resolved (Gate 4/5)**: the user provided a reference link and a screenshot of one section (EternaCloud), and explicitly directed a lighter-touch approach — borrow layout structure (the voice mode's two-column, orb-in-card composition) while deliberately keeping BUD's own palette rather than an exact visual clone. Treated as the final visual direction, not a placeholder pending a more literal screenshot.

## Acceptance
Text input receives a coherent mode-led reply; explicit advice/reality-check requests select the correct mode; sensitive input suppresses sarcasm; preferences survive restart; memory candidate appears without being saved until approval; a second session can recall only approved memory; voice input transcribes English/Hinglish and uses the same chat route; UI indicates idle/listening/thinking/speaking and supports reduced motion; deployed link works from a clean browser with no exposed secrets.
