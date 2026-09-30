# UI direction

Reference: https://dribbble.com/shots/27661068-AI-Voice-Website-Concept-Design . The exact shot image was not supplied in this project; the uploaded Screenshot (174) shows challenge categories, not this design. Previous conversation identified dark visual direction and palette chips `#030404`, `#9DCACF`, `#C3D2D3`, `#5DBBBB`, `#54514F`, `#A3D0B3`, `#92635F`, `#DBC940`. Treat placement/typography below as an **adaptation**, not a measured replica; update against a screenshot before high-fidelity implementation.

## Proposed app screen
- Header: BUD wordmark, compact privacy note, clear session/reset action.
- Desktop: central conversation canvas with the large voice orb and chat composer; collapsible preference panel; recent conversation in a readable scroll area. Mobile: single column, voice orb above chat, preferences in a drawer.
- Near-black background `#030404`, elevated surfaces `#111819`, teal `#5DBBBB` focus/accent, cool text `#C3D2D3`, warm gold `#DBC940` reserved for approved-memory prompts. Meet readable contrast; do not use translucent panels behind long text.
- Orb states: idle slow breathing glow; recording concentric ripples and live timer; thinking slow rotation; speaking amplitude-style bars if TTS exists; error still orb with visible text. Use CSS transforms/opacity and `prefers-reduced-motion` to disable nonessential animation.
- The exact active state must be understandable without animation or colour. Provide keyboard access, button labels, recording stop control, microphone permission/error copy, and text fallback.

No copyrighted Dribbble illustration or asset is copied. Match visual principles after the reference screenshot arrives. No fake waveform synchronized to audio unless the visual is clearly ambient.
