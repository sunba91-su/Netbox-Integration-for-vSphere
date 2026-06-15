# ADR-004: No Implicit Deletions

**Status:** Accepted
**Date:** 2026-06-15

## Context

If a host is removed from vSphere, the next sync run will detect it is "missing". The tool must decide: delete it from NetBox, deactivate it, or leave it.

Deleting NetBox objects is risky:
- Cascading deletes affect dependent objects (interfaces, IPs, inventory items).
- Production recoverability is poor (NetBox has no recycle bin).
- The delete might be premature if vSphere is temporarily unreachable (network blip, maintenance).

## Decision

**The tool NEVER deletes NetBox objects by default.** The sync only creates and updates.

- Objects present in vSphere and NetBox → update.
- Objects absent from vSphere but present in NetBox → report in the diff.
- A `--prune` flag enables deactivation logic: sets status to "Offline" or "Decommissioning" (never hard-delete).
- The report includes a list of orphaned objects that would be pruned.

## Consequences

**Positive:**
- Safe default — no accidental data loss.
- `--prune` requires explicit opt-in, preventing operator error.
- Orphan report provides visibility into drift.

**Negative:**
- NetBox accumulates stale objects without `--prune`.
- `--prune` requires human review of the report before invocation.
- Soft-deactivation leaves historical references intact but may confuse NetBox consumers.

## Related

- `docs/vision.md` — Data Model: deactivation strategy.
- `docs/SRS.md` — FR-10 (no deletion by default), FR-11 (prune flag).
- `docs/architecture.md` — API Design: idempotent upsert, no delete.
