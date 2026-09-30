# BUD — session handoff

Written 30 Sep 2026, 05:40 IST. Read this first if you're picking up this project cold — it tells
you exactly where things stand and what to do next, without re-deriving it from git history. Full
evidence for every claim below lives in `tasks.md` (short checklist) and `docs/sprint-tracker.md`
(detailed log); this file is the fast-start summary, not a replacement for either.

## TL;DR

BUD is a voice-first English/Hinglish AI companion (AI Build Challenge 2026 submission, target
30 Sep IST / 1 Oct reserved for QA — **verify the actual portal deadline**, `docs/build-plan.md`'s
dates are estimates). Gates 1-3 are fully verified complete, including live browser confirmation.
**Gate 4 (voice input, full-page UI redesign, BUD speaking replies) is implemented but not closed.**

**The one thing blocking further progress right now**: BUD still doesn't speak, and it's very
likely a **Groq organization mismatch** — see "Current blocker" below. Everything else in Gate 4 is
implemented, tested, and ready for the user's live retest once that's resolved.

## Current blocker (start here)

Text-to-speech (`canopylabs/orpheus-v1-english` via Groq) returns `503 MODEL_TERMS_REQUIRED` from
our backend, even after the user accepted the model's terms in Groq's playground and confirmed it
worked there (they heard and downloaded audio). Re-testing our backend immediately after that
still gets the identical `400 model_terms_required` from Groq directly:

```
{"error":{"message":"The model `canopylabs/orpheus-v1-english` requires terms acceptance.
Please have the org admin accept the terms at
https://console.groq.com/playground?model=canopylabs%2Forpheus-v1-english", ...}}
```

The message explicitly says **"the org admin"** — Groq API keys belong to exactly one
organization, and this key's organization (seen in an earlier rate-limit error today) is
`org_01kwyej3hwfwbv6bne3psd10yn`. The leading hypothesis: the user has more than one Groq
organization and accepted the terms while a *different* org was active in the console than the one
that owns the key in `backend.env`.

