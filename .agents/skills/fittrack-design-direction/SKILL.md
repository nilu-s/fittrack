---
name: fittrack-design-direction
description: Define or revise FitTrack's visual direction for product UI redesigns before implementation. Use for palette, density, hierarchy, surface, and layout-direction decisions; not for interaction contracts or CSS-only changes.
---

# FitTrack Design Direction

Read `docs/adr/0002-muted-light-product-ui.md` and
`docs/design/fittrack-ui-direction.md` before proposing a new visual direction.

Work from the active product surface and its real content. Preserve the
gedämpft-helle direction: clear sections, no pure-white default surface, no
gradient, glow, glassmorphism, card pile, or generic health-dashboard styling.

Deliver a decision, not implementation code: visual thesis, semantic color
roles, hierarchy/density, section and feature-element treatment, and the
specific fit with the current surface. Name any departure from the direction
and why it is necessary.

Do not decide API contracts, account behavior, or the interaction semantics of
the mixed day feed; use `fittrack-ia-interaction` for those decisions.
