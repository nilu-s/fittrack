# Shopping tiles deployment · 2026-09-12

User explicitly authorized commit and deployment after implementation.
Application commit: `64376cf`, pushed to `feat/clean-ui-day-dock`.
Built from a clean git archive of that commit, using the existing Compose web
build arguments and an isolated build-context override. Uncommitted UnifiedDay
and todo-reorder changes were excluded. Only the web service was replaced with
`docker compose up -d --no-deps --no-build web`.

Running image: `sha256:b62ae9b26bdb317ce5141655893deca68690b874200d08086f0e9fb80cb10f23`.
Public origin: https://cronicl.49.12.225.84.sslip.io

Verification: `/api/health` returned 200 and `status=ok`; `/login` returned 200;
anonymous `/api/shopping` returned 401. The shopping tile browser regression
passed against the deployed site at 320, 390 and 1440px with intercepted API
requests and synthetic records: square tiles, no horizontal overflow, keyboard
completion/reopening, focus restoration, and visible editing controls.
No real shopping records were changed by the test.

Rollback: previous running image preserved as
`personal-organizer-web:rollback-shopping-64376cf`
(`sha256:fe97df5140355393aa44adbcaacf763ca8e6024fdd27cd384cf632674eabadb9`).
Retag it as `personal-organizer-web:latest`, then run
`docker compose up -d --no-deps --no-build --force-recreate web` and repeat the
health and login checks. Retain until release acceptance.
