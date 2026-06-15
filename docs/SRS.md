# Software Requirements Specification (SRS)

## NetBox Integration for vSphere

**Version:** 1.0
**Date:** 2026-06-15
**Status:** Draft

---

## Table of Contents

1. Introduction
2. Overall Description
3. Functional Requirements
4. Non-Functional Requirements
5. External Interface Requirements
6. Data Model Requirements
7. Sync Engine Requirements
8. Security Requirements
9. Constraints and Assumptions
10. Acceptance Criteria
11. Open Items
12. Appendix: Configuration Schema

---

## 1. Introduction

### 1.1 Purpose

This document specifies the software requirements for `netbox-vsphere-sync`,
a Python CLI tool that performs one-way, cron-driven synchronisation from
VMware vSphere into NetBox (4.5+).

### 1.2 Scope

The tool reads the full vSphere inventory (datacentres, clusters, ESXi hosts,
port groups, VMkernel interfaces, hardware components, datastores) and
reconciles it against a NetBox instance using the REST API. vSphere is the
authoritative source. NetBox is the output.

### 1.3 Definitions

| Term | Definition |
|---|---|
| **vSphere** | VMware vSphere (ESXi + vCenter) virtualisation platform |
| **NetBox** | Open-source IPAM/DCIM tool (netboxlabs.com) |
| **Sync** | One-way reconciliation from vSphere to NetBox |
| **Natural Key** | Business key used to match domain objects to NetBox records |
| **ACL** | Anti-Corruption Layer — adapter between domain and external API |
| **Bootstrap** | First-run creation of prerequisite NetBox metadata |

### 1.4 References

| Document | Location |
|---|---|
| Vision Document | `docs/vision.md` |
| Domain Model | `docs/domains.md` |
| NetBox Best Practices | `.agents/skills/netbox-integration-best-practices/` |

---

## 2. Overall Description

### 2.1 Product Perspective

```
┌──────────────┐     ┌──────────────────────┐     ┌──────────────┐
│   vCenter    │────▶│  netbox-vsphere-sync  │────▶│   NetBox     │
│  (PyVmomi)   │     │  (sync engine)        │     │  (pynetbox)  │
│  READ ONLY   │     │  CLI + cron           │     │  READ/WRITE  │
└──────────────┘     └──────────────────────┘     └──────────────┘
```

- **vSphere**: Read-only. No write operations against vCenter.
- **NetBox**: Read + Write. Creates and updates objects via REST API.
- **Tool**: Stateless CLI. Each run is independent and idempotent.

### 2.2 User Classes

| User | Description |
|---|---|
| **Infrastructure Engineer** | Installs, configures, and operates the tool |
| **Platform Operator** | Runs the tool via cron, monitors sync results |
| **NetBox Administrator** | Manages NetBox instance, reviews synced data |

### 2.3 Product Functions (High-Level)

1. Connect to vCenter and read inventory
2. Connect to NetBox and read existing state
3. Compute diff (creates, updates, unchanged)
4. Apply changes in dependency order
5. Report results (console + structured logs)
6. Optionally delete orphaned objects (--prune)

### 2.4 Design Constraints

- **One-way sync only**: vSphere → NetBox. No reverse direction.
- **Single vCenter per run**: One config file = one vCenter connection.
- **Cron-driven**: Periodic polling, not event-driven.
- **No concurrent runs**: Lock file prevents overlapping executions.
- **Idempotent**: Re-running produces the same result when data hasn't changed.
- **No deletions by default**: Orphaned objects are reported, not removed.

---

## 3. Functional Requirements

### 3.1 Entity Synchronisation

#### FR-001: Site Synchronisation

| Attribute | Value |
|---|---|
| **ID** | FR-001 |
| **Priority** | CRITICAL |
| **Description** | Synchronise vSphere Datacenters to NetBox Sites |

