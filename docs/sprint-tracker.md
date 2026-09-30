# Sprint and milestone tracker

Target: finish implementation and deployment by **30 Sep 2026 IST**, use **1 Oct** for final QA and submission. These are work blocks, not assumed availability; log actual start/finish times. The deadline time must be verified in the submission portal.

## How to use this tracker

Change a task to `Done` only when its proof column is filled with an observed test or demo result. `Blocked` requires a concrete blocker and owner. Update this file after every work block; keep `tasks.md` as the short gate checklist. Overall progress counts **verified required tasks**, not lines of code or files created.

| ID | Sprint / milestone | Task | Estimate | Status | Proof / blocker |
| --- | --- | --- | --- | --- | --- |
| 1.1 | Sprint 1 · Foundation · 29 Sep | Confirm host, visitor isolation, retention and Groq models | 30–45 min | Blocked | Needs user decisions/account verification |
| 1.2 | Sprint 1 · Foundation · 29 Sep | Bootstrap FastAPI, React/Vite, env and `/health` | 60–90 min | Done | 29 Sep: Python 3.12.14 / Node 24.21.0; Uvicorn and Vite 6.4.3 started; live health 200 with exact JSON; pytest 3 passed; production build passed; no server configuration markers in built JS |
| 1.3 | Sprint 1 · Foundation · 29 Sep | Premium responsive app shell and API connection | 60–90 min | Done | Build and render smoke test passed; user verified page rendering, no console errors, Backend connected, and 360px layout without overlap or horizontal scrolling |
| 2.1 | Sprint 2 · Brain · 29 Sep | Typed chat and Groq adapter | 60–90 min | Done | `openai/gpt-oss-120b`; 93 backend tests pass; live `/api/chat` pipeline verified via `scripts/verify_live.py` and `scripts/verify_conversation.py`. User confirmed browser acceptance at `localhost:5173` 29 Sep 06:42 IST: messages send/receive with no console errors. |
| 2.2 | Sprint 2 · Brain · 29 Sep | Safety route and validated five-mode analyzer | 90–120 min | Done | Strict `json_schema` response format, one retry, malformed fallback, sensitive/urgent overrides covered offline and live; local safety regex hardened (adverb-gap regression). User confirmed modes matched what was typed in the browser. |
| 2.3 | Sprint 2 · Brain · 29 Sep | Deterministic response policy and mode tests | 60–90 min | Done | Personality layer (humour/curiosity/flirting, safety-clamped) plus five mode strategies; verified live across 13 conversational categories. User confirmed personality felt natural, not robotic/repetitive, with seriousness holding for heavier topics. |
| 3.1 | Sprint 3 · Personalization · 29 Sep | SQLite sessions/messages and visitor isolation | 60–90 min | Done | `db.py` + lazy session registration + `SESSION_OWNER_MISMATCH` on hijack, live-verified with real cross-token calls and confirmed in the browser. |
| 3.2 | Sprint 3 · Personalization · 29 Sep | Four sliders, storage and effective overrides | 45–60 min | Done | Personality-conditioning bug found by the user, root-caused and fixed (see below), then user-confirmed live: slider LOW vs HIGH difference clearly observable, panel persists across reload, context override works. 160 offline tests pass including 21 new deterministic personality tests. |
| 3.3 | Sprint 3 · Personalization · 29 Sep | Memory propose/approve/reject/delete and restart checks | 75–120 min | Done | Full propose->approve->list->isolate loop live-verified with real Groq; expiry enforcement bug found and fixed. User confirmed the approve/reject UI works in the browser. |
| 4.1 | Sprint 4 · Voice and UI · 30 Sep | Record/stop/transcribe and English/Hinglish cases | 90–120 min | In progress | `whisper-large-v3` wired end-to-end; user found a live Hinglish hallucination ("ki haal chaal" -> nonsense), root-caused (no decoder context, not a language-forcing bug) and fixed with Groq's real `prompt` parameter. English re-verified live with no regression; Hinglish improvement needs the user's own voice (no Hindi TTS locally). |
| 4.2 | Sprint 4 · Voice and UI · 30 Sep | Full-page voice-first redesign, orb states, mobile, keyboard and reduced motion | 90–150 min | In progress | Permanent sidebar removed; BUD's existing orb is now the central animated `BudOrb` (idle/recording/responding); floating three-action band (Write/Let's talk/Parameters); full waveform+pause/resume recording panel; Parameters and "Your space" overlays replace the sidebar's content. 15/15 frontend tests pass (9 new interaction tests via a new jsdom+RTL harness). Same theme/palette preserved throughout; Dribbble screenshot fidelity remains Gate 5. |
| 5.1 | Sprint 5 · Release · 30 Sep | HTTPS deployment, env/CORS/storage configuration | 60–120 min | Blocked | Hosting/storage choice required |
| 5.2 | Sprint 5 · Release · 30 Sep | Clean-browser, isolation, restart and demo rehearsal | 60–90 min | To do | — |
| 6.1 | Final QA · 1 Oct | Fix release blockers, record demo, submit | Reserved | To do | Verify portal deadline |
| X.1 | Stretch | Piper speech and speaking state | 60–120 min | Deferred | Only after release path works |
| X.2 | Stretch | librosa baseline-based acoustic cues | 60–120 min | Deferred | Only after release path works |

## Milestone exit criteria

- **M1 Foundation:** `/health` visible from frontend; server key absent from client bundle.
- **M2 Brain:** typed chat works; all five representative modes and safety overrides pass.
- **M3 Personalization:** preferences and approved memory survive restart; two visitors are isolated.
- **M4 Voice/UI:** English/Hinglish voice turn works; desktop/mobile and reduced-motion checks pass.
- **M5 Release:** public link works in a clean browser; persistence policy is accurate; demo recorded.

