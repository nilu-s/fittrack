# Multi-account cutover runbook

1. Take and verify a database backup; enable maintenance mode.
   Rehearse against `backend/tests/fixtures/legacy-owner-rehearsal.json` before
   the maintenance window.
2. Set deployment-only `ALLOWED_GOOGLE_EMAILS` and `LEGACY_OWNER_EMAIL`.
3. Apply Alembic through revision 020, then let the designated legacy owner
   complete an allowed Google login. The login maps legacy `luis` records to
   that account exactly once. Apply the remaining revisions through head
   (currently 033) only after that login; revision 021 aborts if the nominated
   email resolves to anything other than exactly one account or if any
   account-owned orphan remains.
4. Register the ESP device ID and a hash of its dedicated device credential,
   create non-overlapping account ranges, then deploy v2 firmware.
5. Smoke-test 63 kg, 115 kg, discarded 87 kg and an idempotent retry.
6. On failure before revision 021, stop traffic and restore the verified
   backup; do not run ownership backfill against a different legacy-owner
   account. After the ownership-finalization revision, rollback is restore
   from that backup rather than choosing a different account mapping.