**Requirements:**
- Create NetBox Site for each vSphere Datacenter
- Natural key: `name` (unique)
- Fields: name, slug (auto-derived), description (vSphere path), custom_field[vcenter_mor]
- Skip if Site exists but has no vcenter_mor custom field (unmanaged site)
- Auto-derive slug from name (lowercase, hyphens, special chars removed)

**vSphere Source:**
```
Datacenter.name → Site.name
Datacenter.path → Site.description
Datacenter.mor  → Site.custom_fields.vcenter_mor
```

#### FR-002: Cluster Synchronisation

| Attribute | Value |
|---|---|
| **ID** | FR-002 |
| **Priority** | CRITICAL |
| **Description** | Synchronise vSphere Clusters to NetBox Clusters |

**Requirements:**
- Create NetBox Cluster for each vSphere ClusterComputeResource
- Natural key: `name` + `site_name` (clusters are namespaced by datacenter)
- Fields: name, type ("vSphere Cluster"), site, custom_fields (mor, ha, drs, cpu, memory)
- ClusterType "vSphere Cluster" must be bootstrapped if missing
- Optional: ClusterGroup (configurable in YAML)

**vSphere Source:**
```
Cluster.name           → Cluster.name
Cluster.datacenter     → Cluster.site (resolved)
Cluster.mor            → Cluster.custom_fields.vcenter_mor
Cluster.haEnabled      → Cluster.custom_fields.vcenter_ha_enabled
Cluster.drsEnabled     → Cluster.custom_fields.vcenter_drs_enabled
Cluster.drsLevel       → Cluster.custom_fields.vcenter_drs_level
Cluster.totalCpu       → Cluster.custom_fields.vcenter_cluster_cpu_mhz
Cluster.totalMemory    → Cluster.custom_fields.vcenter_cluster_memory_mb
```

#### FR-003: Device (ESXi Host) Synchronisation

| Attribute | Value |
|---|---|
| **ID** | FR-003 |
| **Priority** | CRITICAL |
| **Description** | Synchronise vSphere HostSystems to NetBox Devices |

**Requirements:**
- Create NetBox Device for each ESXi host
- Natural key: `name` (FQDN, unique per NetBox instance)
- Device Role "ESXi Server" must be bootstrapped if missing
- Manufacturer + DeviceType auto-created from host hardware info
- Status mapping: connected→Active, disconnected→Offline, notResponding→Failed, maintenance→Offline

**vSphere Source:**
```
HostSystem.name                → Device.name (FQDN)
HostSystem.hardware.vendor     → DeviceType.manufacturer
HostSystem.hardware.biosInfo   → DeviceType.model
HostSystem.cluster             → Device.cluster
HostSystem.datacenter          → Device.site
HostSystem.version             → Device.custom_fields.vcenter_esxi_version
HostSystem.build               → Device.custom_fields.vcenter_esxi_build
HostSystem.connectionState     → Device.status
HostSystem.powerState          → Device.custom_fields.vcenter_power_state
HostSystem.numCpuCores         → Device.custom_fields.vcenter_cpu_cores
HostSystem.numCpuThreads       → Device.custom_fields.vcenter_cpu_threads
HostSystem.cpuModel            → Device.custom_fields.vcenter_cpu_model
HostSystem.memorySize          → Device.custom_fields.vcenter_memory_bytes
HostSystem.mor                 → Device.custom_fields.vcenter_mor
```

#### FR-004: VLAN (Port Group) Synchronisation

| Attribute | Value |
|---|---|
| **ID** | FR-004 |
| **Priority** | HIGH |
| **Description** | Synchronise vSphere Port Groups to NetBox VLANs |

**Requirements:**
- Create NetBox VLAN for each vSphere Port Group
- Natural key: `vid` + `site_name`
- VLAN ID allocation strategy (configurable):
  - `from_portgroup`: Use vlanTag directly when available
  - `reserved_range`: Allocate from configurable range (default 4000-4094) for untagged
  - `auto_allocate`: Skip if no tag and no reserved range
