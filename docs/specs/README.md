# Specification registry

This registry contains the normative sources for live Cronicl behaviour.
Revalidate a row when one of its listed touchpoints is changed or its mapped
verification contradicts it; there is no calendar-based expiry. A row is
`superseded` only with a successor, or `retired (historical)` only with a
retention reason. Plans, evidence and READMEs are not normative sources.

| Spec | Status | Scope | Touchpoints requiring revalidation | Verification |
| --- | --- | --- | --- | --- |
| `unified-entry-and-assistant.md` | approved for implementation 2026-09-10; implementation in progress | Compact contextual input, local parsing, executable assistant and full manual editors; revises input/assistant clauses in todo, notes and day-feed contracts | Footer, chat, editors, assistant schemas/services, proxy and execution | `frontend/scripts/test-quick-entry.mjs`; A1–A15 in `../plans/2026-09-10-unified-entry-implementation.md` (remaining evidence pending) |
| `android-google-sign-in.md` | approved by user 2026-09-08 | Android Credential Manager, native v2 identity proof and sessions; supersedes Android browser handoff | Auth/Google configuration, bridge, login UI, session schema and migration | `backend/tests/test_google_native_auth.py`, `backend/scripts/verify_native_auth_migration.py`, `frontend/scripts/test-native-login-ui.mjs`, Android/device acceptance |
| `native-travel-companion.md` | approved; Android login revised by `android-google-sign-in.md`, iOS login v1 blocked | Private travel monitoring, native location and existing todo highlight | Native lifecycle, auth, migration, worker/push, routes and travel UI | `backend/tests/test_native_auth_containment.py` (v1 rejection), `backend/tests/test_native_travel.py` (v2 session/travel), migration rehearsal, frontend checks, device acceptance |
| `multi-account-scale-and-body-composition.md` | approved (revised by shared spaces) | Accounts, shared scale and health-language limits | Auth/session, ownership scope, Scale v2 payload or assignment, body profile/BIA, the single Alembic baseline, Google integrations | `backend/tests/test_scale_v2_contract.py`, `backend/tests/test_scale_sync_contract.py`, account-isolation integration suite (required), clean-database baseline rehearsal |
| `shared-spaces.md` | approved (revised by notes, areas and all-tasks home context) | Explicit member-owned areas, invitations, shared notes/to-dos and shared manual shopping lists | Space/membership/invitation routes, todo or shopping access scope, migrations, API client and day/feed controls | `backend/tests/test_shared_spaces_contract.py`, `backend/tests/test_notes_contract.py`, account-isolation integration suite, frontend check/build and accessibility review |
| `notes-and-areas.md` | approved | Private note board, area-derived access and calendar planning | Note schema/routes/migration, todo origin link, board/footer/calendar controls | note API isolation tests, frontend check/build and accessibility review |
| `contacts.md` | approved | Private, consent-based account contacts and public aliases without resource sharing | Account alias onboarding, contact routes/search, contact migration, API client, contacts page/header entry | `backend/tests/test_contacts_contract.py`, alias/contact account-isolation integration tests, frontend check/build |
| `configurable-meals.md` | implemented (online-first) | Konto-private Mahlzeiten, Rezepte, Pläne und Verzehr | Meal routes/schemas/models, meal migrations, sync entity contract, meal API client or editor flow | `backend/tests/test_configurable_meals_contract.py`, `backend/tests/test_meal_account_isolation.py`, meal browser flow (required) |
| `shopping-list.md` | approved (revised by shared spaces) | Private Einkaufsartikel, Footer-Schnellzugriff und explizite Mahlzeitenbedarfsübernahme | Shopping routes/schemas/models/migration, meal-plan ingredient projection, footer/panel, shopping route, API client | `backend/tests/test_shopping_contract.py`, frontend check/build, accessibility review |
| `todo-places-and-travel.md` | approved (revised by shared spaces) | Private und Space-To-dos mit bestätigtem Ort, KI-Entwurf und Anreise | Todo schema/model/migration, place/travel/AI routes, sync, Tagesansicht | `backend/tests/test_todo_places_contract.py`, account-isolation integration suite, frontend check/build |

Use [`fittrack-artifact-lifecycle`](../../.agents/skills/fittrack-artifact-lifecycle/SKILL.md)
when a change may invalidate an artifact. It requires an evidence-based outcome:
confirmed, revise, supersede, or retire.
