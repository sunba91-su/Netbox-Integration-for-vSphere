# ADR-037: Fail-Fast vs Continue on Partial Failure

**Status:** Accepted
**Date:** 2026-06-15

## Context

During a sync run, two categories of errors can occur:
1. **Fatal errors:** vCenter unreachable, NetBox API down, config invalid, lock held by live process. The run cannot proceed.
2. **Partial errors:** A single device fails to update (e.g., foreign key missing), a specific datastore cannot be created. Other entities can still be processed.

Treating partial errors as fatal would lose progress on all other entities. Treating fatal errors as recoverable would produce partial, misleading results.

## Decision

**Fail fast on configuration, connection, and lock errors.** Continue on individual entity failures.

| Error Type | Behaviour | Exit Code |
|---|---|---|
| Invalid config / missing credentials | Abort before any API calls | 2 |
| vCenter connection failure | Abort before sync | 2 |
| NetBox API connection failure | Abort before sync | 2 |
| Lock held by live process | Exit 0 (skip — not an error) | 0 |
| Single entity creation/update failure | Log error, continue | 1 (if any) |
| Bootstrap metadata failure | Abort (metadata is prerequisite) | 2 |

Exit codes:
- **0:** Success (or skipped due to lock).
- **1:** Partial success — some entities failed.
- **2:** Fatal error — no sync performed.

## Consequences

**Positive:**
- Best-effort sync preserves progress on successful entities.
- Clear exit code semantics for automation.
- Fatal errors prevent wasted API calls.

**Negative:**
- Partial failure exit (1) may be missed by cron scripts that only check for non-zero.
- Entity-level errors may cascade (e.g., interface fails because device failed earlier).
- Requires careful ordering of failure checks.

## Related

- `docs/SRS.md` — NFR-13 (error handling), NFR-14 (exit codes).
- `docs/architecture.md` — Error handling strategy.