- Skip link-local IPs (169.254.x.x, fe80::)

**vSphere Source:**
```
PortGroup.name        → VLAN.name
PortGroup.datacenter  → VLAN.site
PortGroup.vlanTag     → VLAN.vid
PortGroup.mor         → VLAN.custom_fields.vcenter_mor
```

#### FR-005: Interface (VMkernel) Synchronisation

| Attribute | Value |
|---|---|
| **ID** | FR-005 |
| **Priority** | HIGH |
| **Description** | Synchronise vSphere VMkernel NICs to NetBox Interfaces |

**Requirements:**
- Create NetBox Interface for each VMkernel NIC
- Natural key: `device_name` + `name`
- Type: "virtual"
- Fields: name, type, enabled, mtu, mac_address, description

**vSphere Source:**
```
VMkernelNic.deviceName    → Interface.device_name
VMkernelNic.key/name      → Interface.name (e.g., "vmk0")
VMkernelNic.mac           → Interface.mac_address
VMkernelNic.mtu           → Interface.mtu
VMkernelNic.portgroup     → Interface.description
VMkernelNic.enabled       → Interface.enabled
```

#### FR-006: IPAddress Synchronisation

| Attribute | Value |
|---|---|
| **ID** | FR-006 |
| **Priority** | HIGH |
| **Description** | Synchronise vSphere VMkernel IPs to NetBox IPAddresses |

**Requirements:**
- Create NetBox IPAddress for each VMkernel IP
- Natural key: `address` (CIDR notation)
- Combine IP + subnet mask into CIDR
- Role assignment via decision matrix (service tag → prefix rules → default)
- Skip link-local addresses (169.254.x.x, fe80::)
- Multiple IPs per interface: each synced separately

**vSphere Source:**
```
VMkernelNic.ip.address      → IPAddress.address (CIDR)
VMkernelNic.serviceTags     → IPAddress.role (decision matrix)
VMkernelNic.portgroup       → IPAddress.description
HostSystem.name             → IPAddress.dns_name
```

#### FR-007: Hardware Inventory Synchronisation

| Attribute | Value |
|---|---|
| **ID** | FR-007 |
| **Priority** | MEDIUM |
| **Description** | Synchronise ESXi host hardware to NetBox InventoryItems |

**Requirements:**
- Create NetBox InventoryItem for each hardware component
- Natural key: `device_name` + `name` + `role`
- Supported component types: CPU, Memory, Disk, NIC, Controller, HBA, BIOS
- De-duplicate per run: components keyed by (name, role, manufacturer)
- Never delete: component removal from vSphere leaves orphaned items

**vSphere Source:**
```
hardware.cpuPkg[]                  → InventoryItem (role=CPU)
hardware.memoryModules[]           → InventoryItem (role=Memory)
storageSystem.scsiTopology         → InventoryItem (role=Storage/Disk)
networkSystem.pnic[]               → InventoryItem (role=NIC)
storageSystem.hostBusAdapter[]     → InventoryItem (role=Controller)
networkSystem.hba[]                → InventoryItem (role=HBA)
hardware.biosInfo                  → InventoryItem (role=BIOS)
```

#### FR-008: Datastore (Storage) Synchronisation

| Attribute | Value |
|---|---|
| **ID** | FR-008 |
| **Priority** | MEDIUM |
| **Description** | Synchronise vSphere Datastores to NetBox InventoryItems (per-host) |

**Requirements:**
- Create one InventoryItem per datastore per host (per-host strategy)
- Natural key: `device_name` + `name` + `role` (role = "Storage")
- Description: human-readable format with capacity, usage, type
- Custom fields: storage_free_bytes, storage_backend_type, storage_shared

