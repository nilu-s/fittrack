# System overview

```text
Google OIDC -> signed browser session -> current account -> scoped ORM/API
Renpho BLE -> ESP32 device key -> Scale v2 -> range assignment -> daily projection
```

| Module | Boundary | Normative source | Verification |
| --- | --- | --- | --- |
| `backend/app/routes/auth.py` | OIDC/session/account creation | multi-account spec §5.1 | backend tests |
| `backend/app/services/ownership.py` | account query/write scope | multi-account spec §4 | authorization tests |
| `backend/app/routes/scale_v2.py` | device ingest and private feed | multi-account spec §5.3–5.4 | scale-v2 contract tests |
| `esp32-scale-bridge/src/main.cpp` | raw device transport only | Scale v2 contract | PlatformIO build |
