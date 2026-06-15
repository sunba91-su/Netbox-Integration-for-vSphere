# ADR-012: Separate Aggregates per Entity

**Status:** Accepted
**Date:** 2026-06-15

## Context

In DDD, an aggregate is a cluster of domain objects treated as a single unit. However, NetBox's REST API does not support transactional commits across entity types — creating a Device and its Interfaces requires two separate API calls, each with its own success/failure state.

Treating the entire sync as a single aggregate would imply transactional guarantees that the underlying API cannot provide.

## Decision

**Each NetBox entity type is its own aggregate root:**

| Aggregate | Entities |
|---|---|
| SiteAggregate | Site |
| ClusterAggregate | Cluster |
| DeviceAggregate | Device |
| InterfaceAggregate | Interface |
| IPAddressAggregate | IPAddress |
| VLANAggregate | VLAN |
| InventoryItemAggregate | InventoryItem |

- Each aggregate has a self-contained natural key.
- Aggregates reference each other by natural key (e.g., Device references Site by name).
- The sync engine enforces dependency order externally (see ADR-005).
- No cross-aggregate transactions attempted.

## Consequences

**Positive:**
- Mirrors NetBox REST API capabilities — no false transactional promises.
- Independent lifecycle per entity type.
- Simpler aggregate boundaries.

**Negative:**
- No atomic multi-entity creation.
- Orphaned children possible if parent creation fails after child creation.
- Sync engine must handle partial failures per aggregate.

## Related

- `docs/domains.md` — Aggregate definitions and boundaries.
- `docs/architecture.md` — Database Design: NetBox data model.
- `docs/SRS.md` — FR-06 (dependency ordering), FR-12 (partial failure handling).
