# ADR-014: Per-Host Storage Assignment

**Status:** Accepted
**Date:** 2026-06-15

## Context

In vSphere, a datastore is a storage volume mounted on one or more ESXi hosts. In NetBox, storage is represented as `InventoryItem` records with the role "Storage" assigned to a specific device (ESXi host).

There are two design approaches:
1. Create one NetBox InventoryItem per datastore (shared across hosts).
2. Create one per datastore **per mounted host** (N InventoryItems for N hosts).

vSphere API returns the exact set of mounted hosts per datastore via `datastore.host`.

## Decision

**Create one InventoryItem per datastore per mounted host:**

- Natural key: `(device, datastore_name, role="Storage")`.
- Description includes capacity, usage, and type in human-readable format (schema-agnostic).
- Storage backend vendor is omitted if unavailable from vSphere.
- If a host is removed from a datastore, the corresponding InventoryItem is reported as orphaned.

## Consequences

**Positive:**
- Enables query "what storage is mounted on this specific host?" in NetBox.
- Matches NetBox DCIM model (InventoryItem scoped to a device).
- Accurate representation of vSphere storage topology.

**Negative:**
- N× increase in InventoryItem count (one per mount point).
- Orphan cleanup required when datastore mappings change.
- Datastore-level information (total capacity, type) is duplicated across N items.

## Related

- `docs/vision.md` — Data Model Mapping: InventoryItem.
- `docs/domains.md` — InventoryItem aggregate design.
- `docs/SRS.md` — FR-14 (per-host datastore sync).
- `docs/architecture.md` — Database Design: InventoryItem.