## Progress snapshot (29 Sep, Gate 1 work block)

Gate 1 follow-up: user browser evidence identified `React is not defined` in App.jsx. Added the missing React import and an SVG favicon. Verified `npm.cmd test`: 1 render smoke test passed through Vite's JSX transform; `npm.cmd run build` passed. This render test does not execute browser effects or establish a successful UI health request; user subsequently confirmed browser rendering, no console errors and acceptable appearance at their current viewport. User then explicitly confirmed Backend connected and the 360px layout without overlap or horizontal scrolling. Gate 1 acceptance is complete.

Required implementation tasks verified: **8 / 13** (IDs 1.1-5.2). Gates 1, 2 and 3 are complete, including user-provided browser acceptance evidence for all three. Gate 4 is implemented and partly API-level-verified (see below); Gate 5 onward remain unimplemented. Hosting and production retention/identity-policy decisions remain open (local isolation and restart-survival are now implemented and verified).

## Gate 3 work block (29 Sep 2026, ~06:30-07:10 IST)

Built the full persistence layer in one pass: `backend/app/db.py` (stdlib `sqlite3`, no new dependency, fresh connection per call, schema matching `architecture.md`'s five tables), `identity.py` (owner-token header -> SHA-256 hash), `routes/{preferences,memory}.py`, `services/memory.py` (candidate extractor). `groq.py`'s strict-JSON-schema branch was generalized to accept any Pydantic schema (it was hardcoded to `Analysis`) so the extractor could reuse the same strict-schema path Gate 2 built for the analyzer. `policy.py` gained `effective_sliders()`, implementing the exact sensitive/urgent/REALITY_CHECK clamp formulas and 0-24/25-49/50-74/75-100 banding from `docs/prompts.md`, layered so the existing Gate 2 per-turn humour/flirt safety clamp still wins. `chat.py` was rewritten to thread an optional `owner_token_hash` through: lazy session registration with hijack rejection, atomic turn persistence, preference/memory loading into the prompt, and a time-boxed, failure-tolerant memory-candidate extraction step.

Deliberate deviation from `docs/api-contracts.md`'s original sketch: `/api/sessions` was not built as its own endpoint; session registration happens lazily on first `/api/chat` use of a `session_id` instead, avoiding an extra round-trip before the first message. Documented explicitly in the updated `api-contracts.md`.

Two real bugs found and fixed while building this, not carried over from a prior gate:
1. The `RequestValidationError` handler's message was hardcoded to the `/api/chat` contract wording and returned that same (wrong) message for a missing `X-Owner-Token` header or an out-of-range preference value. Made it path-aware.
2. `memory_candidates.expires_at` was written on creation but never checked anywhere — an "expired" candidate could still be approved indefinitely. Added the expiry filter to the read/approve paths plus a regression test.

Offline: `python -m pytest -q` -> **135 passed** (up from 93; +42 new tests: db lifecycle/isolation/expiry, `effective_sliders` formulas and exact band boundaries, preferences/memory routes including cross-visitor isolation and 404s on unknown/wrong-owner resources, and chat-layer persistence/session-hijack/memory-proposal/extraction-failure-safety). Frontend: `npm.cmd test` -> 2 passed (updated for the new `X-Owner-Token` header); `npm.cmd run build` -> passed, 29 modules.

Live (real backend, real Groq on `openai/gpt-oss-120b`, backend restarted before testing to guarantee current code):
- Preferences: GET returns proposed defaults (70/35/10/60) when unset; PUT+GET round-trips; a second `X-Owner-Token` sees only defaults, never the first visitor's saved values (isolation confirmed); after a **real `taskkill` + fresh `uvicorn` restart** (not an in-process simulation), the first visitor's saved values (`warmth: 85`, etc.) read back unchanged -- genuine restart-survival evidence, not a unit-test simulation.
- Memory: a stated preference ("I really prefer direct, no-fluff feedback") correctly produced a `memory_candidate`; approved it via the live endpoint; confirmed it appears in that visitor's `GET /api/memories` and is absent for a different visitor; started a **new session under the same owner** afterward with no errors. (Whether that memory measurably changed a single live reply's wording is too fuzzy a signal to assert on its own -- the extractor is explicitly told never to make BUD recite memories back -- so the "memory reaches generation" claim rests on a unit test asserting the memory text appears in the system prompt, combined with this live proof that the store/approve/list/isolate mechanics work end-to-end against the real API and real database file.)
- Session hijack: reusing a `session_id` under a second `X-Owner-Token` correctly returned `403 SESSION_OWNER_MISMATCH` with zero provider calls made.
- Message persistence: confirmed by reading the SQLite file directly after both a persisted and a non-persisted (no token) chat turn.

Not live-confirmed: memory extraction being skipped when sensitivity is not `normal`. Attempted twice; both hit Groq's rate limit (`429`, a real quota exhaustion from this session's cumulative live testing across Gates 2 and 3, not an application bug). The skip is a deterministic Python condition (`if owner_token_hash and sensitivity == "normal"`) covered by an offline unit test, but per this project's own evidence rule it is flagged here as outstanding rather than assumed passing.

Remaining Gate 3 blocker, same shape as Gates 1-2: no browser-automation tool this session. The Personality slider panel and the memory approve/reject prompt exist in the UI (`PersonalityPanel.jsx`, `MemoryPrompt.jsx`, wired into `App.jsx`/`ChatWindow.jsx`) and pass the build, but have not been exercised through the actual React app. Needed to close Gate 3: a browser-enabled session, or the user manually moving sliders, approving/rejecting a proposed memory, and reloading the page to confirm both survive, in the running dev UI.

