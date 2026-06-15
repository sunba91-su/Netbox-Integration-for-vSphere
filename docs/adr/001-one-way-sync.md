# ADR-001: One-Way Sync Direction

**Status:** Accepted
**Date:** 2026-06-15

## Context

The integration spans two systems — vSphere (compute source of truth) and NetBox (network/infrastructure CMDB). Designing as bidirectional sync introduces conflict resolution, greater blast radius, and significant operational risk. vCenter's API surface is not designed for programmatic writes, and accidental mutations could destabilise production compute.

No requirements demand writing back to vSphere.

## Decision

Sync is strictly one-way: **vSphere → NetBox**. NetBox is always the target. vSphere is always authoritative for the synced data.

- NetBox custom fields store vSphere metadata (MOR, BIOS UUID, power state).
- The sync tool never performs vSphere API write operations.
- No support for "correcting" vSphere from NetBox.

## Consequences

**Positive:**
- Simple, auditable data flow.
- No conflict resolution logic required.
- No risk of destabilising vCenter.
- NetBox acts as an immutable snapshot of vSphere state.

**Negative:**
- NetBox may contain stale data if vSphere is unreachable during a sync run.
- No mechanism to propagate NetBox annotations (e.g. custom notes) back to vSphere.
- Operators cannot correct vSphere data through NetBox.

## Related

- `docs/vision.md` — Sync direction and data flow.
- `docs/SRS.md` — FR-01 (one-way sync from vSphere).
- `docs/architecture.md` — System Context: unidirectional arrow.
- `docs/domains.md` — Bounded Context: Sync Orchestration.