**vSphere Source:**
```
Datastore.name              → InventoryItem.name
Datastore.capacity          → InventoryItem.description (formatted)
Datastore.freeSpace         → InventoryItem.custom_fields.storage_free_bytes
Datastore.type              → InventoryItem.custom_fields.storage_backend_type
Datastore.multipleHostAccess → InventoryItem.custom_fields.storage_shared
Datastore.mountedHosts      → (used for per-host iteration)
Datastore.mor               → InventoryItem.custom_fields.vcenter_mor
```

### 3.2 Bootstrap

#### FR-009: NetBox Metadata Bootstrap

| Attribute | Value |
|---|---|
| **ID** | FR-009 |
| **Priority** | CRITICAL |
| **Description** | Create prerequisite NetBox metadata on first run |

**Requirements:**
- Create Manufacturer "VMware Inc" if missing
- Create Device Role "ESXi Server" if missing
- Create Cluster Type "vSphere Cluster" if missing
- Create InventoryItem Roles: "Storage", "Hardware" if missing
- Create Custom Fields (see FR-010)
- Bootstrap can be disabled via config (`bootstrap.enabled: false`)
- Bootstrap runs before entity sync

#### FR-010: Custom Field Creation

| Attribute | Value |
|---|---|
| **ID** | FR-010 |
| **Priority** | HIGH |
| **Description** | Create NetBox custom fields if they do not exist |

**Required Custom Fields:**

| Model | Field Name | Type | Purpose |
|---|---|---|---|
| Site | `vcenter_mor` | Text | vSphere managed object reference |
| Cluster | `vcenter_mor` | Text | vSphere managed object reference |
| Cluster | `vcenter_ha_enabled` | Boolean | HA feature flag |
| Cluster | `vcenter_drs_enabled` | Boolean | DRS feature flag |
| Cluster | `vcenter_drs_level` | Text | DRS automation level |
| Cluster | `vcenter_cluster_cpu_mhz` | Integer | Total CPU capacity (MHz) |
| Cluster | `vcenter_cluster_memory_mb` | Integer | Total memory capacity (MB) |
| Device | `vcenter_mor` | Text | vSphere managed object reference |
| Device | `vcenter_esxi_version` | Text | ESXi version string |
| Device | `vcenter_esxi_build` | Text | ESXi build number |
| Device | `vcenter_power_state` | Text | Power state |
| Device | `vcenter_cpu_cores` | Integer | Physical CPU cores |
| Device | `vcenter_cpu_threads` | Integer | Logical CPU threads |
| Device | `vcenter_cpu_model` | Text | CPU model name |
| Device | `vcenter_memory_bytes` | Integer | Total memory (bytes) |
| VLAN | `vcenter_mor` | Text | vSphere managed object reference |
| InventoryItem | `storage_free_bytes` | Integer | Free space (bytes) |
| InventoryItem | `storage_backend_type` | Text | VMFS/NFS/vSAN/VVol |
| InventoryItem | `storage_shared` | Boolean | Multiple host access |

### 3.3 Sync Operations

#### FR-011: Full Sync

| Attribute | Value |
|---|---|
| **ID** | FR-011 |
| **Priority** | CRITICAL |
| **Description** | Execute complete synchronisation cycle |

**Requirements:**
- Pipeline: Authenticate → Bootstrap → Collect → Fetch → Diff → Apply → Report
- Process all 8 entity types in dependency order
- Dependency order: Site → Cluster → Device → VLAN → Interface → IPAddress → InventoryItem
- Report created/updated/unchanged/errors per entity type
- Exit code 0 = success (no errors), 1 = partial errors, 2 = connection/config error

#### FR-012: Dry-Run Mode

| Attribute | Value |
|---|---|
| **ID** | FR-012 |
| **Priority** | HIGH |
| **Description** | Preview sync changes without applying |

**Requirements:**
- Triggered by `--dry-run` flag
- Collects from vSphere, fetches from NetBox, computes diff
- Does NOT write to NetBox
- Reports what WOULD be created/updated
- Same exit codes as full sync

