# Deploying BUD (Gate 6)

Resolved decisions this deployment implements (see `docs/scope.md`'s "Open decisions" for the
full history): host is **Render**, access policy is the existing per-visitor `X-Owner-Token`
mechanism (ships as-is, not replaced by a login), retention is **indefinite** with a visible
in-UI disclosure.

## Architecture

Two Render services, no code changes required beyond what's already in this repo — both the
backend (CORS via `FRONTEND_ORIGIN`) and frontend (`VITE_API_BASE_URL`) already read their
cross-origin config from environment variables:

- **Backend** — a Render **Web Service** (Python), running FastAPI/uvicorn, with a **persistent
  disk** mounted for the SQLite file. Without the disk, every deploy/restart would silently wipe
  all preferences and memories — do not skip this.
- **Frontend** — a Render **Static Site**, built by Vite, served as static files. Render's static
  sites include Node.js at build time, which the Python web service's runtime does not, so this
  is simpler and more standard than trying to build both from one Python service.

## 1. Push this repo to GitHub

Render deploys from a git remote. From the repo root:

```powershell
git init                     # if not already a repo
git add -A
git commit -m "Initial commit"
```

Then create an empty repo on GitHub and push:

```powershell
git remote add origin https://github.com/<you>/<repo>.git
git branch -M main
git push -u origin main
```

`.gitignore` already excludes `backend.env`, `.env`, `node_modules`, `**/dist`, `**/data`, `*.db`
— verify with `git status` before pushing that nothing secret is staged.

## 2. Backend — Render Web Service

New → Web Service → connect the repo.

| Setting | Value |
| --- | --- |
| Root Directory | `backend` |
| Runtime | Python 3 |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |

Environment variables (Render dashboard → Environment):

| Key | Value |
| --- | --- |
| `PYTHON_VERSION` | `3.12.6` (a stable, widely-supported version — this repo's dev venv runs a newer 3.14, but pin to something Render's buildpack is well-tested against rather than the bleeding edge) |
| `GROQ_API_KEY` | your key — mark **Secret** |
| `GROQ_CHAT_MODEL` | `openai/gpt-oss-120b` |
| `GROQ_WHISPER_MODEL` | `whisper-large-v3` |
| `GROQ_TTS_MODEL` | `canopylabs/orpheus-v1-english` |
| `DATABASE_PATH` | `/var/data/bud.db` |
| `FRONTEND_ORIGIN` | the frontend's Render URL — you'll only know this after step 3, so come back and set it, then **manually redeploy** the backend once you have it |

Add a **persistent disk**: Settings → Disks → Add Disk, mount path `/var/data`, 1 GB is plenty for
SQLite at this scale.

Deploy, then confirm: `curl https://<backend>.onrender.com/health` → `{"status":"ok"}`.

## 3. Frontend — Render Static Site

New → Static Site → same repo.

| Setting | Value |
| --- | --- |
| Root Directory | `frontend` |
| Build Command | `npm install && npm run build` |
| Publish Directory | `dist` |

Environment variable (Vite bakes this in **at build time**, so it must be set before the first
build, and the site rebuilt if you change it):

| Key | Value |
| --- | --- |
| `VITE_API_BASE_URL` | the backend's Render URL from step 2, e.g. `https://bud-backend.onrender.com` (no trailing slash) |

Deploy, then go back to step 2 and set the backend's `FRONTEND_ORIGIN` to this site's URL, and
trigger a manual redeploy of the backend so CORS actually allows it.

## 4. Post-deploy verification (do not skip — this is gate evidence, not the deploy itself)

From a genuinely clean browser (private/incognito window, no dev tools pre-open) at the frontend
URL:

1. `view-source:` the page or check Network tab — confirm no `GROQ_API_KEY` or any secret appears
   anywhere in the served HTML/JS (it shouldn't — the key is server-side only, but verify).
2. Send a text message, confirm a reply arrives.
3. Record a voice message ("Let's talk"), confirm it transcribes/sends/speaks.
4. Open Parameters, move a slider, reload the page, reopen Parameters — confirm it persisted.
5. Open a **second** browser (or another private window with a fresh profile, so it gets a new
   `X-Owner-Token`) and confirm it does **not** see the first browser's preferences/memories —
   this is the per-visitor isolation decision actually holding in production, not just locally.
6. Restart the backend service from the Render dashboard (Manual Deploy → same commit, or just
   wait for Render's own periodic restarts on the free tier) and confirm preferences/memories
   **survive** — this is the same restart test Gate 3 did locally, now against the real disk.

## Known free-tier caveat

Render's free Web Service tier spins down after inactivity and takes ~30-60s to wake on the next
request — the first request after idle will be slow/may time out once. This is a Render platform
behavior, not a BUD bug; mention it if demoing live, or upgrade the instance type if the
submission needs to stay warm.
