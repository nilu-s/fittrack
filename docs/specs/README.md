# Specification registry

This registry contains the normative sources for live FitTrack behaviour.
Revalidate a row when one of its listed touchpoints is changed or its mapped
verification contradicts it; there is no calendar-based expiry. A row is
`superseded` only with a successor, or `retired (historical)` only with a
retention reason. Plans, evidence and READMEs are not normative sources.

| Spec | Status | Scope | Touchpoints requiring revalidation | Verification |
| --- | --- | --- | --- | --- |
| `multi-account-scale-and-body-composition.md` | approved | Accounts, shared scale and health-language limits | Auth/session, ownership scope, Scale v2 payload or assignment, body profile/BIA, Alembic ownership or scale migrations, Google integrations | `backend/tests/test_scale_v2_contract.py`, `backend/tests/test_scale_sync_contract.py`, account-isolation integration suite (required) |
| `configurable-meals.md` | implemented (online-first) | Konto-private Mahlzeiten, Rezepte, Pläne und Verzehr | Meal routes/schemas/models, meal migrations, sync entity contract, meal API client or editor flow | `backend/tests/test_configurable_meals_contract.py`, `backend/tests/test_meal_account_isolation.py`, meal browser flow (required) |

Use [`fittrack-artifact-lifecycle`](../../.agents/skills/fittrack-artifact-lifecycle/SKILL.md)
when a change may invalidate an artifact. It requires an evidence-based outcome:
confirmed, revise, supersede, or retire.
