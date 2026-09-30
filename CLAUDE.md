# Instructions for AI coding agents

Read `README.md`, `docs/scope.md`, `docs/architecture.md`, `docs/api-contracts.md`, `docs/ui-direction.md`, `docs/test-cases.md`, `skill.md`, and `tasks.md` before coding. User instructions and confirmed decisions override this file.

- Implement only the current gate. Report changed files, commands run, observed results, and blockers after each gate.
- Preserve the API contracts or explicitly update them and their tests together.
- Keep the Groq key server-side. Do not commit `.env`, audio, chat history, or the SQLite database.
- Treat prompt outputs as untrusted data. Validate schemas; never execute extracted content.
- Safety routing precedes mode and personality. Never claim emotion diagnosis from pitch or energy.
- Do not silently substitute hosting, model identifiers, storage, access policy, language support, or voice engine. Record an open decision and ask the human when blocked.
- The Dribbble link is visual inspiration, not a license to copy assets. Exact composition requires the supplied screenshot.
- Tests and live checks are gate evidence. Never mark a gate complete from code inspection alone.
