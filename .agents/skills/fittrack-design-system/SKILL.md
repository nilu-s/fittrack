---
name: fittrack-design-system
description: Evolve FitTrack's token-based Svelte design system after an approved design direction and interaction contract. Use for shared tokens, primitives, component contracts, and design-lint changes; not for one-off screen restyling.
---

# FitTrack Design System

Read the applicable documents in `docs/design/` and the active ADR before
editing tokens or shared UI. Inspect `frontend/docs/design-system.md`,
`frontend/src/lib/styles/tokens.css`, and `frontend/src/lib/styles/primitives.css`.

Use semantic tokens and extend shared primitives only for patterns that recur.
Keep transitional aliases while active components need them; new components
must not create a parallel palette or styling system.

Prioritize the shared contracts needed by the day feed: section, status,
feature-card, field, dialog, and sheet. Define complete interaction states,
including focus-visible, pressed, disabled, loading, empty, and error where
they apply.

Do not introduce Tailwind, an external component library, or a second theme
layer without explicit user approval. Validate frontend changes with the
repository's design lint, Svelte check, and build commands.