#### FR-013: Prune Mode

| Attribute | Value |
|---|---|
| **ID** | FR-013 |
| **Priority** | MEDIUM |
| **Description** | Remove orphaned objects from NetBox |

**Requirements:**
- Triggered by `--prune` flag (opt-in, never default)
- Identifies NetBox objects managed by the tool (have vcenter_mor) that no longer exist in vSphere
- Deactivates (status → decommissioning) rather than hard-deletes
- Reports pruned objects in sync summary

#### FR-014: Check Command

| Attribute | Value |
|---|---|
| **ID** | FR-014 |
| **Priority** | HIGH |
| **Description** | Validate connectivity to vCenter and NetBox |

**Requirements:**
- `netbox-vsphere-sync check` command
- Tests vCenter connection (SmartConnect)
- Tests NetBox connection (API status)
- Tests Vault connection (if enabled)
- Reports OK/FAIL for each
- Exit code 0 = all OK, 2 = any failure

#### FR-015: Bootstrap Command

| Attribute | Value |
|---|---|
| **ID** | FR-015 |
| **Priority** | MEDIUM |
| **Description** | Create prerequisite NetBox metadata only |

**Requirements:**
- `netbox-vsphere-sync bootstrap` command
- Creates Manufacturers, Roles, ClusterTypes, Custom Fields
- Does NOT sync entities
- Idempotent: safe to run multiple times

### 3.4 Configuration

#### FR-016: Configuration Loading

| Attribute | Value |
|---|---|
| **ID** | FR-016 |
| **Priority** | CRITICAL |
| **Description** | Load configuration from multiple sources |

**Requirements:**
- Configuration sources (in precedence order, highest first):
  1. CLI flags (--vcenter-host, --netbox-url, etc.)
  2. Environment variables (VCENTER_HOST, NVS_NETBOX_URL, etc.)
  3. Vault secrets (if vault.enabled)
  4. YAML config file (specified via --config or NVS_CONFIG)
  5. Defaults
- No default config file path (explicit only via --config or NVS_CONFIG)
- Validate config on load (Pydantic)
- Fail fast with clear error messages on invalid config

#### FR-017: Vault Integration

| Attribute | Value |
|---|---|
| **ID** | FR-017 |
| **Priority** | HIGH |
| **Description** | Optional HashiCorp Vault integration for secrets |

**Requirements:**
- Support three auth methods: token, approle, kubernetes
- Read vCenter and NetBox credentials from Vault KV v2
- Auto-renew Vault token at 90% of TTL
- Fall back to env vars if Vault is unreachable
- Mask credentials in all log output

### 3.5 Reporting

#### FR-018: Sync Report

| Attribute | Value |
|---|---|
| **ID** | FR-018 |
| **Priority** | HIGH |
| **Description** | Generate human-readable sync report |

**Requirements:**
- Rich console output with tables and spinners
- Structured JSON logging to stdout
- Report includes:
  - vCenter connection status
  - NetBox connection status
  - Per-entity-type counts (created, updated, unchanged, errors)
  - Total duration
  - Exit code

#### FR-019: Lock File

| Attribute | Value |
|---|---|
| **ID** | FR-019 |
| **Priority** | MEDIUM |
| **Description** | Prevent concurrent sync runs |

**Requirements:**
- Acquire lock file at start (e.g., `/tmp/nvs-sync.lock`)
- If lock exists and process is alive: exit with warning (code 0)
- If lock exists but process is stale: acquire and proceed
- Release lock on exit (including errors)
- Lock contains PID for staleness detection

---

## 4. Non-Functional Requirements

### 4.1 Performance

| ID | Requirement | Target |
|---|---|---|
| NFR-001 | Sync 500 ESXi hosts | < 5 minutes |
| NFR-002 | NetBox API pagination | Limit = 100 per request |
| NFR-003 | NetBox brief mode | Use ?brief=True for lists |
| NFR-004 | Config_context exclusion | Exclude from device queries |
| NFR-005 | Batch size | Configurable, default 100 |

