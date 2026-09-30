# BUD project workflow (local instruction file)

This is a repository-level build guide for Claude/Codex, not an installed ChatGPT skill.

## At each gate

1. Read the gate, acceptance criteria, current contracts, and relevant prompts.
2. State the smallest implementation and outstanding decisions.
3. Implement one vertical slice. Keep UI state, API route, policy, provider adapter, and persistence separate.
4. Run focused tests plus a manual request or browser check. Capture actual result.
5. Update `tasks.md` with evidence and unresolved issues. Stop at the gate boundary.

## Completion definition

The app starts locally; text and voice paths share the same conversation pipeline; mode policy and safety overrides pass cases; saved preferences survive restart; memory requires explicit approval; UI works on desktop/mobile and with reduced motion; public demo is tested from a clean browser if deployment is chosen. If optional features fail, report them as omitted.