## Personality-conditioning fix (29 Sep 2026, ~13:00-14:50 IST) -- Gate 3 explicitly reopened

User did the browser-UI check from the previous work block and found persistence worked, but a real behavioural bug: all four sliders persisted and were confirmed reaching the backend, but changing them produced no meaningfully observable difference in BUD's replies. Exact reproduction supplied: the same message sent at humour LOW/MEDIUM/HIGH ("I had such a boring day at work. My brain has officially stopped working.") produced three near-identical acknowledge-plus-question replies with no wit gradient; the same for a directness test on an advice prompt, where only response length varied.

**Investigation** (traced UI slider -> request payload -> backend preference retrieval -> prompt construction -> analyzer/mode interaction -> final generation, per the user's explicit instruction, before writing any fix): `backend/app/services/policy.py`'s `response_policy` only inserted the humour/sarcasm slider band text inside `if humor_allowed:`, where `humor_allowed` is `Analysis.humor_allowed` -- a field the analyzer LLM sets independently, per turn, based on whether *it* judges the moment "casual or playful." Its instruction in `state.py`'s `ANALYZER_PROMPT` required the user to already be joking/playful, or set it false "whenever the moment is serious, vulnerable, or ... informational." A boredom complaint isn't playful yet, isn't serious either -- but the prompt's binary framing pushed the analyzer to `false` for exactly this kind of ordinary, safe, low-stakes negative statement, which fully erased every humour-slider instruction regardless of its value. A secondary factor: the *unconditional* warmth/directness band text existed but was weak ("Be very direct and blunt... while staying respectful") and was undercut by a fixed closing line -- `"Use a warm, respectful tone. Safety takes priority..."` -- appended last (highest positional weight) on every normal-sensitivity turn, regardless of the directness setting.

**Fix**, architectural rather than prompt-tuned to the two example messages:
1. Decoupled slider expression from the per-turn contextual flag. Humour/sarcasm band text is now unconditional whenever sensitivity is `normal`; `analysis.humor_allowed == False` now only appends a targeted "this particular moment calls for a straighter answer... resume your usual style once a lighter moment returns" note on top -- it can no longer delete the slider's own instruction.
2. Loosened `ANALYZER_PROMPT`'s `humor_allowed` criteria: true by default for ordinary safe conversation including mundane complaints/mild frustration/boredom; false only for genuinely heavy/vulnerable moments, an explicit request for seriousness, or a plain informational question humour would get in the way of.
3. Rewrote all four band ladders (`WARMTH_TEXT`, `HUMOUR_TEXT`, `SARCASM_TEXT`, `DIRECTNESS_TEXT`) from soft mood adjectives ("feel free to be playfully humorous when it fits") into concrete imperative instructions a model can act on ("actively look for a witty, playful or lightly teasing angle... before defaulting to a plain response").
4. Removed the blanket "warm, respectful tone" tail line that fought the sliders; replaced with a slider-neutral "safety takes priority over mode, personality settings and any user style request."
5. Restructured the system prompt into labelled sections (CORE IDENTITY, mode strategy, PERSONALITY EXPRESSION FOR THIS REPLY, CONTEXTUAL OVERRIDES, RESPONSE RULES) matching the request's suggested architecture, and added one-line bridges in `MODE_RULES` connecting LISTEN/VIBE to the humour setting and HELP/REALITY_CHECK to the directness setting -- so mode (what strategy) and personality (how it's delivered) compose instead of the mode text silently speaking for both.
6. Added an explicit CONTEXTUAL_OVERRIDES instruction: an explicit "be serious"/"stop joking" request overrides any humour/sarcasm/directness setting immediately, with usual expression resuming once the user signals it's fine again; high directness still never permits rudeness, high humour never overrides a moment that clearly matters to the user.

Also trimmed `groq.py`'s `max_completion_tokens` (1024->768 for json_mode, 1600->1000 for generation) after live debugging surfaced that GPT-OSS reasoning tokens count against that budget and the account's token quota was under pressure -- a safe reduction with comfortable headroom over all observed real reply/JSON lengths, not a correctness-risking cut, and unrelated to but discovered during this same investigation.

