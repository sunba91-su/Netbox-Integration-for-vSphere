# ADR-026: PID-Based Lock File

**Status:** Accepted
**Date:** 2026-06-15

## Context

Cron-driven sync may schedule a new run before the previous run completes (if the sync takes longer than the cron interval). Concurrent sync runs can:
- Corrupt NetBox data through interleaved create/update operations.
- Overload the vCenter API with duplicate requests.
- Produce confusing interleaved log output.
- Undermine the dependency-order guarantee (see ADR-005).

## Decision

A **PID-based lock file** at `/tmp/nvs-sync.lock` prevents concurrent execution:

```
/tmp/nvs-sync.lock
  Contains: <PID>
```

- On startup, the tool checks if `/tmp/nvs-sync.lock` exists.
- If it exists, read the PID and call `os.kill(pid, 0)` to check if the process is alive.
- If the process is alive → exit 0 (previous run still in progress).
- If the process is dead (stale lock) → remove the lock and proceed.
- Write the current PID to the lock file.
- `atexit` and signal handlers ensure cleanup on normal/crash exit.
- Exit 0 if locked (not an error — just skip).

## Consequences

**Positive:**
- Prevents concurrent runs reliably.
- Stale lock detection prevents permanent blocking after crashes.
- Simple — no external dependencies (Redis, etcd).

**Negative:**
- Not suitable for distributed deployments (multiple machines).
- Stale PID edge case: PID reuse on systems with short-lived PIDs (unlikely but possible).
- Lock file path is hardcoded to `/tmp/`.

## Related

- `docs/SRS.md` — NFR-17 (concurrency prevention).
- `docs/architecture.md` — Security Design: lock file.
- `docs/standards.md` — Security requirements.
