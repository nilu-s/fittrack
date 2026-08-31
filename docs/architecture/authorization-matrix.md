# Authorization matrix

| Resource | Principal | Action | Enforcement | Test |
| --- | --- | --- | --- | --- |
| Account-owned records | Browser account | read/write | verified session and ORM account scope | A-versus-B regression suite |
| Google token | Browser account | read/refresh/disconnect | `account_id` predicate | auth integration test |
| Scale v2 ingest | Registered device | create raw event | device key; no browser dependency | scale-v2 contract |
| Scale measurement | Assigned browser account | list/reject | ORM account scope | scale-v2 contract |
