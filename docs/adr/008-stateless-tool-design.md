# ADR-008: Stateless Tool Design

**Status:** Accepted
**Date:** 2026-06-15

## Context

Maintaining persistent state (a local database, checkpoint files, or offset tracking) adds complexity to deployment, failure recovery, and testing. Stateful tools require careful handling of corruption, concurrent access, and migration.

## Decision

The tool is **stateless**. It has no local database, no checkpoint files, and no persistent offset tracking.

- The only artifacts it produces are the lock file (`/tmp/nvs-sync.lock`) and log output.
- Every run re-reads the full vSphere inventory and reconciles against the full NetBox state.
- No "incremental since last run" tracking — always a full reconciliation.
- Crash recovery is trivial: re-run the sync.

## Consequences

**Positive:**
- Simple deployment — no database setup.
- Easy testing — no fixture state management.
- Crash recovery is immediate.
- Easy horizontal scaling (run multiple instances against different vCenters).

**Negative:**
- Every full sync re-reads all vSphere data, increasing API load.
- Not suitable for very large inventories where full reconciliation exceeds the sync window.
- No ability to detect "changed since last run" without comparing full state.

## Related

- `docs/architecture.md` — System Context: no persistent store.
- `docs/standards.md` — Deployment simplicity.
- `docs/SRS.md` — NFR-06 (stateless).