**Next step (needs the user, not an agent — it's login-gated)**: in the Groq console, check the
organization switcher / Settings → API Keys to confirm which org owns the key in `backend.env`,
switch to that org if it's not already active, and re-accept the terms at the URL above while that
org is selected. Then ping whoever's continuing this to re-test —
`backend/scripts` has no dedicated script for this, but a one-liner works:

```powershell
cd D:\BUD\backend
.\.venv\Scripts\python.exe -c "import httpx; from app.config import groq_tts_config; key, model = groq_tts_config(); r = httpx.post('https://api.groq.com/openai/v1/audio/speech', headers={'Authorization': f'Bearer {key}'}, json={'model': model, 'input': 'Hi.', 'voice': 'autumn', 'response_format': 'wav'}, timeout=20); print(r.status_code, r.text[:300])"
```

`200` with binary content means it's fixed — restart the backend (see below) and test from the
actual browser at `localhost:5173`.

## Environment / how to resume

Both dev servers were running and healthy as of this handoff (backend `:8000`, Vite `:5173`).
If they've been stopped:

```powershell
# Terminal 1
cd D:\BUD\backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# Terminal 2
cd D:\BUD\frontend
npm.cmd run dev
```

Secrets live in `D:\BUD\backend.env` (gitignored): `GROQ_API_KEY`, `GROQ_CHAT_MODEL`
(`openai/gpt-oss-120b`), `GROQ_WHISPER_MODEL` (`whisper-large-v3`), `GROQ_TTS_MODEL`
(`canopylabs/orpheus-v1-english`). **Restart the backend after any `backend.env` change** — it's
loaded once at import time.

Current test counts (both green): `python -m pytest -q` from `backend/` → **190 passed**;
`npm.cmd test` from `frontend/` → **19 passed**. Run both before trusting anything is still working.

## Gate status

| Gate | Status | Notes |
| --- | --- | --- |
| G1 Foundation | ✅ Verified complete | Live browser-confirmed |
| G2 Text chat + Groq | ✅ Verified complete | Live browser-confirmed; personality layer added and live-tested |
| G3 Persistence + sliders + memory | ✅ Verified complete | Included a user-reported personality-conditioning bug, root-caused and fixed |
| **G4 Voice + full-page redesign + TTS** | 🟡 **Implemented, not closed** | See below and "Current blocker" |
| G5 Visual polish | ⬜ Not started | Needs the exact Dribbble screenshot (still not supplied) |
| G6 Deployment | ⬜ Not started | Hosting/storage/retention decisions still open, see `docs/scope.md` |

## What's in Gate 4 (this is a lot — it grew well beyond the original scope by explicit user direction)

1. **Voice input**: `RecordingPanel.jsx` — real `MediaRecorder` + `AnalyserNode` waveform, working
   Pause/Resume, live timer, 2-minute auto-stop, mic-permission-denial handling. Transcript lands in
   the **editable** composer, never auto-sent (verified by test).
2. **Transcription**: `/api/transcribe` → Groq Whisper `whisper-large-v3`, audio streamed in memory
   (never written to disk). A user-reported Hinglish hallucination ("ki haal chaal" → nonsense) was
   root-caused (no decoder context on short code-switched audio, not a language-forcing bug) and
   fixed with Groq's real `prompt` parameter. **Needs the user's live retest** — no Hindi TTS voice
   exists on this dev machine to verify independently.
3. **A real concurrency bug, found and fixed**: `React.StrictMode` double-invokes effects in dev
   mode; a boolean "cancelled" ref in `RecordingPanel` got reset by the second mount before the
   first mount's `getUserMedia()` resolved, so a stale, orphaned `MediaRecorder` kept recording
   uncontrolled after "Pause" — a real "mic stays live" bug, not cosmetic. Fixed with a monotonic
   generation counter; there's a regression test that renders inside real `StrictMode` to prove it
   (`tests/interaction.test.mjs`). This may also have been corrupting audio quality generally,
   which is a plausible contributing factor to (2)'s Hindi failure.
4. **Full-page voice-first UI redesign** (explicit user direction, not originally in scope for this
   gate): permanent sidebar removed; `BudOrb` is now the central animated voice representation
   (idle/recording/responding, with an entrance zoom-out animation on load); a floating three-action
   band (Write / Let's talk / Parameters); Parameters and account-status content moved into
   on-demand overlays. BUD's existing palette/theme/personality/memory were explicitly preserved
   throughout — this was a frontend-only change, backend untouched.
5. **A real layout bug, found and fixed**: the composer was vertically centered via flex
   `margin: auto` while the action band uses `position: fixed`, so on some viewport heights the
   composer landed directly behind the fixed band (visible in a user screenshot). Fixed by making
   content flow top-down with guaranteed clearance instead of depending on centering.
6. **TTS ("BUD speaks")** — added by explicit user request mid-gate, not originally planned. Engine
   choice (Groq's Orpheus vs. browser `SpeechSynthesis` vs. self-hosting Piper) was confirmed with
   the user rather than assumed, since Piper was the previously-recorded stretch-goal decision.
   Groq's real API was verified via their docs before implementing: `POST /openai/v1/audio/speech`,
   **200-character input limit per call** — `backend/app/services/speak.py` chunks longer replies at
   sentence boundaries and stitches the resulting WAV clips into one file so the frontend always
   gets a single playable clip. Auto-plays after each reply unless muted (header toggle, persisted).
   **This is the piece currently blocked** — see "Current blocker" above. A TTS failure now surfaces
   visibly in the chat UI instead of failing silently (that silence was itself a bug found and fixed
   this session).

## Outstanding live-test checklist for Gate 4 (do not close the gate without these)

From the user, in the actual browser at `localhost:5173`:

1. The exact phrase "Hi, how are you, ki haal chaal?" (the original Hindi failure report)
2. A longer mixed-language (Hinglish) sentence — one short phrase isn't enough signal
3. Plain English voice, plain Hindi voice, Indian-accented mixed speech
4. Microphone permission denial
5. Pause / Resume (should now actually stop capturing — this was the StrictMode bug)
6. Correcting a transcript before sending (confirm it never auto-sends)
7. Text mode via "Write"
8. Parameters overlay (sliders still load/save correctly)
9. Three-dot → "Your space, taking shape" overlay
10. Orb idle vs. responding animation
11. Responsive layout on a narrow/short viewport (confirm the action-band overlap is actually gone)
12. **TTS once the org/terms issue is resolved** — does BUD's voice actually play, does mute work,
    does a long multi-sentence reply play as one continuous clip with no gap at chunk boundaries

## Open decisions still unresolved (see `docs/scope.md` for full detail)

- Public hosting target + persistent storage arrangement — **not decided**.
- Whether the public demo is single-user or per-visitor — local isolation mechanism exists
  (`X-Owner-Token`) but this is a dev default, not a confirmed production policy.
- Data retention duration for a public deployment.
- The exact Dribbble reference screenshot — still never supplied; current UI is an adaptation, not
  a measured replica. Needed before Gate 5's visual-polish pass can target it precisely.
- The Groq org/terms issue above.

## Where to look for more detail

- `tasks.md` — short, checklist-style evidence per gate. Start here for "is X actually verified."
- `docs/sprint-tracker.md` — long-form narrative of every work block, including root-cause
  writeups for every bug mentioned above. This is where the *why* lives.
- `docs/api-contracts.md` — exact request/response shapes for every endpoint, including the
  `/api/speak` chunking behavior and all error codes.
- `docs/architecture.md`, `docs/scope.md`, `docs/prompts.md` — system design, product decisions,
  and the exact analyzer/personality prompt mechanics, respectively.
- `CLAUDE.md` — standing rules for whoever (human or agent) works on this next: don't silently
  substitute models/hosting/storage, treat live/manual checks as required gate evidence (never
  mark something complete from code or automated tests alone), and read the docs above before
  making changes.
