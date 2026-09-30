# Setup and deployment

## Prerequisites
Install Python and Node.js versions supported by the chosen FastAPI/React/Vite dependencies; verify with `python --version` and `node --version` at Gate 1. Obtain a Groq API key and verify the selected model IDs and current quotas in your own account. Use HTTPS for browser microphone access on the public site.

## Local Gate 1 (PowerShell, from D:\BUD)

Verified with Python 3.12.14, Node 24.21.0 and npm 11.19.0. No Groq key is needed for this gate. Use `npm.cmd` if PowerShell blocks `npm.ps1`.

```powershell
python -m venv backend/.venv
cd backend
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

If the Windows `python` alias is unavailable, use an installed interpreter. The exact bootstrap used in this workspace was:

```powershell
& C:/Users/baps/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe -m venv backend/.venv
```

In a second terminal:

```powershell
cd D:/BUD/frontend
npm.cmd ci
npm.cmd run dev
```

Open `http://localhost:5173`. The UI requests `http://localhost:8000/health` and offers a retry button if the request fails or exceeds five seconds. Stop each server with Ctrl+C.

```powershell
cd D:/BUD/backend
.\.venv\Scripts\python.exe -m pytest -q
(Invoke-WebRequest -UseBasicParsing http://localhost:8000/health).Content
cd D:/BUD/frontend
npm.cmd run build
(Invoke-WebRequest -UseBasicParsing http://localhost:5173).StatusCode
```

Backend CORS permits only `http://localhost:5173` by default. To change it, set `$env:FRONTEND_ORIGIN` before starting the backend; the backend does not automatically load a root `.env`. Copy `frontend/.env.example` to `frontend/.env` only to override the public `VITE_API_BASE_URL`, then restart Vite. Never put provider secrets in Vite variables. Root `.env.example` contains future-gate placeholders and is not needed for Gate 1.

## Public link decision gate
Choose hosting, TLS, backend process, secret variables, permitted CORS origin, rate limiting and storage before publishing. A default ephemeral filesystem cannot support the promised long-term memory across restarts. Either provide a persistent volume for SQLite with backup/reset policy or agree to a database change and update scope/contracts. Isolate visitors with a tested owner mechanism. Show a concise data disclosure and reset/delete capability. Use a health check, check deployed frontend/API together, verify microphone permission and clean-browser flow, then test memory after restart.

Piper is optional: package the executable and model only if host CPU/memory/runtime support it. If omitted, show text reply and no speaking state. A browser speech synthesis fallback would change the agreed tech choice and needs approval.

## Gate 2 local configuration and verification

Put `GROQ_API_KEY` and the explicitly chosen `GROQ_CHAT_MODEL` in `D:\BUD\backend.env` (ignored by Git). The loader reads process environment first, then `backend.env`, then `backend/.env`; it never loads example files. Restart Uvicorn after changing configuration. Never put the key in a Vite variable or an example file.

From `D:\BUD\backend`:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
# In a separate terminal with the same working directory:
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts/verify_live.py
```

The live script uses synthetic examples and consumes Groq quota. It checks final modes/safety and a two-turn context exchange over the running API; it is not a browser test or a standalone classifier accuracy measurement. Ordinary automated tests mock provider responses and do not consume quota.

From `D:\BUD\frontend`:

```powershell
npm.cmd run dev
npm.cmd test
npm.cmd run build
```

Open `http://localhost:5173`, type a message, and press Enter or Send. Shift+Enter inserts a newline. Verify the real reply, mode label, a context-dependent follow-up, error handling, and Clear chat. Do not mark the browser demonstration complete from build/HTTP checks alone. Model IDs must be checked against the account's `/openai/v1/models` response, and changed only with user approval.

Provider contract reference: https://console.groq.com/docs/api-reference ; analyzer JSON mode: https://console.groq.com/docs/structured-outputs (JSON mode still requires application schema validation).

## Gate 3 local configuration and verification

SQLite lives at `backend/data/bud.db` by default (gitignored; created automatically on backend startup). Override the path with `$env:DATABASE_PATH` before starting Uvicorn if needed — useful for pointing at a clean file when testing the restart story. No new secrets are required; visitor identity is a client-generated `X-Owner-Token` header (never put a real credential in it).

```powershell
cd D:\BUD\backend
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

To verify preferences/memory survive a restart from the command line (PowerShell), with the backend running:

```powershell
$headers = @{ "X-Owner-Token" = "manual-test-visitor" }
Invoke-RestMethod -Uri http://localhost:8000/api/preferences -Method Put -Headers $headers -ContentType "application/json" -Body '{"warmth":80,"humour":50,"sarcasm":20,"directness":70}'
# Stop Uvicorn (Ctrl+C), start it again, then:
Invoke-RestMethod -Uri http://localhost:8000/api/preferences -Headers $headers
```

The second call must return the same values. From `D:\BUD\frontend`, open `http://localhost:5173`: the Personality panel (under "Check connection") loads and saves the four sliders; sending a message that states a preference or goal should surface a gold "Remember this?" prompt below the chat, and approving it should make it appear under "Remembered" after reopening that panel. Reloading the page must keep the same sliders/remembered items (same browser, same `localStorage`-held token) — do not mark this complete from the build or offline tests alone.

## Gate 4 local configuration and verification

Add `GROQ_WHISPER_MODEL` (verified for this project: `whisper-large-v3`) to `backend.env` alongside the existing chat settings; same loader, same restart-required-after-change rule. No new secret — it reuses `GROQ_API_KEY`. Requires `python-multipart` (now in `requirements.txt`); re-run `pip install -r requirements.txt` after pulling this gate's changes.

```powershell
cd D:\BUD\backend
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

To sanity-check transcription from the command line without a microphone, Windows' built-in text-to-speech can generate a real audio file to upload:

```powershell
Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$synth.SetOutputToWaveFile("$env:TEMP\test_speech.wav")
$synth.Speak("Testing the transcription endpoint.")
$synth.Dispose()
Invoke-RestMethod -Uri http://localhost:8000/api/transcribe -Method Post -Form @{ audio = Get-Item "$env:TEMP\test_speech.wav" }
```

This only exercises English (Windows ships English SAPI voices by default; Hindi requires an additional language pack). From `D:\BUD\frontend`, open `http://localhost:5173` and use the "Let's talk" action: allow microphone access when prompted, speak, use Pause/Resume or Done, and confirm the transcript appears in the composer for you to review or correct before sending — it must never send itself. Test denial (block the mic permission) and a Hinglish recording — do not mark this complete from the build or offline tests alone; live English-only transcription via synthesized speech is not the same as a real browser microphone test in both languages.

### BUD speaking (Orpheus TTS)

Add `GROQ_TTS_MODEL='canopylabs/orpheus-v1-english'` to `backend.env`; same loader, no new secret. **One-time manual step required before this works at all**: the account owner must accept the model's terms by visiting `https://console.groq.com/playground?model=canopylabs%2Forpheus-v1-english` while logged in and accepting — this cannot be done from the command line or by an agent. Until that's done, `/api/speak` returns `503 MODEL_TERMS_REQUIRED` with this same instruction. Once accepted, reloading the frontend and sending any message should play BUD's reply aloud automatically; use the speaker icon in the header to mute/unmute (persisted per-browser). Test: a normal reply is spoken, muting stops future replies from being spoken, and a long reply (multiple sentences) plays as one continuous clip with no audible gap or truncation at the chunk boundaries.
