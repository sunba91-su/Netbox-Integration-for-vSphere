# ADR-005: Dependency-Order Entity Creation

**Status:** Accepted
**Date:** 2026-06-15

## Context

NetBox entities have foreign-key dependencies enforced at the API layer:
- A Device must reference an existing Site, Cluster, DeviceRole, and Manufacturer.
- An Interface must reference an existing Device.
- An IPAddress must reference an existing Interface.
- A VLAN must reference an existing Site.

Creating entities in the wrong order results in 400-level API errors.

## Decision

Entities are created and updated in a strict **topological dependency order**:

1. Site (closest to zero dependencies)
2. ClusterType, Manufacturer, DeviceRole (prerequisite metadata)
3. Cluster
4. Device (ESXi host)
5. VLAN
6. Interface
7. IPAddress
8. InventoryItem (datastores)

The sync engine processes entities layer-by-layer, collecting created/updated IDs for use as foreign keys in subsequent layers.

## Consequences

**Positive:**
- No foreign-key constraint violations during sync.
- Deterministic ordering — easy to debug.
- Each layer can be independently tested.

**Negative:**
- No parallelism within the entity creation phase.
- Must maintain the dependency order graph as entity types are added.
- A failure in an earlier layer blocks all later layers.

## Related

- `docs/domains.md` — Aggregate dependency order.
- `docs/SRS.md` — FR-06 (dependency ordering for entities).
- `docs/architecture.md` — Component Diagram: Sync Engine.
- `docs/vision.md` — Data Model: entity dependency table.