### 4.2 Reliability

| ID | Requirement | Target |
|---|---|---|
| NFR-006 | Idempotent sync | Same result on re-run |
| NFR-007 | Dependency order | Topological sort enforced |
| NFR-008 | No implicit deletions | Prune mode opt-in only |
| NFR-009 | Partial failure | Continue on individual errors |
| NFR-010 | API timeout | 60 seconds per call |

### 4.3 Usability

| ID | Requirement | Target |
|---|---|---|
| NFR-011 | CLI help | --help for every command |
| NFR-012 | Error messages | Actionable, include context |
| NFR-013 | Progress indication | Spinner for long operations |
| NFR-014 | Exit codes | 0=success, 1=partial, 2=error |

### 4.4 Maintainability

| ID | Requirement | Target |
|---|---|---|
| NFR-015 | Python version | 3.11+ (best effort) |
| NFR-016 | Type safety | Pyright strict |
| NFR-017 | Code style | Ruff (lint + format) |
| NFR-018 | Test coverage | >= 80% line coverage |
| NFR-019 | Pre-commit hooks | ruff + pyright |

### 4.5 Security

| ID | Requirement | Target |
|---|---|---|
| NFR-020 | TLS verification | Enabled by default |
| NFR-021 | Credential masking | Never log passwords/tokens |
| NFR-022 | No credential storage | Env vars or Vault only |
| NFR-023 | Vault token TTL | Short-lived (60 min default) |

---

## 5. External Interface Requirements

### 5.1 vSphere API (PyVmomi)

| Attribute | Value |
|---|---|
| Protocol | HTTPS (SmartConnect) |
| Auth | Username + password |
| Operations | READ ONLY |
| API Version | vSphere 7.0+ (best effort), 8.0+ (guaranteed) |
| Pagination | PropertyCollector with RetrievePropertiesEx |

### 5.2 NetBox REST API (pynetbox)

| Attribute | Value |
|---|---|
| Protocol | HTTPS |
| Auth | v2 Token (Bearer nbt_*.*) |
| Operations | READ + WRITE |
| Version | 4.5+ (required for v2 tokens) |
| Pagination | ?limit=100 (max 1000) |
| Brief Mode | ?brief=True for lists |
| Bulk Ops | List endpoints with PATCH JSON arrays |

### 5.3 HashiCorp Vault (hvac)

| Attribute | Value |
|---|---|
| Protocol | HTTPS |
| Auth | token | approle | kubernetes |
| Secrets Engine | KV v2 |
| Optional | Yes (fallback to env vars) |

### 5.4 CLI Interface

| Attribute | Value |
|---|---|
| Framework | Click |
| Commands | sync, check, bootstrap, config |
| Flags | --dry-run, --prune, --verbose, --quiet, --version |
| Config | --config FILE |

---

## 6. Data Model Requirements

### 6.1 Entity Mapping Summary

| # | vSphere Entity | NetBox Entity | Natural Key |
|---|---|---|---|
| 1 | Datacenter | Site | name |
| 2 | ClusterComputeResource | Cluster | name + site_name |
| 3 | HostSystem | Device | name (FQDN) |
| 4 | DistributedPortGroup | VLAN | vid + site_name |
| 5 | HostVirtualNic | Interface | device_name + name |
| 6 | HostIPConfig | IPAddress | address (CIDR) |
| 7 | Hardware components | InventoryItem | device_name + name + role |
| 8 | Datastore | InventoryItem | device_name + name + "Storage" |

### 6.2 Dependency Graph

```
Site ──────────┬── Cluster
               ├── VLAN
               │
Device ────────┤   (depends on Site + Cluster)
               │
               ├── Interface ─── IPAddress
               ├── InventoryItem (HW)
               └── InventoryItem (Storage)
```

