# Shopping tiles

Objective: implement the user's requested Bring-style square shopping tiles.
Owning conflict domain: ShoppingList.svelte. Scope: that shared component,
its browser regression and this evidence. No API, persistence, authentication,
deployment or unrelated UnifiedDay edits. Stop on conflicting authoritative
requirements or failed frontend checks.

Design: square red open tiles and green completed tiles, local SVG item icons,
quantity and notes, separate open/recently-used sections. A native checkbox-role
button toggles the item; visible edit/delete buttons retain the existing flows.
Keyboard focus follows a tile between sections. Existing search and item editor
remain the entry/detail workflows. No Bring assets or external catalog added.

Artifact lifecycle: docs/specs/shopping-list.md **confirmed** for the touched
shopping display/interaction. Native status controls, details, sources, local
icons and existing account/API boundaries are preserved. The user's explicit
visual request supplies the red/green tile direction for this surface; other
surfaces retain the muted-light direction. This is not full Bring feature parity.

Verification: frontend/scripts/test-shopping-tiles-ui.mjs checks square dimensions,
no horizontal page overflow, keyboard completion/reopening, focus preservation
and visible editing at 320, 390 and 1440px using mocked API records. Run from
frontend with SHOPPING_TEST_URL pointing to a local /shopping page. Also run
npm run check, npm run lint:design and npm run build.
