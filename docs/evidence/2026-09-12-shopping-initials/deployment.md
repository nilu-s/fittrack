# Shopping initial fallback deployment · 2026-09-12

The user explicitly authorized commit and deployment. Application commit:
`19aa764` (`feat(shopping): derive fallback initials`), pushed to
`feat/clean-ui-day-dock`.

Only `api` and `web` were built and replaced with
`docker compose up -d --no-deps --no-build --force-recreate api web`.
No migration, database, environment or credential change was made.

Deployed images:

- API: `sha256:813e950c0aededbdeed78ab753e06ef9419f7801e542797f4292c037b59183e3`
- Web: `sha256:c5aaab1bca65eb0ac043036a75f104e9b2113c5f90c65937fffa0e2d59614ba7`

Verification:

- frontend check, design lint and production build passed;
- production-like API container verified `Paprika` → `produce` and unknown
  titles → `initials`;
- local `/api/health` returned `200` with `status=ok`;
- public `/login` returned `200`; public anonymous `/api/shopping` returned
  `401`;
- the public browser regression passed with an `initials` item at 320, 390 and
  1440px, including square tiles, no horizontal overflow and keyboard toggling.
  It uses intercepted synthetic API responses and did not modify shopping data.

Rollback images from the preceding source commit are retained locally:
`personal-organizer-api:rollback-initials-19aa764`
(`sha256:fc8656256299948dd95f4ff771dacb42bbdfa96d083e15800fe8e448cff13b4c`)
and `personal-organizer-web:rollback-initials-19aa764`
(`sha256:f94306ac6c62592abf45826979b5d93e98e07d460958c9944a982206226148ed`).
Retag both as `personal-organizer-api:latest` and
`personal-organizer-web:latest`, respectively, then recreate only `api` and
`web` using the same Compose command. Retain until release acceptance.
