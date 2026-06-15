# ADR-003: Idempotent Sync via Natural Keys

**Status:** Accepted
**Date:** 2026-06-15

## Context

A sync tool must be safe to re-run repeatedly without creating duplicate objects or requiring manual cleanup. NetBox REST API is not natively idempotent — a `POST` to `/api/dcim/devices/` creates a new device every time.

Database IDs (NetBox internal primary keys) are unsuitable as stable identifiers because they change across backups, re-imports, and branching.

## Decision

Every sync uses **stable business keys (natural keys)** from vSphere to match NetBox objects:

| Entity | Natural Key |
|---|---|
| Device (ESXi host) | `(site, name)` |
| Cluster | `(site, name)` |
| Interface | `(device, name)` |
| IP Address | `(address, interface, vrf)` |
| VLAN | `(site, vid)` |
| InventoryItem | `(device, name, role)` |

Sync algorithm per entity: **lookup → PATCH if found → POST if new**.

- If the natural key matches an existing object, update it (PATCH).
- If no match, create (POST).
- No DELETE on re-run.

## Consequences

**Positive:**
- Safe to re-run any number of times.
- No duplicate objects in NetBox.
- Handles vSphere data changes gracefully (BIOS UUID, serial, CPU count etc.).

**Negative:**
- A change to a natural key (e.g. host rename) creates an orphan + new object, not a rename.
- Lookup performance requires NetBox fields that support natural-key queries (e.g. `name`, `site_id`).
- Natural key schema must be defined upfront and stable.

## Related

- `docs/vision.md` — Data Model Mapping: natural keys table.
- `docs/domains.md` — Aggregate design: natural key as aggregate identifier.
- `docs/SRS.md` — FR-07 (idempotent updates), FR-09 (natural keys).
- `docs/architecture.md` — API Design: upsert semantics.