Offline: added `backend/tests/test_personality.py`, 21 new deterministic tests directly targeting this bug class: band-boundary assignment, all four dimensions have four distinct concrete band texts, **the regression test for the actual bug** (humour band text reaches the prompt regardless of `humor_allowed`, with the override note appearing only when it's false), low-vs-high band text differs per dimension and dimensions don't cross-contaminate (changing sarcasm doesn't change warmth/directness text), safety fully suppresses humour/sarcasm/flirt even at slider value 100, `MODE_RULES` reference the correct dimension per mode, the contextual-override instruction is present in the composed prompt, and two full `chat()`-level tests proving a saved preference reaches the generator's system prompt for **prompts the user never tested** (an unseen high-humour case and an unseen low-directness case), directly answering the "must generalize, not be hardcoded to the two example prompts" requirement. `python -m pytest -q` -> **160 passed** (up from 135).

**Live re-verification could not be completed this session.** A first live smoke test on the exact humour regression prompt returned `429` on all three slider settings even with 25-30s backoff and retries. Root-caused with a direct diagnostic call against Groq's API (not guessed): the response body was `"tokens per day (TPD): Limit 200000, Used 199760, Requested 471"` for `openai/gpt-oss-120b` in this account -- a **daily** token quota, effectively exhausted (99.88% used) by the cumulative live testing across today's Gate 2 and Gate 3 work, not the per-minute limit that recovered earlier today. `retry-after: 100` and the specific TPD numbers confirm this is a hard daily cap; no pacing or backoff strategy works around it. `backend/scripts/verify_personality.py` was written and is ready to run -- it covers the full required matrix (all 4 sliders at LOW/DEFAULT/HIGH on a dedicated prompt each, the two exact regression prompts from the report, a context-override transcript, 4 slider-combination configurations, and one unseen prompt per slider) -- but has not been run to completion.

**Gate 3 closed 29 Sep 16:15 IST.** The user updated the Groq API key (confirmed working end-to-end post-restart: a real `/api/chat` turn returned 200), then ran live testing directly in the browser rather than waiting for `scripts/verify_personality.py`, and confirmed: slider LOW vs HIGH difference was clearly observable in replies; the Personality panel loads, saves and persists across reload; the memory approve/reject prompt works; and an explicit "be serious" request correctly overrode humour/sarcasm even with playful sliders set high. Combined with 160/160 offline tests (81 Gate 2 + 42 Gate 3 persistence + 21 Gate 3 personality, zero regressions) and this session's own final health check (both servers healthy), this satisfies the Gate 3 completion criteria without needing the scripted matrix run to completion -- real browser evidence from the user is stronger proof than an API-level script for exactly the kind of "does this feel different" question this bug was about.

Work block: approximately 03:24-03:31 IST on 29 Sep 2026.

Observed evidence:
- Backend: `.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000` started successfully.
- Frontend: `npm.cmd run dev` started Vite 6.4.3 at `http://localhost:5173`; HTTP GET returned 200.
- Live API: `(Invoke-WebRequest -UseBasicParsing http://localhost:8000/health).Content` returned `{"status":"ok"}` with HTTP 200.
- Tests: `.\.venv\Scripts\python.exe -m pytest -q` returned **3 passed**, with one upstream Starlette/AnyIO deprecation warning.
- Build: `npm.cmd run build` passed, 25 modules transformed. `rg` found no `GROQ_API_KEY`, `SELECT_AND_VERIFY_MODEL` or `DATABASE_URL` in `frontend/dist` (no secrets are required by Gate 1).
- Dependency install: Vite patched to 6.4.3; npm reported **0 vulnerabilities**.
- Browser attempt: Chrome unavailable; browser inventory `[]`. Subsequent user verification confirms page rendering, no console errors and acceptable appearance at their current viewport. The user then confirmed Backend connected and the 360px layout without overlap or horizontal scrolling. Detailed keyboard and reduced-motion runtime QA remain for Gate 5.

Environment issues resolved: used installed Python 3.12 instead of the broken Windows alias; used `npm.cmd` instead of the blocked PowerShell wrapper; dependency downloads succeeded after network escalation. No remaining Gate 1 blockers: user manual verification supplied the browser acceptance evidence despite absent browser automation. Exact Dribbble screenshot remains absent; shell is an adaptation only.

## Gate 2 work block (29 Sep 2026)

Implementation is present, but Gate 2 is **not complete**. Verified required task count remains **2 / 13** until live provider and browser acceptance pass.

- Backend command: `.\.venv\Scripts\python.exe -m pytest -q` from `backend`: **76 passed**, one upstream Starlette/AnyIO deprecation warning.
- Frontend commands: `npm.cmd test`: **2 passed**; `npm.cmd run build`: passed, 26 modules transformed. Tests cover rendering and API-client success/error handling; they are not browser interaction tests.
- Uvicorn command: `.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000`; restarted successfully with Gate 2 code. Existing Vite dev server serves the updated frontend, HTTP 200. `/health` remains `{"status":"ok"}`.
- Environment: user values had landed in root `.env.example`, not the requested file. Moved only Groq settings into ignored `backend.env`, removed the example key, and verified key presence and requested model equality without printing the key. Actual key is absent from frontend build output.
- Live command: `.\.venv\Scripts\python.exe scripts/verify_live.py`. Eleven ordinary cases failed with sanitized HTTP 502; urgent case passed with deterministic supportive text and no provider generation; context test failed on its first turn. Direct sanitized diagnosis: provider HTTP 404, `model_not_found` for `llama-3.3-70b-versatile`.
- Read-only account model query returned HTTP 200. Available alternatives include `openai/gpt-oss-120b` and `openai/gpt-oss-20b`; no replacement has been silently selected. Owner: user model decision, then agent live rerun.
- Browser inventory returned `[]`. No real typed browser conversation has been demonstrated for Gate 2. Owner: browser-enabled session or explicit user manual verification after provider setup succeeds.
- Tests use mocked provider responses to verify pipeline/policy behavior. They do not establish classifier accuracy or universal safety compliance. Runtime local urgent response was verified; ordinary real model replies remain unverified.

Scope held: no SQLite, long-term memory, sliders, microphone or voice output. Optional request history is tab-local context only; documented in `api-contracts.md`. Public deployment decisions are unchanged.

## Gate 2 work block, continued (29 Sep 2026, ~05:00–05:20 IST)

Model unavailability resolved: `backend.env` `GROQ_CHAT_MODEL` set to `openai/gpt-oss-120b`. `app/services/groq.py` now requests a strict `json_schema` response format (not just `json_object`) for the `gpt-oss` model family, raised the analyzer token budget, and treats a provider `json_validate_failed` 400 or a `finish_reason: length` on a JSON-mode call as `ANALYZER_INVALID`, which `app/services/state.analyze` retries once exactly like a local parse failure, falling back to a deterministic LISTEN clarification if the retry also fails.

A first live pass (17 raw-analyzer cases + 17 full-pipeline cases) surfaced four reply-quality defects, all fixed in `app/services/policy.py` and `app/services/state.py` (`ANALYZER_PROMPT`): unsolicited Hinglish on an English prompt (added explicit language-matching instructions), a reply implying BUD could bake a cake (added an explicit no-body/no-physical-activity-claims rule), a REALITY_CHECK reply that treated an expectation about a friend as being about BUD itself (added explicit third-party framing unless BUD is named), and a LEARN/RAG explanation that invented a medical example (restricted illustrative examples to harmless domains and required stating that retrieval does not guarantee accuracy).

Backend restarted on the updated code before re-verification (process previously running could have predated the edits). `python -m pytest -q`: **81 passed**. Re-running the raw analyzer (`scripts/verify_analyzer.py`, no retries, no deterministic policy) found two further misclassifications: a grief-plus-roast-request message chose mode `VIBE` instead of `LISTEN` (sensitivity was already correctly `sensitive`, so downstream humour would still have been suppressed, but the mode itself was wrong), and ordinary hurt feelings about a slow-replying friend were flagged `sensitive` instead of `normal`. Tightened `ANALYZER_PROMPT` so a serious loss/danger/abuse disclosure keeps mode `LISTEN` even alongside a joke/roast request, and so everyday interpersonal friction stays `normal`; both cases individually re-verified as passing, and `pytest` remained **81 passed** (prompt text is not covered by offline mocks).

Full live pipeline re-run: `python -m scripts.verify_analyzer` style raw check plus `scripts/verify_live.py --delay 12` against the restarted backend: **18/18 passed, 0 failures** — all five modes, mixed/negated/uncertain intent, the grief-with-roast-request sensitive case (BUD declines the roast, states sympathy, stays sensitivity `sensitive`), the urgent self-harm case (deterministic local route, confirmed no provider call needed), four Hinglish cases, and the two-turn context-recall check (`"You mentioned it's a junior Python developer role."`).

Gate 2 remaining blocker: this session has no browser-automation tool, so all live evidence above is `httpx`-level against `/api/chat`, not a conversation driven through the actual React UI. The backend (port 8000) and existing Vite dev server are both running the current code. Needed to close Gate 2: either a browser-enabled session, or the user manually exercising a few typed conversations in the UI and confirming replies/modes match and the console is clean — the same manual-verification path used to close Gate 1.

## Reply delivery pass (29 Sep 2026, user-requested)

User feedback: replies read flat, humour didn't land, and output needed better visual structure. `app/services/policy.py`'s `response_policy` base instructions gained: (1) sparing emoji (max two, never in `urgent`/`sensitive` replies, never inside HELP/LEARN's substantive steps, so functional content stays uncluttered); (2) an explicit blank-line-between-distinct-thoughts rule for scannable multi-step replies — no frontend change needed since `frontend/src/styles.css` (`.message p`) already sets `white-space: pre-wrap`, so backend newlines already render as real breaks; (3) VIBE-specific comedic-timing guidance: short one-line setup, punchline as its own short final line, no immediate self-explaining or softening afterward, which was killing delivery.

While live-testing this, found LEARN-mode replies were leaking raw `**bold**`, `` ` `` backticks and ``` code fences — the frontend has no Markdown renderer (plain `<p>` tag), so these would show as literal stray punctuation. This predates this work block (present in earlier Gate 2 live samples too) but had not been caught. Tightened the plain-text instruction to explicitly ban all Markdown syntax including bolded labels like "Example:", and to render code as plain indented lines.

Live re-verification (restarting the backend each time to pick up the edits):
- VIBE joke ("Monday coffee"): punchline now lands on its own line after a blank line, one warm closing emoji — matches the requested comedic timing.
- VIBE/HELP cake and interview-prep cases: one tasteful emoji each, steps still numbered and emoji-free internally.
- Two LEARN cases (RAG explanation, a Python `SyntaxError` fix): zero Markdown tokens (`**`, `` ` ``, ``` ``` ```, `#`) in either reply after the fix; code shown as plain indented lines.
- Sensitive (grief-with-roast-request) and urgent (self-harm) cases: confirmed still zero emoji and zero humour, as required.
- `python -m pytest -q`: **81 passed** throughout (all changes are prompt text, not covered by offline mocks, but nothing regressed).

This is still API-level (`httpx`) verification, same browser-UI caveat as above.

## Personality / conversational-behaviour upgrade (29 Sep 2026, ~06:00-06:20 IST, user-directed)

User request: make BUD feel like a socially intelligent friend (warm, curious, capable of humour,
teasing and user-invited flirting, serious when it matters) instead of a therapist/support-bot,
explicitly excluding persistent memory/preference storage (still Gate 3). This is a scope decision
recorded in `docs/scope.md`'s Confirmed section, not an unrequested change.

Architecture: the analyzer (`Analysis` in `schemas.py`, `ANALYZER_PROMPT` in `state.py`) gained eight
new per-turn signals alongside the frozen `mode`/`sensitivity`: `user_intent`, `tone`,
`emotional_intensity`, `response_style`, `humor_allowed`, `flirt_allowed`,
`follow_up_question_needed`, `reality_check_needed`. The unused `advice_requested` field (never
consumed anywhere in the pipeline) was removed rather than kept alongside the new, more useful
`user_intent`. `response_policy` (`policy.py`) was rewritten from a static per-mode string into a
personality layer (constant across modes) plus dynamic per-turn instructions built from these flags,
with `MODE_RULES` narrowed to strategy only. Critically, humour and flirting are clamped to `false`
in Python whenever the combined sensitivity is not `normal`, regardless of what the analyzer itself
proposed for that turn -- the model's own judgement is never the last word on safety-adjacent style,
consistent with `CLAUDE.md`'s "safety routing precedes mode and personality."

Offline: `python -m pytest -q` -> **93 passed** (81 prior + 9 new: humour/flirt clamped under
sensitivity even when the analyzer disagrees, flirting offered only when flagged and withheld by
default, follow-up-question instruction toggling, the reality-check nudge appearing outside
`REALITY_CHECK` mode but not duplicating inside it, three `response_style` length variants, and one
safety-regex regression -- see below).

Live: wrote `backend/scripts/verify_conversation.py`, a 13-category regression conversation set
matching the request's validation list exactly (greeting, casual conversation, distraction, joke/
banter, teasing BUD, flirting, Hinglish, curiosity, criticizing BUD, vulnerable disclosure, explicit
opinion request, playful-to-serious and serious-to-casual transitions), with automated 429
retry/backoff and a cheap banned-generic-AI-phrase check. Iterated against the real
`openai/gpt-oss-120b` model (backend restarted before each run) and found/fixed three real issues:

1. Hinglish replies drifted into Devanagari script. Root cause: the personality rewrite had dropped
   the explicit "Romanized" instruction from the earlier reply-delivery pass. Restored it as its own
   prominent `LANGUAGE (strict)` block with a worked example; re-verified across 4 separate live
   Hinglish cases (LISTEN/VIBE/REALITY_CHECK/HELP modes) with zero Devanagari characters after the fix.
2. A casual personal reveal ("BUD, I hate the sea, I'm scared of the ocean") got no curious follow-up
   at all -- the analyzer was treating it like heavy venting that shouldn't be probed. Tightened
   `follow_up_question_needed` guidance to distinguish a casual quirk/fear reveal (curiosity welcome)
   from genuinely heavy venting (don't probe); re-verified 3/3 live runs now ask one natural question.
3. An explicit opinion request ("what do you think, should I quit my job") got a neutral 3-step
   option list that never actually answered the question. Added an explicit "give a real opinion, not
   a dodge" instruction; re-verified live -- BUD now states an actual leaning before the practical
   context.
4. (Found opportunistically, not from the personality work itself) The local `SENSITIVE` safety regex
   required "feeling **so** X"; "feeling **really** overwhelmed and worthless" slipped through to
   `normal` on one live run out of three, relying entirely on the analyzer's own (probabilistic)
   sensitivity call. Widened the regex to a bounded gap so this is now a deterministic local backstop
   regardless of analyzer variance; added a regression test; re-verified `sensitive` on two repeated
   live calls with identical text.

Final full 13-category live run: zero banned-phrase hits; the joke-banter case matched the
"redeem myself" example tone almost verbatim; the criticism case ("stop asking what's on my mind,
you're being weird") was acknowledged in one short line without over-apologizing ("Got it, I'll ease
off.") and the very next turn asked no question at all, confirming the behaviour change actually
persisted rather than just being claimed in that one reply; flirting was reciprocal and
self-aware without being unprompted elsewhere in the same run; the playful-to-serious and
serious-to-casual transitions both dropped/regained humour and emoji appropriately with sensitivity
flipping to `sensitive` and back to `normal` in step.

Known, accepted limitation: mode selection for an ambiguous serious disclosure phrased with "I don't
know what to do" varied between `LISTEN` and `HELP` across otherwise-identical live runs. Both are
defensible under the existing mixed-intent precedent ("I need to rant, but tell me what to do" =>
HELP), and sensitivity/no-humour/no-flirt held correctly in every run regardless of which mode was
picked. Not chased further -- flagged as expected analyzer variance, not a regression, to avoid
over-fitting the prompt to one run's outcome.

Same browser-UI caveat as the rest of Gate 2: all of the above is `httpx`-level against `/api/chat`.

## Gate 4 work block (29 Sep 2026, ~16:15-16:30 IST)

Per `skill.md`'s per-gate workflow, checked `tasks.md`'s open decisions before implementing: the exact Whisper model ID had never been confirmed (only the chat model was resolved in Gate 2). Queried `/openai/v1/models` and found two active Whisper models on this account -- `whisper-large-v3` and `whisper-large-v3-turbo`. Asked the user rather than picking silently (per `CLAUDE.md`: never silently substitute model identifiers); they chose `whisper-large-v3` for better Hindi/Hinglish code-switching accuracy over turbo's speed. Recorded in `tasks.md` and `docs/scope.md`.

Backend: `app/services/transcribe.py` streams the uploaded audio directly to Groq's `/audio/transcriptions` endpoint in memory (never written to disk, trivially satisfying `docs/scope.md`'s "keep raw recording only during transcription" boundary since there is nothing on disk to clean up). `app/routes/transcribe.py` validates content-type against a browser-realistic allowlist (webm/ogg/wav/mp4/mpeg) and size (≤10MB) before any provider call, returning 422 for empty/bad-format and 413 for oversize. Discovered and fixed a missing dependency: FastAPI's `UploadFile` requires `python-multipart`, which was not in `requirements.txt` and caused a runtime error until added and installed.

Frontend: `services/api.js` gained `transcribeAudio()` (multipart `FormData`, deliberately omitting a manual `Content-Type` header so the browser sets the correct boundary). New `components/VoiceOrb.jsx`: a `MediaRecorder`-based mic button with idle/recording (live timer)/transcribing/error states, clear mic-permission-denied and unsupported-browser error copy, and a 2-minute auto-stop. Wired into `ChatWindow`'s composer so a successful transcript lands in the existing editable textarea (appended to any existing draft) rather than auto-sending -- the user can correct it before pressing send, satisfying the "editable transcript, same chat path" requirement from `docs/architecture.md` without a second conversation pipeline.

Offline: `python -m pytest -q` -> **173 passed** (up from 160; +13 new tests: unsupported content-type, empty recording, oversize recording, missing file, missing configuration, provider error sanitization for 401/403/429/500, timeout, a successful transcription with language detection, empty-transcript rejection, and one full route test with a faked provider). `npm.cmd test` -> **3 passed** (added a `transcribeAudio` client test verifying the multipart body shape and that no manual Content-Type is set). `npm.cmd run build` -> passed, 30 modules.

Live verification used a trick to get genuine speech without a browser: Windows ships a built-in TTS engine (`System.Speech`/SAPI, no new dependency) with two installed English voices. Synthesized "I had such a boring day at work. My brain has officially stopped working." to a real WAV file via PowerShell, then sent it through the actual running `/api/transcribe` against the real Groq API: it came back with the **exact spoken sentence** and `language: "English"` correctly detected. Piped that transcript into `/api/chat` unchanged and got a normal 200 reply, confirming the "same chat path, no second pipeline" design actually holds end-to-end, not just on paper. Also live-verified the three validation edge cases (empty, bad content-type, oversize) against the running server -- all correctly rejected before reaching Groq.

Not verified this session: Hinglish/Hindi transcription accuracy (`Get-InstalledVoices` shows only `Microsoft David/Zira Desktop`, both en-US -- no Hindi voice available locally to synthesize a sample) and the actual browser recording UX (mic permission prompt, `VoiceOrb`'s visual states, stop control, keyboard access) -- no browser-automation tool this session, the same limitation noted for every prior gate. **Gate 4 remains open** pending the user's own live test: an English recording, a Hinglish recording, a microphone-permission-denial case, and reviewing/correcting a transcript before sending, all through the actual browser at `localhost:5173`.

## Gate 4 continued: Hinglish fix and full UI redesign (30 Sep 2026, ~03:00-04:10 IST)

User reported a live failure: "Hi, how are you, ki haal chaal?" transcribed as "Hello, how are you? I can't even hold the child's head." -- a hallucination, not a mistranslation. Explicitly instructed to inspect before changing anything and to verify Groq's actual supported parameters rather than invent any. Fetched Groq's speech-to-text docs directly: confirmed the real parameter set is `file`/`url`, `language`, `model`, `prompt` (<=224 tokens), `response_format`, `temperature` (default and recommended `0`), `timestamp_granularities[]`. Our `transcribe.py` used only `model` and `response_format` -- `language` was already correctly unset (not the bug), `temperature` was already at the recommended default (not an actionable lever), and `prompt` was the one real, unused lever. Root cause: Whisper hallucinating on short, ambiguous, code-switched audio with no decoder context -- a known failure mode. Fix: added a short neutral `TRANSCRIPTION_CONTEXT_PROMPT` (style/context hint about expected Hinglish code-switching, explicitly not a vocabulary list or a "clean up the words" instruction); `language` stays unset. Also tightened `getUserMedia` constraints (`echoCancellation`/`noiseSuppression`/`autoGainControl`) in the new recording component, previously relying on unspecified browser defaults. Explicitly did **not** add a chat-LLM "correction" pass over the transcript -- that risks fabricating what the user actually said, which the user explicitly ruled out. Added a regression test asserting the prompt is sent and `language` stays absent. Live-reverified the English happy path is unaffected (exact transcript, correct language, via the same Windows-TTS method as the original Gate 4 verification). The Hinglish improvement itself needs the user's live retest -- no Hindi TTS voice is available on this machine to verify it directly.

Then implemented the full-page voice-first UI redesign, preserving BUD's existing palette/theme/personality/memory entirely (backend untouched for this half): removed the permanent sidebar; the existing orb is now `BudOrb`, a central component with idle/recording/responding animation states (respecting the existing global reduced-motion rule); a new floating three-action band (Write/Let's talk/Parameters) in BUD's own dark palette, not the reference screenshot's colours; a new `RecordingPanel` with a real `AnalyserNode` waveform (visualization only, torn down on stop/cancel/unmount, never wired to output), working native `MediaRecorder` pause/resume, and a live timer -- finishing always lands the transcript in the same editable composer, never auto-sending; `PersonalityPanel`/`MemoryList` (unchanged storage/logic) now open inside a Parameters modal; the old sidebar's status/privacy copy moved into a "Your space, taking shape" overlay reachable from a new profile/three-dot menu. State model: `composerMode` ('text'/'voice') lifted to `App.jsx`; each `RecordingPanel` instance's sub-state (`requesting_mic`/`recording`/`paused`/`transcribing`/`error`) is a single enum, structurally preventing impossible combinations rather than juggling independent booleans. The now-redundant `VoiceOrb.jsx` (a plain mic button) was deleted -- `RecordingPanel` is a strict superset.

The existing frontend test setup (SSR string-rendering only) could not simulate clicks or state transitions, which most of the requested tests need. Added `jsdom` + `@testing-library/react` (a standard, minimal, directly-justified addition) plus a small fixture (`tests/setup-dom.mjs`) providing jsdom globals and fake `MediaRecorder`/`getUserMedia`/`AudioContext` implementations, so the *real* `RecordingPanel` logic runs against fakes rather than testing a mock of the component. New `tests/interaction.test.mjs` (9 tests): Write/Let's-talk toggle the composer, permission denial shows an error with a working fallback, pause/resume behave correctly, finishing a recording never calls `/api/chat` on its own, cancelling and unmounting both provably stop the microphone track, Parameters opens with sliders visible and expanded, the three-dot menu opens the Space overlay, and the orb's CSS state reflects "responding." `render.test.mjs` gained 2 structural checks (no `<aside>`, all three action-band labels present). **Frontend: 15/15 passing.** Backend: **174/174**, unaffected by Part B and only +1 test from Part A.

**Gate 4 remains open.** Live checks still needed from the user: retest the exact original Hinglish phrase plus a longer mixed-language sample; English/Hindi/Indian-accented speech; mic permission denial; pause/resume in the real browser; transcript correction before sending; the Parameters and "Your space" overlays; orb idle vs. responding animation; and the responsive layout on a narrow viewport.

## Gate 4 continued: live-feedback fixes and TTS (30 Sep 2026, ~03:00-04:45 IST)

User ran the browser check and reported: Hindi still not understood at all; a hover/focus border on the chat bar; too little spacing between the orb and its caption; a request for an entrance animation on the hero heading; and -- most importantly -- "even when I pause, the recording still continues," plus a new request for BUD to speak its replies aloud.

Investigated the pause bug before touching anything else, since it's the most serious (a privacy-relevant "mic stays live" issue). Confirmed `main.jsx` wraps the app in `React.StrictMode`, which deliberately mounts `RecordingPanel`'s effect, tears it down, and mounts it again in development. The existing boolean `cancelled` ref got reset to `false` by the second mount before the first mount's in-flight `getUserMedia()` promise resolved, so the stale first attempt's stream/recorder attached anyway -- a second, orphaned `MediaRecorder` that Pause/Cancel/Stop never referenced (`recorder.current` only ever pointed at whichever attempt finished last). Fixed by replacing the boolean with a monotonic generation counter compared against the live ref value at resolution time (not a value captured before the `await`), and by having cleanup also bump the counter so a still-pending `getUserMedia()` at final unmount discards itself too. Added a regression test that renders inside a real `React.StrictMode` wrapper with a fake `getUserMedia` returning a fresh stream per call, and asserts exactly one stream survives after pausing -- the test itself first exposed a phantom-stream counting bug in the test helper, fixed separately from the actual component fix. This race plausibly also explains degraded/hallucinated Hindi transcription (two overlapping mic captures corrupting the audio Whisper received), though that specific improvement needs the user's live retest since no Hindi TTS voice exists on this machine to verify independently.

CSS: removed the 6px-offset focus-visible outline specifically from the chat textarea (kept for buttons/links; `.composer` now tints its own border teal on focus instead) -- almost certainly the reported "border on hover"; added visible top margin between the orb and its caption (was zero). Entrance animation: the hero heading now scales down from large-and-centered with a fade-in over ~1s (`cubic-bezier` ease-out, "zoom out... make it the center of attraction" as requested) before the orb/chat/action-band fade in just after; respects the existing global reduced-motion rule automatically. Had to give `.action-band` its own keyframe variant since a shared one would have overwritten its existing `translateX(-50%)` centering transform mid-animation.

TTS: researched Groq's actual text-to-speech docs before implementing anything (`console.groq.com/docs/text-to-speech`, `.../orpheus`) rather than guessing at parameters. Confirmed endpoint `POST /openai/v1/audio/speech`, parameters `model`/`input`/`voice`/`response_format`, only `wav` supported, 6 named voices, and a **200-character input limit per call** -- a real constraint requiring the backend to chunk longer replies at sentence boundaries (falling back to word boundaries for one long sentence) and stitch the resulting WAV clips into a single file via Python's `wave` module, so the frontend always gets one playable clip regardless of reply length. Asked the user to confirm the engine (Orpheus vs. browser `SpeechSynthesis` vs. Piper) rather than silently picking, given the project's own rule against silently substituting the voice engine and Piper's already-recorded stretch-goal status; they chose Orpheus. `ChatWindow` now calls `/api/speak` after each successful reply (unless muted via a new persisted header toggle), plays the result, never overlaps two replies, stops if the user switches to voice input or clears the chat, and cleans up its object URL/audio element on unmount; `BudOrb` treats TTS playback as "responding" the same as the network-wait window.

Live-testing the happy path immediately surfaced a real, unanticipated blocker: Groq returned `400 model_terms_required` for `canopylabs/orpheus-v1-english` -- this model needs one-time terms acceptance at `console.groq.com/playground?model=canopylabs%2Forpheus-v1-english`, a manual step gated behind the account owner's login that cannot be done programmatically. Added a specific check for this provider error code so the backend now returns a clear `503 MODEL_TERMS_REQUIRED` explaining exactly what to do, instead of the generic sanitized `PROVIDER_ERROR`. **TTS audio itself has not been live-verified** and cannot be until the user completes that acceptance.

Offline: `python -m pytest -q` -> **190 passed** (up from 173; +15 TTS chunking/stitching/multi-chunk-frame-count/error-mapping/terms-required tests, +2 route tests). `npm.cmd test` -> **18 passed** (up from 15; +1 StrictMode race regression test, +2 TTS mute/speaking-lifecycle tests). `npm.cmd run build` -> passed, 36 modules.

**Gate 4 still not closed.** In addition to the live checks already listed above, now also needs: the user's retest of the exact Hinglish phrase and pause/resume after the StrictMode fix; confirmation the CSS/animation changes look right; and the user completing Orpheus's terms acceptance so TTS audio can finally be verified.
