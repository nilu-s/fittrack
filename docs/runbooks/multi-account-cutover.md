# Multi-account cutover runbook

1. Take and verify a database backup; enable maintenance mode.
2. Set deployment-only `ALLOWED_GOOGLE_EMAILS` and `LEGACY_OWNER_EMAIL`.
3. Apply Alembic revision 019, then let the designated legacy owner complete
   an allowed Google login. The login maps legacy `luis` records to that
   account exactly once.
4. Register the ESP device ID and a hash of its dedicated device credential,
   create non-overlapping account ranges, then deploy v2 firmware.
5. Smoke-test 63 kg, 115 kg, discarded 87 kg and an idempotent retry.
6. On failure, stop traffic and restore the verified backup; do not run
   ownership backfill against a different legacy-owner account.
