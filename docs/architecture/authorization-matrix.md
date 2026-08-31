# Authorization matrix

| Resource | Principal | Action | Enforcement | Test |
| --- | --- | --- | --- | --- |
| Account-owned records | Browser account | read/write | verified session and ORM account scope | A-versus-B regression suite |
| Offline sync record | Browser account | create/update/delete | session account applied server-side; owner fields discarded | sync contract tests |
| Google token | Browser account | read/refresh/disconnect | `account_id` predicate | auth integration test |
| Google Fit / Calendar import | Browser account | import | current account token and account-scoped projection | integration contract tests |
| Scale v2 ingest | Registered device | create raw event | device key; no browser dependency | scale-v2 contract |
| Scale measurement | Assigned browser account | list/reject | ORM account scope | scale-v2 contract |
| Body profile | Browser account | read/write | verified session and `account_id` | scale-v2 contract |
