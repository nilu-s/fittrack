---
name: fittrack-accessibility-audit
description: Audit or harden FitTrack UI changes for accessible task completion, including native semantics, keyboard and touch parity, dialogs, focus, contrast, motion, and responsive behavior.
---

# FitTrack Accessibility Audit

Inspect the actual rendered controls and state transitions of the affected
surface. Prefer native buttons, links, inputs, and dialog semantics over
interactive `div` or `span` elements.

Verify that every primary action has keyboard, touch, and screen-reader access;
visible focus is not obscured; dialogs/sheets restore focus; status does not
depend on color alone; and reduced-motion behavior remains understandable.

Treat long-press, double-tap, and drag only as optional shortcuts. Report
concrete issues with affected component, user impact, and smallest safe fix.
Do not redesign the product or change API/account/health-data behavior during
an audit.
