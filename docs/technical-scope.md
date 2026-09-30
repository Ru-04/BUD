# BUD technical scope — implementation baseline

Status: specification only. Do not mark capabilities implemented from this document. Confirm the decisions in `scope.md` before public deployment.

## System boundary

React/Vite captures typed text or a browser recording, shows the conversation, the voice orb and four personality controls. FastAPI owns validation, Groq calls, routing, policy, persistence and optional audio output. The browser never receives a provider secret. SQLite stores visitor-isolated sessions/messages/preferences and only explicitly approved long-term memories. The deployment must provide HTTPS, durable storage if durable memory is promised, and visitor isolation.

## Required request flow

1. Browser starts or restores an isolated visitor context and session.
2. Text goes directly to `/api/chat`. Voice recording goes to `/api/transcribe`, then its editable transcript goes to the same `/api/chat` path.
3. Server validates payload, checks sensitive/urgent content, loads recent turns and approved memories, classifies the latest intent into one of five modes, and validates the structured result.
4. Deterministic policy applies safety, mode rules and effective personality settings in that priority order. Groq generates one response; server stores the successful exchange and returns reply, mode and optional memory candidate.
5. A candidate memory is proposed for human approval. Only the approval endpoint makes it an approved memory. The user can delete approved memories.

## Components and completion checks

| Component | Required behavior | Proof |
| --- | --- | --- |
| Health and configuration | Backend starts, restricted CORS, secrets only server-side | UI health call; inspect built JS for key |
| Chat | Typed message gets a reply and a persisted session turn | End-to-end request and restart check |
| Safety | Urgent/sensitive handling overrides style | Sensitive and urgent cases in `test-cases.md` |
| State analyzer | Strict JSON enum; ambiguity handled; invalid output falls back | Five-mode and malformed-output tests |
| Response policy | Five mode constraints; 0–100 slider translation and clamps | Unit tests plus response samples |
| Storage | Session isolation; approved memories; CRUD for settings | Two-visitor test, approval/rejection/deletion, restart |
| Voice input | Browser mic to Groq Whisper; English/Hinglish transcript | Recorded cases plus denial/timeout handling |
| UI | Dark reference-inspired layout, responsive orb/ripple, accessible controls | Desktop/mobile review and reduced-motion test |
| Deployment | Public HTTPS link; no shared visitor data; declared retention | Clean-browser run and backend restart test |

## Optional after required gates

Piper WAV generation/playback, then librosa measurements relative to a baseline. An isolated optional failure must not break chat or voice transcription. No diagnosis from voice features. No auth system, avatar, RAG, vector DB, model training, or extra dashboards.

## Contract and source map

`api-contracts.md` defines routes; `prompts.md` defines analyzer and mode policy; `architecture.md` defines service boundaries and tables; `test-cases.md` defines acceptance cases; `ui-direction.md` defines visual behavior; `deployment.md` defines release checks. If an implementation changes a contract, update its document and tests in the same gate.
