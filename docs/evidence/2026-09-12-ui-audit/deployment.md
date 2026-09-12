# UI deployment · 2026-09-12

Explicit user authorization: commit and deploy after the UI audit.

Application commit: `0707a9a` (`fix(ui): harden dialogs and responsive layouts with browser audit`).
Service replaced: `web` only, using `docker compose build web` and
`docker compose up -d --no-deps --no-build web`. No migration or production
configuration edits. Existing Compose build arguments were retained.

Deployed image:
`sha256:8ce81f67b2b278fcdaee9e73fca8a744e6ac689ea098f8c2fd41d326b22be652`.

Verification:
- Svelte check: 0 errors, 0 warnings; design lint and production build pass.
- Full local Playwright audit: 139 checked states, no page/dialog overflow or runtime errors.
- Public `/login`: HTTP 200; `/api/health`: HTTP 200, `status=ok`.
- Public `/api/travel` without authentication: HTTP 401.
- Real unauthenticated browser visit redirects to `/login`, displays the Google
  login control and loads its JS/CSS without errors.
- `test-meal-settings-ui.mjs` and `test-todo-direct-edit-ui.mjs` also pass against
  the public deployment with API interception and synthetic fixtures. No private
  data was modified by these checks.

Rollback image preserved locally:
`personal-organizer-web:rollback-ui-20260912`, original ID
`sha256:bf6f390144e2107e8a9250e0bcfdb933245ff1f8d8d504d67e33128c316173ce`.
To roll back, retag that image as `personal-organizer-web:latest`, then run
`docker compose up -d --no-deps --no-build --force-recreate web` and repeat the
public health/login checks. Retain the rollback image until this release has
been accepted in normal use.

Camera, real Google sign-in and native device permissions still require physical
device acceptance; this deployment does not claim those checks were performed.
