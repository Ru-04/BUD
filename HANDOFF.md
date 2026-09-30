# BUD — session handoff

Written 30 Sep 2026, 15:25 IST. Read this first if you're picking up this project cold. Full
evidence for every claim below lives in `tasks.md` (checklist per gate); this file is the
fast-start summary.

## TL;DR

BUD is a voice-first English/Hinglish AI companion (AI Build Challenge 2026 submission). **All six
gates are complete and live-verified**, including a real public deployment:

- Frontend: https://bud-frontend.onrender.com/
- Backend: https://bud-backend-w1ka.onrender.com

| Gate | Status |
| --- | --- |
| G1 Foundation | ✅ Verified complete |
| G2 Text chat + Groq | ✅ Verified complete |
| G3 Persistence + sliders + memory | ✅ Verified complete |
| G4 Voice + full-page UI redesign + TTS | ✅ Verified complete |
| G5 Visual polish + accessibility/responsive QA | ✅ Verified complete |
| G6 Public deployment | ✅ Verified complete |

## Environment / how to resume local dev

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

Test counts (both green as of the last run): `python -m pytest -q` from `backend/` → **190
passed**; `npm.cmd test` from `frontend/` → **25 passed**.

## Production deployment (Render, live)

Two services, no shared infrastructure beyond env-var wiring — see `docs/deploy.md` for the full
setup guide and `render.yaml` for a best-effort blueprint:

- **`bud-backend`** — Python Web Service. Free tier: **no persistent disk**, so SQLite data
  (preferences/memories) does **not** survive a restart/spin-down. This was an explicit,
  user-confirmed trade-off (see `docs/scope.md` decision #3) after discovering live that Render's
  free tier doesn't support disks — not a bug, and the in-UI disclosure text says so plainly.
- **`bud-frontend`** — Static Site, built by Vite. `VITE_API_BASE_URL` is baked in at build time,
  so changing it requires a rebuild, not just an env var save.
- CORS is wired via `FRONTEND_ORIGIN` on the backend — **must exactly match** the frontend's
  origin with no trailing slash (a trailing slash caused a real CORS outage during setup; browsers
  never include one in the `Origin` header).
- Free tier also cold-starts after inactivity (~30-60s on first request) — a Render platform
  behavior, not a BUD issue.

Live-verified: health check, CORS preflight, zero secret leakage in the served JS bundle,
per-visitor isolation across two separate browser profiles, and restart-induced data reset
(expected, matches the disclosed retention policy).

## Known, disclosed limitations (not blockers)

- **Hinglish/Hindi TTS and transcription accuracy were never independently verified on the dev
  machine** — no Hindi TTS voice was available locally to generate a synthetic test sample (Gate
  4). The live pipeline works (English verified end-to-end, Hinglish transcription was improved
  with a context-prompt fix per `tasks.md` Gate 4), but true Hindi/Hinglish quality depends on the
  user's own live testing, which happened during Gate 4/6 rather than an automated check.
- **Retention is best-effort on the free Render tier**, not indefinite — disclosed in the UI and
  in `docs/scope.md`. Upgrading to a paid Render plan and adding a persistent disk (see
  `docs/deploy.md`'s "Architecture" section) would restore true indefinite retention if ever
  needed.
- **Daily Groq token quota** was hit during heavy live testing earlier in the project (200k
  TPD on this account's tier, see `tasks.md` Gate 3) — relevant if the public demo sees heavy
  traffic.

## Where to look for more detail

- `tasks.md` — the full checklist-style evidence log per gate, including every bug found and
  fixed, root causes, and exact test counts at each point.
- `docs/deploy.md` — the authoritative Render deployment guide.
- `docs/api-contracts.md`, `docs/architecture.md`, `docs/scope.md`, `docs/prompts.md` — system
  design, product/deployment decisions (including the full history of what was resolved vs.
  corrected), and the exact analyzer/personality prompt mechanics.
- `CLAUDE.md` — standing rules for whoever (human or agent) works on this next.