### 6.3 Natural Key Strategy

- Every NetBox object matched by stable business key (not database ID)
- Upsert semantics: lookup by key → PATCH if exists, POST if new
- Natural keys are immutable after creation
- A change in natural key = different object (old one orphaned)

---

## 7. Sync Engine Requirements

### 7.1 Pipeline

```
1. Authenticate     (Vault → env → config → flags)
2. Bootstrap        (Manufacturers, Roles, ClusterTypes, Custom Fields)
3. Collect          (Read all from vSphere, paginated)
4. Fetch            (Read all from NetBox, paginated, brief mode)
5. Diff             (Compute creates, updates, unchanged)
6. Apply            (Execute in dependency order, PATCH/POST)
7. Report           (Summary table + structured logs)
```

### 7.2 Diff Engine

- Compare each desired (vSphere) object against existing (NetBox) by natural key
- Fields compared: all updatable fields (not natural key fields)
- PATCH only if at least one field differs
- Never PATCH natural key fields (name, role, device)

### 7.3 Error Handling

| Scenario | Behaviour |
|---|---|
| vCenter unreachable | Abort early, exit code 2 |
| NetBox unreachable | Abort early, exit code 2 |
| Vault unreachable | Fall back to env vars, log warning |
| Individual entity failure | Log error, continue with others, exit code 1 |
| Natural key collision | Log ERROR, continue, exit code 1 |
| Config validation error | Fail fast, exit code 2 |
| Lock file conflict | Exit with warning, exit code 0 |

### 7.4 Dry-Run

- Compute diff as normal
- Skip all write operations (POST/PATCH)
- Report what WOULD be created/updated
- Same output format as live sync

---

## 8. Security Requirements

### 8.1 Authentication

| System | Method | Token Lifetime |
|---|---|---|
| vCenter | Username + password | Session (SmartConnect) |
| NetBox | v2 API Token | Long-lived (managed externally) |
| Vault | AppRole / K8s / Token | 60 min (auto-renew at 90%) |

### 8.2 Credential Handling

- Never hardcode credentials
- Never log credentials (mask with `****`)
- Never write credentials to disk
- Credentials from: CLI flags → env vars → Vault → config file
- Config file may use `${VAR}` interpolation for env var references

### 8.3 Network Security

- TLS verification enabled by default for all endpoints
- Override with `--no-verify-vcenter` / `--no-verify-netbox` flags
- Vault TLS verification also configurable

---

## 9. Constraints and Assumptions

### 9.1 Constraints

| ID | Constraint | Impact |
|---|---|---|
| C-001 | One-way sync only | vSphere → NetBox, no reverse |
| C-002 | Single vCenter per run | Multiple vCenters = multiple configs |
| C-003 | Cron-driven | Periodic polling, not event-driven |
| C-004 | No concurrent runs | Lock file mechanism required |
| C-005 | CLI-only | No web UI, no dashboard |
| C-006 | Python 3.11+ | Best effort for 7.0, guaranteed 8.0+ |
| C-007 | NetBox 4.5+ | Required for v2 tokens |
| C-008 | vSphere 7.0+ | Best effort for 7.0, guaranteed 8.0+ |
| C-009 | No VM sync | VirtualMachine → NetBox VM is out of scope |
| C-010 | No bidirectional | Risk outweighs benefit |

### 9.2 Assumptions

| ID | Assumption | Risk |
|---|---|---|
| A-001 | Target NetBox has admin access for custom field creation | HIGH — tool will fail if no admin |
| A-002 | vSphere API is accessible from tool's host | MEDIUM — network/firewall |
| A-003 | ESXi hosts have FQDNs resolvable by the tool | MEDIUM — DNS required |
| A-004 | Host FQDNs are unique across all vSphere instances | LOW — by convention |
| A-005 | VLAN IDs are unique per site | LOW — by NetBox design |
| A-006 | Storage backend vendor not always available from vSphere | LOW — description may lack vendor info |

