# Vision: NetBox Integration for vSphere

> **Bridge the gap between virtual infrastructure and network source of truth.**
>
> *One-way, cron-driven synchronization from VMware vSphere into NetBox, treating
> the hypervisor as the authoritative source for compute, storage, and network
> topology.*

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Problem Statement](#2-problem-statement)
3. [Solution Architecture](#3-solution-architecture)
4. [Data Model Mapping](#4-data-model-mapping)
5. [InventoryItem & Storage Device-Assignment Strategy](#5-inventoryitem--storage-device-assignment-strategy)
6. [IPAddress Role Decision Matrix](#6-ipaddress-role-decision-matrix)
7. [Vault Integration for Secrets Management](#7-vault-integration-for-secrets-management)
8. [Technical Vision](#8-technical-vision)
9. [Design Principles](#9-design-principles)
10. [Implementation Roadmap](#10-implementation-roadmap)
11. [Operational Considerations](#11-operational-considerations)
12. [Out of Scope (v1)](#12-out-of-scope-v1)

---

## 1. Executive Summary

**Problem.** Organisations running VMware vSphere lack an automated,
maintainable pipeline that keeps their NetBox instance consistent with the live
virtual datacentre. Infrastructure teams manually register ESXi hosts, update
VLAN inventories, track hardware lifecycles, and reconcile storage capacity —
work that is error-prone, stale by the time it is recorded, and does not scale
beyond a handful of clusters.

**Solution.** A Python CLI package (`netbox-vsphere-sync`) that connects to a
single vCenter Server instance per run, reads the full inventory (datacentres,
clusters, hosts, networks, interfaces, hardware, datastores), and reconciles it
against a NetBox 4.5+ instance using the REST API (via `pynetbox`). The sync
is **one-way** (vSphere → NetBox), **idempotent**, and designed to run on a
cron schedule. Credentials can be sourced from HashiCorp Vault or environment
variables.

**Design tenets.**

| Tenet | Rationale |
|---|---|
| vSphere is source of truth | NetBox is the CMDB *output*, not the controller of compute. |
| Idempotent by default | Re-running the sync is safe; no duplicate objects, no stray deletes. |
| Dependency-order creation | Objects are created in topological order (Site → Cluster → Device → Interface → Inventory). |
| Dry-run first | Every sync can be previewed without making changes. |
| Minimal NetBox assumptions | The tool bootstraps its own Device Roles, Cluster Types, and Manufacturers if they do not exist. |

**Key metrics of success.**

- A single `netbox-vsphere-sync` command reconciles an entire vSphere
  inventory in under 5 minutes (tested against 500+ hosts).
- Zero manual data entry for synced object types after initial setup.
- No duplicate or orphan records caused by the sync tool.

---

## 2. Problem Statement

### 2.1 Current State

Most teams manage NetBox data through one or more of:

- **Manual entry** via the NetBox UI — laborious, inconsistent, always out of
  date.
- **Ad-hoc scripts** — single-use, unmaintained, no error handling, no logging.
- **Spreadsheet imports** — a batch CSV upload that is already stale.
- **Commercial tools** — expensive, tightly coupled, or do not support the
  vSphere-NetBox bridge.

None of these approaches provide:

- A repeatable, auditable sync process.
- Clear visibility into what changed on each run.
- Safe dry-run capabilities.
- Graceful handling of transient vCenter or NetBox outages.

### 2.2 Why One-Way?

Making NetBox write back to vSphere introduces enormous risk:

- vCenter APIs are not designed for external writes to host configuration.
- Conflict resolution is non-trivial (which system wins for a given field?).
- Operational blast radius: a bug in the sync tool could reconfigure live
  networking or compute.

**One-way sync limits the blast radius to stale data in NetBox**, which is
detectable and recoverable. vSphere remains the single source of operational
truth.

### 2.3 Why Periodic (Cron)?

- vSphere does not expose a simple, universal change-data-capture stream.
- Property Collector polling is expensive and brittle across vCenter versions.
- A 5–15 minute cron window is acceptable for CMDB freshness in nearly all
  organisations.
- Cron is infrastructure-agnostic (runs on a VM, container, or Kubernetes
  CronJob).

---

## 3. Solution Architecture

### 3.1 High-Level Data Flow

```
┌──────────────┐     ┌──────────────────────┐     ┌──────────────┐
│   vCenter    │────▶│  netbox-vsphere-sync  │────▶│   NetBox     │
│  (PyVmomi)   │     │  (sync engine)        │     │  (pynetbox)  │
└──────────────┘     └──────────────────────┘     └──────────────┘
       │                       │                          │
       │                       │  ┌─────────────┐        │
       │                       │  │  Config      │        │
       │                       │  │  (YAML/Env)  │        │
       │                       │  └─────────────┘        │
       │                       │  ┌─────────────┐        │
       │                       │  │  Vault       │        │
       │                       │  │  (optional)  │        │
       │                       │  └─────────────┘        │
       │                       │  ┌─────────────┐        │
       │                       │  │  Log / Audit │        │
       │                       │  │  (structured │        │
       │                       │  │   to stdout) │        │
       │                       │  └─────────────┘        │
```

### 3.2 Sync Engine Pipeline

Each sync run follows a strict pipeline:

1. **Authenticate** — resolve credentials (Vault → env → config → flags).
2. **Bootstrap** — ensure required NetBox metadata exists (Manufacturer,
   Device Role, Cluster Type, Site → Cluster mapping).
3. **Collect** — fetch all entities from vCenter via paginated PyVmomi queries.
4. **Fetch** — fetch corresponding entities from NetBox (paginated, brief
   where possible).
5. **Diff** — compute creates, updates, and (optionally) deactivations.
6. **Apply** — execute changes in dependency order, with per-entity logging.
7. **Report** — print summary table with counts (created / updated /
   unchanged / errors).

### 3.3 NetBox Readiness (Bootstrap)

The sync tool creates these NetBox records on first run if absent:

| NetBox Object | Value | Purpose |
|---|---|---|
| Manufacturer | `VMware Inc.` | Device type manufacturer for ESXi hosts |
| Device Role | `ESXi Server` | Role assigned to every synced host device |
| Cluster Type | `vSphere Cluster` | Type assigned to each synced cluster |
| Cluster Group | (configurable) | Optional grouping for clusters |
| InventoryItem Role | `Storage` | Role for datastore inventory items |
| InventoryItem Role | `Hardware` | Fallback role for unidentified hardware |
| Site → vCenter DC | (per datacentre) | Top-level site for each vSphere datacenter |

The bootstrapping behaviour is explicitly documented and can be disabled via
configuration.

---

## 4. Data Model Mapping

### 4.1 Entity Map

| # | vSphere Entity | NetBox Entity | NetBox App | Key Fields |
|---|---|---|---|---|
| 1 | **Datacenter** | `Site` | DCIM | `name` ← datacenter name, `slug` ← auto, `custom_fields.vcenter_mor` |
| 2 | **Cluster** | `Cluster` | Virtualization | `name`, `type` = "vSphere Cluster", `site` = mapped DC, `custom_fields.vcenter_mor` |
| 3 | **ESXi Host** | `Device` | DCIM | `name` ← FQDN, `role` = "ESXi Server", `device_type` ← from `hardware.biosInfo`, `site` ← DC, `cluster` ← Cluster, `status` ← connection state |
| 4 | **Port Group** | `VLAN` | IPAM | `vid` ← from vSphere or reserved range, `name`, `site` ← DC, `description` ← "VM Network" / "VMkernel" |
| 5 | **VMkernel Interface** | `Interface` | DCIM | `device` ← parent ESXi, `name` ← vmk name, `type` = "virtual", `enabled` = true, `mtu`, `mac_address`, `description` |
| 6 | **Kernel IP** | `IPAddress` | IPAM | `address` ← CIDR, `interface` ← parent Interface, `status` = "active", `role` ← decision matrix |
| 7 | **Hardware** | `InventoryItem` | DCIM | `device` ← parent ESXi, `name` ← component name, `manufacturer` ← vendor, `part_id`, `serial`, `description`, `role` ← "CPU" / "Memory" / "Controller" / "NIC" / "HBA" / "BIOS" |
| 8 | **Datastore** | `InventoryItem` | DCIM | `device` ← each ESXi host per mount, `name` ← datastore name, `role` = "Storage", `description` ← capacity + type |

### 4.2 Dependency Graph (Creation Order)

```
Site (vSphere DC) ────┬─── Cluster
                      ├─── VLAN (Port Group)
                      │
Device (ESXi Host) ───┤   (depends on Site + Cluster)
                      │
                      ├─── Interface (VMkernel)  ─── IPAddress
                      ├─── InventoryItem (HW)
                      └─── InventoryItem (Datastore)
```

The sync engine enforces this order. If a dependency is missing, the parent
object is created first (or a warning is emitted with the specific identifier).

### 4.3 Natural Key Strategy

To make sync runs idempotent, every object must be matched by a stable key:

| NetBox Object | Natural Key | Notes |
|---|---|---|
| Site | `name` | Unique by convention |
| Cluster | `name` + `site_id` | Clusters are namespaced by datacenter |
| Device | `name` | Host FQDN is unique per NetBox instance |
| VLAN | `vid` + `site_id` | VLANs are namespaced by site |
| Interface | `device_id` + `name` | Interface names are unique per device |
| IPAddress | `address` | CIDR is unique |
| InventoryItem | `device_id` + `name` + `role` | Component name per device per role |

### 4.4 Datacenter → Site (Field-Level)

```
vSphere: Datacenter              NetBox: dcim.Site
──────────────────────────────────────────────────
name                             name, slug  (slug auto-derived from name)
path (folder path)               description  (e.g., "/Datacenters/DC1")
managed-object-reference         custom_field["vcenter_mor"]
```

- **Natural key:** `name` (unique).
- **Conflict:** If a Site with the same name exists but is not managed by this
  tool, the run logs a WARNING and skips it.

### 4.5 Cluster → Cluster (Virtualization)

```
vSphere: ClusterComputeResource   NetBox: virtualization.Cluster
──────────────────────────────────────────────────────────────────
name                              name
datacenter → Site                 site  (resolved from DC mapping)
managed-object-reference          custom_field["vcenter_mor"]
haEnabled                         custom_field["vcenter_ha_enabled"]
drsEnabled                        custom_field["vcenter_drs_enabled"]
drsAutomationLevel                custom_field["vcenter_drs_level"]
totalCPU (MHz)                    custom_field["vcenter_cluster_cpu_mhz"]
totalMemory (MB)                  custom_field["vcenter_cluster_memory_mb"]
```

- **type:** Always `"vSphere Cluster"` (bootstrapped).
- **group:** Optional, configurable in YAML.
- **Natural key:** `name` *scoped per Site* (clusters in different DCs can
  share a name).
- **Lookup order:** `name` + `site_id` → fallback to `name` across all sites
  → create if neither match.

### 4.6 ESXi Host → Device

```
vSphere: HostSystem                    NetBox: dcim.Device
─────────────────────────────────────────────────────────────
name (FQDN)                            name
hardware.biosInfo (model)              device_type → resolved or created
hardware.vendor (e.g., "VMware Inc")   device_type.manufacturer
Cluster → Cluster                      cluster
Datacenter → Site                      site
summary.config.product.version         custom_field["vcenter_esxi_version"]
summary.config.product.build           custom_field["vcenter_esxi_build"]
summary.runtime.connectionState        status  (see mapping below)
summary.runtime.powerState             custom_field["vcenter_power_state"]
summary.hardware.numCpuCores           custom_field["vcenter_cpu_cores"]
summary.hardware.numCpuThreads         custom_field["vcenter_cpu_threads"]
summary.hardware.cpuModel              custom_field["vcenter_cpu_model"]
summary.hardware.memorySize (bytes)    custom_field["vcenter_memory_bytes"]
managed-object-reference               custom_field["vcenter_mor"]
```

**Connection State → Device Status mapping:**

| vSphere State | NetBox Status |
|---|---|
| `connected` | Active |
| `disconnected` | Offline |
| `notResponding` | Failed |
| `maintenance` | Maintenance (custom status if available, else Offline) |

**DeviceType / Manufacturer handling:**
- Manufacturer name derived from `hardware.vendor`. If blank, use `"VMware Inc"`.
- Device model from `hardware.biosInfo` (e.g., `"PowerEdge R640"`,
  `"ProLiant DL380 Gen10"`).
- On each sync, look up Manufacturer by name and DeviceType by model +
  manufacturer. If either is missing, create it.

### 4.7 Port Group → VLAN

```
vSphere: DistributedPortGroup / Network   NetBox: ipam.VLAN
─────────────────────────────────────────────────────────────
name                                       name
datacenter → Site                          site
─                                           vid  (see allocation below)
vlanTag (if set)                           vid  (direct when tagged)
networkType (e.g., "vmkernel")             description
managed-object-reference                   custom_field["vcenter_mor"]
```

**VLAN ID allocation strategy (configurable):**

| Strategy | When | Behaviour |
|---|---|---|
| `from_portgroup` | Port group has `vlanTag` | Use the tag directly. |
| `reserved_range` | Port group is VLAN 0 (access) or no tag | Allocate from reserved range (e.g., 4000–4094). |
| `auto_allocate` | No tag / no reserved range | Skip — log WARNING, do not create VLAN. |

- **Natural key:** `vid` + `site_id`.

### 4.8 VMkernel Interface → Interface + IPAddress

```
vSphere: HostVirtualNic                   NetBox: dcim.Interface
─────────────────────────────────────────────────────────────────
device (FQDN)                              device
key / deviceLabel (e.g., "vmk0")           name
spec.mac                                   mac_address
spec.mtu                                   mtu
spec.portgroup                             description  (e.g., "vMotion - PG-vMotion")
spec.enabled                               enabled  → True
─                                           type     → "virtual"

vSphere: HostVirtualNic.spec.ip            NetBox: ipam.IPAddress
─────────────────────────────────────────────────────────────────
ipAddress (e.g., "10.0.1.10")             address  → CIDR
subnetMask (e.g., "255.255.255.0")        (combined into address field)
─                                           interface  (parent Interface)
─                                           status  → "active"
─                                           role    → decision matrix (§6)
```

- **Multiple IPs per interface:** vSphere supports multiple IPs on a single
  vmk. Each is synced as a separate IPAddress (natural key = `address`).
- **IPv6:** Synced identically. No role special-casing for IPv6 vs IPv4.

### 4.9 Hardware Inventory → InventoryItem

```
vSphere: hardware components (HostSystem)  NetBox: dcim.InventoryItem
─────────────────────────────────────────────────────────────────────
─                                             device (parent Device)
name (derived)                                 name
─                                             role  (see table §5.1)
vendor                                         manufacturer
model                                          part_id
serialNumber                                   serial
description                                    description
─                                             discovered → True
```

**Natural key:** `device_id` + `name` + `role`.
**Updates:** Only `description`, `serial`, `part_id`, and `manufacturer` are
PATCHed on re-sync. Component removal from vSphere never deletes NetBox items.

---

## 5. InventoryItem & Storage Device-Assignment Strategy

### 5.1 Hardware Inventory Parsing Pipeline

The sync engine extracts hardware components from the vSphere `HostSystem`
object by traversing the property tree.

```
HostSystem (PyVmomi)
│
├─ hardware.cpuPkg[]              → CPU(s)
├─ hardware.memoryModules[]       → DIMM(s)
├─ storageSystem.storageDeviceInfo.scsiTopology → Disk/Controller(s)
├─ networkSystem.networkInfo.pnic → NIC(s)
├─ networkSystem.networkInfo.hba  → HBA(s) / FC adapters
├─ hardware.biosInfo              → BIOS/Firmware
└─ runtime.powerState             → skipped (runtime, not hardware)
```

**Extractor detail per component:**

| Component | Source | Name Pattern | Manufacturer | Part ID | Serial | Role |
|---|---|---|---|---|---|---|
| CPU | `hardware.cpuPkg[]` | `"CPU-{index}"` | `vendor` (Intel/AMD) | `description` (model) | — | `CPU` |
| DIMM | `hardware.memoryModules[]` | `"DIMM-{locator}"` | `vendor` | `partNumber` | `serialNumber` | `Memory` |
| Disk | `storageSystem.scsiTopology` | `"{vendor} {model}"` | `vendor` | `model` | `serialNumber` | `Storage` |
| NIC | `networkSystem.pnic[]` | `"{device}"` | `vendor` | `model` | `serialNumber` | `NIC` |
| Controller | `storageSystem.hostBusAdapter[]` | `"{model}"` | `vendor` | `model` | `serialNumber` | `Controller` |
| HBA | `networkSystem.hba[]` | `"{model}"` | `vendor` | `model` | `serialNumber` | `HBA` |
| BIOS | `hardware.biosInfo` | `"BIOS"` | `vendor` | `biosVersion` | — | `BIOS` |

**Parse-time decisions:**

- **Empty/missing fields:** If `vendor` is empty, fall back to `"Unknown"` for
  the manufacturer lookup. If `serialNumber` is empty, the item is created
  without a serial.
- **Role enforcement:** Roles are configurable in YAML. If a role is not in
  NetBox's `InventoryItemRole` list, the tool logs a warning and uses a
  configurable fallback (default: `"Hardware"` generic role, bootstrapped).
- **De-duplication per run:** Components are keyed by `(name, role,
  manufacturer)` within a device. If two components have the same key, only
  the first is emitted and a debug log notes the duplicate.

### 5.2 InventoryItem Create/Update Rules

```
On each sync run, for each ESXi host:

1. Fetch existing InventoryItems from NetBox
   (?device=device_id, ?brief=True, paginated)

2. Fetch live hardware from vSphere

3. For each live component:
   ├─ Natural key = (device_id, name, role)
   ├─ Exists in NetBox?
   │   ├─ YES: PATCH if description/serial/part_id changed
   │   └─ NO:  POST new InventoryItem
   └─ (never deletes — idempotent safety)

4. After all devices processed:
   └─ Log summary per host
```

**What triggers a PATCH:**

| Field | Source | Update Condition |
|---|---|---|
| `description` | Component description | Only if current value differs |
| `serial` | Component serial number | Only if not empty and differs |
| `part_id` | Component part number | Only if current value differs |
| `manufacturer` | Resolved manufacturer ID | Only if current value differs |
| `discovered` | `True` | Never updated after creation |

**What does NOT trigger a PATCH:** `role`, `name`, `device` — these are part
of the natural key and are immutable after creation. A change in these would
mean the component is different; the old item remains orphaned.

### 5.3 Storage (Datastore) Device-Assignment Strategy: Per-Host

Each datastore accessible to multiple ESXi hosts produces one InventoryItem
*per host*.

```
vSphere model:

  Datastore-1
    ├─ mounted on: esxi-01a (accessible)
    ├─ mounted on: esxi-01b (accessible)
    ├─ mounted on: esxi-01c (accessible)
    └─ type: VMFS

NetBox model (per-host):

  InventoryItem on Device "esxi-01a":
    name = "Datastore-1"
    role = "Storage"
    description = "capacity: 10.9 TiB | type: VMFS | backend: HPE 3PAR"
    custom_field["storage_free_bytes"] = 4294967296000
    custom_field["storage_mounted_hosts"] = 3

  InventoryItem on Device "esxi-01b":   ← same datastore, different parent
    name = "Datastore-1"
    ...
  InventoryItem on Device "esxi-01c":   ← same datastore, different parent
    name = "Datastore-1"
    ...
```

**Natural key:** `(device_id, name, role)`

- `device_id` = NetBox device ID of the ESXi host.
- `name` = datastore name from vSphere.
- `role` = `"Storage"` (constant).

**Implications:**
- A datastore mounted on 3 hosts produces 3 InventoryItems.
- If a host is added to the cluster, a new item is created on the next sync.
- If a host is removed, the item is NOT deleted (idempotent safety) but logged
  in the "orphaned items" report.

**Why per-host rather than shared:**

| Concern | Per-Host | Site-Level | First-Host |
|---|---|---|---|
| Query which hosts see this datastore | Easy (query by name) | Impossible | Incomplete |
| Query what storage on this host | Easy | Easy | Easy |
| Item count | 3× per datastore | 1× per datastore | 1× per datastore |
| Delete safety | Orphaned items per host | Single point of truth | Ambiguous |
| Matches NetBox DCIM model | YES — per-device | Friction — needs null device | Compromise |

### 5.4 Datastore Fields

| vSphere Datastore Field | NetBox Field | Notes |
|---|---|---|
| `name` | `name` | |
| `summary.capacity` (bytes) | `description` | Formatted: `"capacity: {size} | type: {type} | backend: {vendor}"` |
| `summary.freeSpace` (bytes) | custom_field `storage_free_bytes` | Raw bytes for aggregation |
| `summary.type` | custom_field `storage_backend_type` | `VMFS`, `NFS`, `vSAN`, `VVol` |
| `summary.multipleHostAccess` | custom_field `storage_shared` | `true` / `false` |
| managed-object-reference | custom_field `vcenter_mor` | Stable identifier |

**Human-readable `description` format:**
```
capacity: 10.9 TiB | used: 6.2 TiB (57%) | type: VMFS | backend: HPE 3PAR
```

The description is rebuilt every sync from live vSphere data. If capacity or
free space changes, the description is PATCHed.

### 5.5 Storage-Specific Sync Steps

```
sync_storage(vsphere_client, netbox_client, config):

1. For each Datacenter:
   ├─ Fetch all Datastores from vSphere
   └─ For each Datastore:
       ├─ Fetch all HostSystems that mount it
       │   (host.datastore property)
       └─ For each HostSystem:
           ├─ Resolve NetBox Device ID from host FQDN
           ├─ Build InventoryItem payload
           ├─ Lookup by natural key (device_id, name, "Storage")
           ├─ Exists? → PATCH if free_space / capacity changed
           └─ Missing? → POST new InventoryItem

2. After all datastores processed:
   └─ Log summary: "Storage: 45 created, 3 updated, 0 errors"
```

### 5.6 Conflict / Edge Cases

| Scenario | Behaviour |
|---|---|
| Host moved between clusters | On next sync: cluster assignment updated. InventoryItems follow device. |
| Datastore renamed | Old item orphaned (key mismatch). New one created. Logged WARNING. |
| Datastore capacity expanded (VMFS) | On next sync: `description` PATCHed with new capacity. No data loss. |
| vCenter partially down (some hosts unreachable) | Sync continues for reachable hosts. Skipped hosts logged INFO. |
| NetBox role "Storage" does not exist | Bootstrapped at sync start. |

---

## 6. IPAddress Role Decision Matrix

### 6.1 VMkernel Service Types

Each VMkernel interface in vSphere can be tagged with one or more services.
The sync reads `HostVirtualNic.spec.ipRouteConfig` and the associated port
group to determine the interface's purpose.

| Service Tag (vSphere) | Port Group Convention | Typical Use | IPAddress Role |
|---|---|---|---|
| *none (default)* | `Management Network`, `MGMT-*` | ESXi management | `loopback` |
| `vmotion` | `vMotion-*`, `VMK_*` | Live migration | `anycast` |
| `vsan` | `vSAN-*`, `VSAN_*` | vSAN backend | `anycast` |
| `faultToleranceLogging` | `FT-*`, `FT_*` | Fault Tolerance | `anycast` |
| `vSphereReplication` | `VR-*`, `HBR-*` | Replication | `anycast` |
| `vSphereBackupNFC` | `Backup-*` | Backup traffic | `loopback` |
| `management` | `MGMT-*` (explicit) | Management | `loopback` |
| `vmKernel` (general) | `VMK-*` | General-purpose | unset |
| *VM Network* | `VM-*`, `Prod-*` | Guest traffic | (not synced) |

### 6.2 Decision Matrix

```
┌─────────────────────┬──────────────────────┬──────────────────────────────┐
│ Criteria             │ Condition            │ IPAddress Role              │
├─────────────────────┼──────────────────────┼──────────────────────────────┤
│ Interface type       │ VMkernel (vmk*)      │ See service-based matrix    │
│                      │ VM Network           │ (not synced — VM scope)     │
├─────────────────────┼──────────────────────┼──────────────────────────────┤
│ Service (if set)     │ vmotion              │ anycast                      │
│                      │ vsan                 │ anycast                      │
│                      │ faultToleranceLogging│ anycast                      │
│                      │ vSphereReplication   │ anycast                      │
│                      │ vSphereBackupNFC     │ loopback                     │
│                      │ management           │ loopback                     │
├─────────────────────┼──────────────────────┼──────────────────────────────┤
│ No service tag set   │ Port group name      │ Match via config prefix map │
│                      │ matches pattern      │ (see §6.3)                  │
│                      ├──────────────────────┼──────────────────────────────┤
│                      │ No pattern matched   │ None (omit role field)      │
├─────────────────────┼──────────────────────┼──────────────────────────────┤
│ IP is link-local     │ 169.254.x.x / fe80:: │ Skip — never create         │
├─────────────────────┼──────────────────────┼──────────────────────────────┤
│ vCenter reports down │ Connection lost      │ status = "decommissioning"  │
└─────────────────────┴──────────────────────┴──────────────────────────────┘
```

### 6.3 Configurable Port Group Prefix → Role Mapping

Since vSphere service tags are not always populated, the sync supports
prefix-based matching on the port group name as a fallback:

```yaml
sync:
  ipaddress_role_mapping:
    rules:
      - prefix: "vMotion-"
        role: "anycast"
      - prefix: "vSAN-"
        role: "anycast"
      - prefix: "FT-"
        role: "anycast"
      - prefix: "VR-"
        role: "anycast"
      - prefix: "HBR-"
        role: "anycast"
      - prefix: "MGMT-"
        role: "loopback"
      - prefix: "Backup-"
        role: "loopback"
      - prefix: "Management"
        role: "loopback"
    default_role: null
```

**Evaluation order:**

1. If vSphere reports a service tag on the VMkernel interface, use the
   service-based matrix (§6.1). This takes precedence.
2. If no service tag, iterate prefix rules in order. First match wins.
3. If no prefix matches, use `default_role` (null = omit role field).

### 6.4 Example Walkthrough

```
Interface: vmk0   Port Group: "Management Network"   Service: [management]
  IP: 10.0.0.10/24    →  role = "loopback"    (service-based)

Interface: vmk1   Port Group: "vMotion-PG"            Service: [vmotion]
  IP: 10.10.0.10/24  →  role = "anycast"     (service-based)

Interface: vmk2   Port Group: "Prod-VMK-42"           Service: []
  IP: 10.20.0.10/24  →  role = null           (no prefix match → omit)

Interface: vmk3   Port Group: "vSAN-Data"             Service: []
  IP: 10.30.0.10/24  →  role = "anycast"      (prefix "vSAN-" matches)
```

### 6.5 IPAddress Field Assembly

```python
{
    "address":     f"{ip}/{prefix_length}",   # e.g., "10.0.0.10/24"
    "interface":   interface_id,
    "status":      "active",
    "role":        role or None,               # from decision matrix
    "dns_name":    parent_device_fqdn,          # optional
    "description": f"vmk{idx} on {portgroup}",
}
```

- **Prefix length:** Derived from the subnet mask reported by vSphere
  (`HostIPConfig.subnetMask` / `prefixLength`).
- **Multiple IPs per interface:** Each synced as a separate IPAddress
  (natural key = `address`).
- **IPv6:** Synced identically.

---

## 7. Vault Integration for Secrets Management

### 7.1 Auth Decision Tree

```
Where does the CLI run?
├─ Kubernetes Pod           → K8s Auth  (no credentials to store)
├─ VM / Bare-metal / CI     → AppRole   (response-wrapped SecretID)
└─ Dev workstation          → Token     (VAULT_TOKEN env var, short TTL)
```

**AppRole flow (recommended for production outside K8s):**

```
1. Create AppRole
   vault auth enable approle
   vault write auth/approle/role/nvs-vcenter \
       secret_id_ttl=10m \
       token_ttl=60m \
       token_max_ttl=24h \
       policies=nvs-read

2. Fetch credentials
   RoleID:   vault read auth/approle/role/nvs-vcenter/role-id
   SecretID: vault write -wrap-ttl=5m -f auth/approle/role/nvs-vcenter/secret-id

3. CLI uses RoleID + wrapped SecretID at runtime
   → hvac Client → approle login → short-lived token → fetch secrets
```

### 7.2 Configuration Schema

```yaml
vault:
  enabled: true
  addr: https://vault.example.com:8200
  ssl_verify: true
  namespace: ""
  auth:
    method: approle                    # token | approle | kubernetes
    role_id: "${VAULT_ROLE_ID}"        # or env var
    secret_id: "${VAULT_SECRET_ID}"    # or env var
  secrets:
    vcenter:
      path: kv-v2/vcenter/creds
      mount_point: kv-v2
      keys:
        username: VCENTER_USER
        password: VCENTER_PASS
    netbox:
      path: kv-v2/netbox/api-token
      mount_point: kv-v2
      keys:
        token: NVS_NETBOX_TOKEN
```

### 7.3 Secret Resolution Order

Credentials are resolved using this precedence (higher = wins):

| Priority | Source | Example |
|---|---|---|
| 1 (highest) | CLI flag | `--vcenter-password '…'` |
| 2 | Env var | `VCENTER_PASSWORD` |
| 3 | Vault (hvac) | `vault.secrets.vcenter → VCENTER_USER, VCENTER_PASS` |
| 4 | YAML config | `vcenter.password` in config file |
| 5 (lowest) | Default | `None` (fails with actionable error) |

If Vault is enabled, the tool authenticates, reads each secret path, maps
keys to env vars, then merges into `os.environ` before initialising PyVmomi
or pynetbox.

### 7.4 VaultClient Wrapper

```python
class VaultClient:
    def __init__(self, addr, auth_method, auth_params, verify=True, namespace=""):
        self._client = hvac.Client(url=addr, verify=verify, namespace=namespace)
        self._auth_method = auth_method
        self._auth_params = auth_params
        self._lease_expiry = 0.0
        self._authenticate()

    def _authenticate(self):
        if self._auth_method == "token":
            self._client.token = self._auth_params["token"]
        elif self._auth_method == "approle":
            self._client.auth.approle.login(
                role_id=self._auth_params["role_id"],
                secret_id=self._auth_params["secret_id"],
            )
        elif self._auth_method == "kubernetes":
            self._client.auth.kubernetes.login(
                role=self._auth_params["role"],
                jwt=self._read_k8s_token(),
            )
        lease = self._client.token_lookup()["data"]
        self._lease_expiry = time.time() + lease.get("ttl", 3600)

    def _ensure_auth(self):
        if time.time() >= self._lease_expiry * 0.9:
            self._authenticate()

    def read_kv_v2(self, path, mount_point="secret"):
        self._ensure_auth()
        try:
            resp = self._client.secrets.kv.v2.read_secret_version(
                path=path, mount_point=mount_point
            )
            return resp["data"]["data"]
        except hvac.exceptions.Forbidden:
            self._authenticate()
            resp = self._client.secrets.kv.v2.read_secret_version(
                path=path, mount_point=mount_point
            )
            return resp["data"]["data"]

    def _read_k8s_token(self):
        with open("/var/run/secrets/kubernetes.io/serviceaccount/token") as f:
            return f.read()
```

### 7.5 Init Sequence With Vault

```
netbox-vsphere-sync sync [--vault-enabled]

1. Read config.yaml
2. If vault.enabled:
   ├─ Instantiate VaultClient
   ├─ Read vault.secrets.vcenter  →  os.environ[VCENTER_USER, VCENTER_PASS]
   └─ Read vault.secrets.netbox   →  os.environ[NVS_NETBOX_TOKEN]
3. Instantiate VSphereClient
4. Instantiate NetBoxClient
5. Run sync pipeline
6. Exit (lease auto-revokes on token expiry)
```

### 7.6 Security Properties

| Concern | Mitigation |
|---|---|
| Credential at rest (disk) | All credentials from env or Vault at runtime. YAML references paths, not secrets. |
| Credential in logs | Env vars masked in debug output (`VCENTER_PASS=****`). |
| Token leak | Vault client token is short-lived (default 60 min). SecretID is response-wrapped. |
| Network eavesdrop | TLS verification enabled by default for all endpoints. |
| Lease accumulation | Short-lived process — token TTL exceeds run duration. |

### 7.7 Without Vault (Fallback)

When `vault.enabled: false`, the tool reads credentials directly from env vars
or YAML config with `${VAR}` interpolation:

```yaml
vcenter:
  host: vc01.example.com
  username: "${VCENTER_USER}"
  password: "${VCENTER_PASS}"
netbox:
  url: https://netbox.example.com
  token: "${NVS_NETBOX_TOKEN}"
```

This supports dev environments, Vault Agent sidecars, and CI secrets injection.

---

## 8. Technical Vision

### 8.1 Stack

| Component | Technology | Rationale |
|---|---|---|
| Language | Python 3.11+ | Ecosystem maturity, pyvmomi, pynetbox |
| vSphere SDK | PyVmomi | Official VMware SDK, comprehensive |
| NetBox Client | pynetbox >=7.0 | Official client, v2 token support |
| Vault Client | hvac >=2.0 | Official HashiCorp client |
| CLI Framework | Click | Industry standard, composable |
| Config Validation | Pydantic v2 | Type-safe, env var support, schema gen |
| Logging | Rich + structlog | Human terminal + structured JSON |
| Testing | pytest, vcrpy | Record/replay HTTP for deterministic tests |
| Linting | Ruff | Fast, drops-in for flake8 + isort + pyupgrade |
| Type Checking | Pyright (strict) | Catches interface contract violations |
| Packaging | pyproject.toml | PEP 621, single-source metadata |
| Automation | Makefile | Common commands without extra tooling |
| Pre-commit | pre-commit | Gate lint + typecheck before commits |

### 8.2 Project Structure

```
netbox-vsphere-sync/
├── pyproject.toml              # Dependencies, metadata, entry points (PEP 621)
├── Makefile                    # Common command recipes
├── README.md                   # Quickstart and usage
├── LICENSE                     # Apache 2.0
├── .gitignore
├── ruff.toml                   # Linter + formatter configuration
├── pyrightconfig.json          # Strict type-checker configuration
├── .pre-commit-config.yaml     # Pre-commit hooks
├── .github/workflows/          # CI pipeline (GitHub Actions)
├── docs/                       # System documentation
│   ├── vision.md               # This file — architecture vision
│   ├── domains.md              # DDD domain model and bounded contexts
│   ├── architecture.md         # System, component, API, deployment design
│   ├── SRS.md                  # Software requirements specification
│   └── standards.md            # Coding, git, testing, security standards
│
├── src/
│   └── netbox_vsphere_sync/    # Main package
│       ├── domain/             # Core domain: entities, VOs, events, ports
│       │   ├── model/          # Entities, value objects
│       │   │   ├── vsphere/    # vSphere-side domain objects
│       │   │   └── config/     # Pydantic config models
│       │   ├── events.py
│       │   ├── ports.py        # Repository protocols (typing.Protocol)
│       │   ├── exceptions.py   # Domain exception hierarchy
│       │   └── constants.py
│       ├── application/        # Use cases: sync engine, diff engine
│       │   ├── sync_engine.py
│       │   ├── diff_engine.py
│       │   ├── dependency_resolver.py
│       │   ├── bootstrapper.py
│       │   └── event_log.py
│       ├── infrastructure/     # Adapters: NetBox ACL, vSphere ACL, Vault, config
│       │   ├── netbox/
│       │   │   ├── acl.py
│       │   │   ├── client.py
│       │   │   └── repositories/
│       │   ├── vsphere/
│       │   │   ├── acl.py
│       │   │   └── collector.py
│       │   ├── vault/
│       │   │   ├── acl.py
│       │   │   └── client.py
│       │   └── config/
│       │       ├── loader.py
│       │       └── secret_resolver.py
│       ├── cli/                # Click commands
│       │   ├── __main__.py
│       │   ├── app.py
│       │   └── commands/
│       └── report/             # Observability: reports, logging
│           ├── generator.py
│           └── console.py
│
└── tests/                      # Mirrors src/ structure
    ├── conftest.py
    ├── domain/
    │   └── model/
    │       ├── test_site.py
    │       ├── test_cluster.py
    │       ├── test_host.py
    │       ├── test_network.py
    │       └── test_inventory.py
    ├── application/
    │   ├── test_sync_engine.py
    │   ├── test_diff_engine.py
    │   └── test_dependency_resolver.py
    ├── infrastructure/
    │   ├── netbox/
    │   │   └── test_repositories.py
    │   └── vsphere/
    │       └── test_collector.py
    └── cli/
        └── test_commands.py
```

### 8.3 CLI Interface

```
Usage: nvs-sync [OPTIONS] COMMAND [ARGS]...

Options:
  -c, --config FILE            Path to YAML config file  [env: NVS_CONFIG]
  --dry-run                    Preview changes without writing
  --prune                      Deactivate orphaned objects
  --vcenter-username TEXT      vCenter username  [env: NVS_VCENTER_USERNAME]
  --vcenter-password TEXT      vCenter password  [env: NVS_VCENTER_PASSWORD]
  --netbox-token TEXT          NetBox API token  [env: NVS_NETBOX_TOKEN]
  --vcenter-insecure           Disable vCenter TLS verification
  --netbox-insecure            Disable NetBox TLS verification
  --help                       Show this message and exit

Commands:
  sync       Run a full synchronization
```

> **Note:** The `bootstrap`, `check`, and `config` commands are planned but not yet implemented.

### 8.4 Sync Report Output

```
$ nvs-sync sync

NetBox vSphere Sync ── run 2026-06-14T10:30:00Z
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

 ✓ vCenter connected: vc01.example.com (3 datacenters)
 ✓ NetBox connected: netbox.example.com (API v4.5)

Sync Results:
  Entity           Created  Updated  Deactivated  Errors
 ──────────────────────────────────────────────────────
  Site                    3        0             0       0
  Cluster                12        2             0       0
  Device                145       23             1       0
  VLAN                   48        5             0       0
  Interface             312       18             0       0
  IPAddress             156        3             0       0
  InventoryItem        2900       45             0       0
 ──────────────────────────────────────────────────────
  Total                3576       96             1       0

 ⏱  Duration: 42.3s
```

---

## 9. Design Principles

### 9.1 Idempotency

Every sync run produces the same result when the source data has not changed.
Achieved through:

- **Natural key matching** — each object is identified by a stable business
  key (§4.3), not by database ID.
- **Upsert semantics** — lookup by natural key first; if found, PATCH; if not,
  POST.
- **No implicit deletions** — by default the tool never deletes. Orphaned
  objects are reported separately. Users opt into deletion via `--prune`.

### 9.2 Fail-Safe Defaults

| Default | Rationale |
|---|---|
| `--dry-run` is always available | Preview before applying. |
| `--prune` is false | No automatic deletion. Users must opt in. |
| SSL verification enabled | Security by default; overridable with flags. |
| Timeout after 60 s per API call | Prevents hung runs from blocking cron. |
| Batch size 100 | Prevents overwhelming NetBox with writes. |

### 9.3 Observability

- **Structured JSON logging** to stdout for log aggregators.
- **Rich console output** (tables, spinners) for interactive use.
- **Exit codes:** 0 = success, 1 = partial errors, 2 = connection/config error.
- **Metrics** exposed via log counters for Prometheus mtail or similar.

### 9.4 Extensibility

- Each sync entity lives in its own module with a standard interface:
  `collect()`, `diff()`, `apply()`.
- The engine discovers modules via a registry (import + decorator).
- Adding a new entity type requires: new module → register → done.
- Custom field mapping and tag injection are declarative in config, not code.

---

## 10. Implementation Roadmap

### Phase 1 — Project Design ✅ COMPLETE

- Design documents completed: vision, domains, architecture, SRS, standards.
- Project standards defined: coding, git, testing, security.
- Directory structure established per DDD layered architecture.

**Related docs:** `docs/vision.md`, `docs/domains.md`, `docs/architecture.md`, `docs/SRS.md`, `docs/standards.md`

### Phase 2 — Project Scaffolding ⬜ PLANNED

- Initialize `pyproject.toml` with runtime + dev dependencies.
- Create `Makefile` with `install`, `lint`, `typecheck`, `test`, `clean`.
- Add `.gitignore`, `ruff.toml`, `pyrightconfig.json`, `.pre-commit-config.yaml`.
- Bootstrap empty package structure under `src/netbox_vsphere_sync/`.

**Deliverable:** `pip install -e .` succeeds, `ruff .` passes, `pyright` passes.

**Related docs:** `docs/standards.md` §8, §10

### Phase 3 — Core Infrastructure ⬜ PLANNED

- `infrastructure/config/loader.py` — Pydantic model, YAML file support, env var overrides.
- `infrastructure/vault/client.py` — VaultClient wrapper with AppRole / K8s / Token auth.
- `infrastructure/netbox/client.py` — authenticated pynetbox wrapper with retry.
- `infrastructure/vsphere/acl.py` — PyVmomi SmartConnect wrapper + ACL.
- `cli/app.py` + commands — Click group with `sync`, `check`, `bootstrap`, `config`.
- `application/sync_engine.py` — orchestrator that runs modules in dependency order.
- `application/diff_engine.py` — generic create/update/delete diff computation.

**Deliverable:** `netbox-vsphere-sync check` displays connectivity for all
three backends.

**Related docs:** `docs/architecture.md` §2, `docs/domains.md` §5

### Phase 4 — Entity Sync Modules ⬜ PLANNED

One module per day in dependency order:

1. `infrastructure/vsphere/collector.py` + sync — Site (vSphere Datacenter → NetBox Site).
2. `infrastructure/netbox/repositories/cluster.py` + sync — Cluster.
3. `infrastructure/netbox/repositories/device.py` + sync — Device (ESXi Host).
4. Sync — VLAN (Port Group).
5. Sync — Interface + IPAddress (VMkernel).
6. Sync — InventoryItem (hardware).
7. Sync — InventoryItem (datastore storage).

Each module includes unit tests with mocked vSphere and NetBox responses.

**Deliverable:** `netbox-vsphere-sync sync --dry-run` produces a complete
change report against a live vCenter.

**Related docs:** `docs/vision.md` §4, `docs/architecture.md` §3, `docs/domains.md` §3–4

### Phase 5 — Testing & Quality ⬜ PLANNED

- Unit tests for every module (>=80 % line coverage).
- Integration test fixtures using vcrpy for recorded NetBox interactions.
- Property-based tests for diff logic.
- CI workflow (GitHub Actions) running ruff, pyright, pytest.

**Deliverable:** `make test` passes. `make lint typecheck` passes.

**Related docs:** `docs/standards.md` §6, `docs/architecture.md` §6

### Phase 6 — Packaging & Documentation ⬜ PLANNED

- PyPI-ready `pyproject.toml` (description, classifiers, project URLs).
- Full `README.md` with install, config, usage, and cron example.
- Configuration file reference.
- Example systemd unit and timer for cron scheduling.
- LICENSE (Apache 2.0).

**Deliverable:** `pip install netbox-vsphere-sync` works. README covers every
flag.

---

## 11. Operational Considerations

### 11.1 vCenter API Impact

- The sync uses read-only vSphere APIs (PropertyCollector,
  RetrievePropertiesEx).
- No write operations are ever performed against vCenter.
- A full sync of 500 hosts issues approximately 3–5 API calls per datacenter,
  not per host.

### 11.2 NetBox API Impact

- Pagination honoured (`?limit=100`).
- Brief mode (`?brief=True`) for all list operations.
- `config_context` excluded from device queries.
- Bulk create/update using list endpoints with PATCH JSON arrays where
  possible.

### 11.3 Failure Modes

| Failure | Behaviour |
|---|---|
| vCenter unreachable | Sync aborts early. Exit code 2. No changes applied. |
| NetBox unreachable | Sync aborts early. Exit code 2. No changes applied. |
| Partial NetBox errors | Individual failures logged; sync continues. Exit code 1. |
| Vault unreachable | Falls back to env vars / config if available. Else abort. |
| Duplicate natural key collision | Caught by pynetbox; logged ERROR; sync continues. |

### 11.4 Security

- API tokens never logged or written to disk.
- Credentials supplied via env vars, Vault, or config — never hardcoded.
- vCenter password and NetBox token masked in verbose output.
- HTTPS verification enabled by default for all endpoints.

### 11.5 Recommended Cron Setup

```cron
# Every 15 minutes, Mon–Fri
*/15 * * * 1-5 /usr/local/bin/netbox-vsphere-sync sync \
    --config /etc/netbox-vsphere-sync/config.yaml \
    >> /var/log/netbox-vsphere-sync.log 2>&1
```

For higher reliability, wrap in a systemd timer with `OnFailure` notification.

---

## 12. Out of Scope (v1)

The following are explicitly **not** part of the initial vision.

- VM synchronization (VirtualMachine → NetBox VM).
- Bidirectional sync (NetBox → vSphere). Risk outweighs benefit.
- NetBox webhook consumer / event-driven sync.
- Web UI or dashboard. CLI-only; results feed into existing observability.
- Multi-vCenter aggregation in a single run.
- NetBox Branching plugin integration.
- Diode ingestion path (for when Diode supports required entity types).
- Automated device-type library management.

---

> **Vision statement.** *By treating vSphere as the authoritative source for
> compute, storage, and network topology and automating reconciliation into
> NetBox, this project eliminates manual CMDB data entry, reduces drift, and
> gives infrastructure teams a reliable, queryable picture of their virtual
> estate — with zero risk to the production hypervisor.*

---

## 13. Document Map

| Document | Path | Purpose |
|---|---|---|
| **Vision** | `docs/vision.md` | This file — architecture vision, data model, strategic decisions |
| **Domain Model** | `docs/domains.md` | DDD bounded contexts, aggregates, entities, value objects, events, ports |
| **Architecture** | `docs/architecture.md` | System context, components, security, deployment design |
| **SRS** | `docs/SRS.md` | Functional and non-functional requirements, acceptance criteria |
| **Standards** | `docs/standards.md` | Coding, git, testing, security standards |
| **Agent Workflow** | `AGENTS.md` | Agent workflow, tech stack, build commands, commit policy |
