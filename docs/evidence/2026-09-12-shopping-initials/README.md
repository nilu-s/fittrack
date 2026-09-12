# Shopping initial fallback

Objective: derive shopping-item icons from the article category and render
title initials when no category icon exists. The user explicitly rejected
manual icon selection and generic fallback symbols.

Owning conflict domain: shopping item classification and shared shopping list
rendering. Scope: `ShoppingList.svelte`, `ShoppingItemEditor.svelte`, shopping
classification/update handling, its contract test and shopping browser
regression. Out of scope: external catalogues, product images, migrations,
authentication and account access behaviour.

Governing artifact: `docs/specs/shopping-list.md`, revised by this explicit
product decision. Artifact lifecycle outcome: **confirmed after revision**.
The account-scoping, meal import and local-only asset commitments remain
unchanged; the former manual-icon clause is replaced by derived category icons
and the initials fallback.

Acceptance: known categories render their local SVG; unknown entries show up
to two title initials; the editor offers category correction but no icon
selection; no browser request selects an account. Verification: backend
shopping contract test, frontend check/design lint/build, and
`frontend/scripts/test-shopping-tiles-ui.mjs` against the deployed web app.

Allowed side effects: one application commit, web image build/replacement,
and public health/login/unauthenticated route checks. Stop on a failed build,
failed public check, or a contradiction with the governing spec.