---

## 10. Acceptance Criteria

### 10.1 Functional Acceptance

| ID | Criterion |
|---|---|
| AC-001 | `netbox-vsphere-sync sync` completes without error against test vCenter |
| AC-002 | All 8 entity types synced correctly (manual verification) |
| AC-003 | Re-running sync produces 0 creates, 0 updates (idempotent) |
| AC-004 | `--dry-run` shows changes without modifying NetBox |
| AC-005 | `--prune` deactivates orphaned objects |
| AC-006 | `check` validates all three backends (vCenter, NetBox, Vault) |
| AC-007 | `bootstrap` creates all prerequisite metadata |
| AC-008 | Config loading respects precedence (CLI > env > Vault > YAML) |
| AC-009 | Vault integration works with AppRole auth |
| AC-010 | Lock file prevents concurrent runs |

### 10.2 Non-Functional Acceptance

| ID | Criterion |
|---|---|
| AC-011 | Sync of 500 hosts completes in < 5 minutes |
| AC-012 | Test coverage >= 80% |
| AC-013 | `ruff .` passes with no errors |
| AC-014 | `pyright` passes in strict mode |
| AC-015 | `pip install netbox-vsphere-sync` works |
| AC-016 | All CLI commands have --help output |

### 10.3 Security Acceptance

| ID | Criterion |
|---|---|
| AC-017 | Credentials never appear in log output |
| AC-018 | TLS verification enabled by default |
| AC-019 | Vault token auto-renews before expiry |
| AC-020 | No secrets in source code or config files |

---

## 11. Open Items

| ID | Item | Resolution Needed |
|---|---|---|
| OI-001 | Datastore backend vendor | vSphere doesn't expose storage array vendor. Description may omit "backend: HPE 3PAR" if unavailable. |
| OI-002 | IPv6 handling | Synced identically to IPv4. No special casing. NetBox handles IPv6 natively. |
| OI-003 | Notification mechanism | Log-only for v1. Webhook on failure deferred to v2. |
| OI-004 | Default config path | No default. Explicit --config or NVS_CONFIG env var only. |
| OI-005 | Device status "Maintenance" | Mapped to "Offline". Custom status deferred to v2. |
| OI-006 | InventoryItem roles | 7 hardware roles + Storage. Configurable via YAML mapping. |
| OI-007 | Slug special characters | Auto-derived: lowercase, hyphens, strip special chars. |
| OI-008 | Concurrency safety | Lock file with PID-based staleness detection. |

---

## 12. Appendix: Configuration Schema

```yaml
vcenter:
  host: vc01.example.com
  username: "${VCENTER_USER}"
  password: "${VCENTER_PASS}"
  verify_ssl: true

netbox:
  url: https://netbox.example.com
  token: "${NVS_NETBOX_TOKEN}"
  verify_ssl: true
  timeout: 30

vault:
  enabled: false
  addr: https://vault.example.com:8200
  ssl_verify: true
  namespace: ""
  auth:
    method: approle
    role_id: "${VAULT_ROLE_ID}"
    secret_id: "${VAULT_SECRET_ID}"
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

bootstrap:
  enabled: true
  custom_fields: true

sync:
  entities: [host, cluster, network, interface, inventory, storage]
  dry_run: false
  prune: false
  batch_size: 100
  timeout: 60

vlan_allocation:
  strategy: from_portgroup
  reserved_range_start: 4000
  reserved_range_end: 4094

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

inventory_roles:
  cpu: "CPU"
  memory: "Memory"
  disk: "Storage"
  nic: "NIC"
  controller: "Controller"
  hba: "HBA"
  bios: "BIOS"
  fallback: "Hardware"
```

---

> **End of SRS.** This document should be reviewed and approved before
> implementation begins. Any changes to requirements must be reflected in
> this document and communicated to all stakeholders.
