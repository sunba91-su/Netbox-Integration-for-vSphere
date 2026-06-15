# ADR-028: Custom Fields for vSphere Data

**Status:** Accepted
**Date:** 2026-06-15

## Context

vSphere properties have no direct NetBox core field equivalents:
- Managed Object Reference (MOR) — unique vCenter identifier for every object.
- BIOS UUID — unique hardware identifier for ESXi hosts.
- ESXi version and build — software version tracking.
- Power state — operational status.
- Cluster MOR — for associating hosts with clusters.
- Datastore capacity/type — storage metadata.

NetBox supports custom fields on most models (Device, Cluster, Interface, etc.). Custom fields are queryable, filterable, and appear in the NetBox UI.

## Decision

Store vSphere-specific metadata as **NetBox Custom Fields**:

| Model | Custom Field | Type | Description |
|---|---|---|---|
| Device | `nvs_vsphere_mor` | Text | vCenter MOR (e.g., `host-123`) |
| Device | `nvs_bios_uuid` | Text | ESXi BIOS UUID |
| Device | `nvs_esxi_version` | Text | ESXi version string |
| Device | `nvs_power_state` | Text | Power state (poweredOn/poweredOff) |
| Device | `nvs_connection_state` | Text | Connection state (connected/disconnected) |
| Device | `nvs_vcenter` | Text | vCenter hostname |
| Cluster | `nvs_vsphere_mor` | Text | vCenter cluster MOR |
| Cluster | `nvs_datacenter` | Text | vSphere datacenter name |
| Interface | `nvs_vsphere_mor` | Text | vCenter port group MOR |
| Interface | `nvs_mac_address` | Text | MAC address (override if needed) |
| InventoryItem | `nvs_vsphere_mor` | Text | vCenter datastore MOR |
| VLAN | `nvs_vsphere_mor` | Text | vCenter port group MOR |

Custom fields are prefixed with `nvs_` (NetBox vSphere) to avoid collisions. The tool creates/validates them during bootstrap (see ADR-007).

## Consequences

**Positive:**
- Preserves NetBox core schema — no monkey-patching or abuse of existing fields.
- Extensible — new vSphere properties can be added as new custom fields.
- Queryable via NetBox API and UI.

**Negative:**
- Custom field creation requires additional NetBox API permissions.
- Some custom fields are one-to-one with existing NetBox fields (e.g., MAC address could use core field but custom field provides vSphere source-of-truth marker).
- Custom fields cannot be removed if they contain data (NetBox limitation).

## Related

- `docs/vision.md` — Custom Fields table.
- `docs/architecture.md` — Database Design: Custom Fields Inventory.
- `docs/SRS.md` — FR-04 (custom field creation), FR-05 (custom field mapping).
