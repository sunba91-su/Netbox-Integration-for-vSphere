# Software Architecture: netbox-vsphere-sync

## Table of Contents

1. [System Context Diagram](#1-system-context-diagram)
2. [Component Diagram](#2-component-diagram)
3. [Database Design](#3-database-design)
4. [API Design](#4-api-design)
5. [Security Design](#5-security-design)
6. [Deployment Design](#6-deployment-design)

---

## 1. System Context Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          System Context Diagram                              │
│                                                                              │
│  ┌─────────────┐                                                             │
│  │  Platform   │──── cron ────┐                                              │
│  │  Operator   │              │                                              │
│  └─────────────┘              ▼                                              │
│                     ┌─────────────────────┐                                  │
│                     │ netbox-vsphere-sync  │                                  │
│                     │    (CLI + engine)    │                                  │
│                     └────┬──────┬──────┬──┘                                  │
│                          │      │      │                                     │
│              ┌───────────┘      │      └───────────┐                        │
│              ▼                  ▼                   ▼                        │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────┐                │
│  │   vCenter    │   │   NetBox     │   │ HashiCorp Vault  │                │
│  │  (vSphere)   │   │  (IPAM/DCIM) │   │  (secrets, opt.) │                │
│  └──────────────┘   └──────────────┘   └──────────────────┘                │
│                                                                              │
│  External actors:                                                            │
│  ┌──────────────┐                                                            │
│  │  Infra Eng.  │──── configures ────▶ config.yaml + env vars               │
│  └──────────────┘                                                            │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.1 System Boundary

| Boundary | What's Inside | What's Outside |
|---|---|---|
| **netbox-vsphere-sync** | CLI, sync engine, config loader, reporters | vCenter, NetBox, Vault, user |
| **External: vCenter** | VMware vSphere 7.0+ / 8.0+ | Tool reads only |
| **External: NetBox** | NetBox 4.5+ REST API | Tool reads + writes |
| **External: Vault** | HashiCorp Vault KV v2 (optional) | Tool reads secrets |
| **External: Scheduling** | cron, systemd timer, K8s CronJob | Triggers the CLI |

### 1.2 Data Flows

| Flow | Direction | Protocol | Authentication | Frequency |
|---|---|---|---|---|
| Inventory read | vCenter → Tool | HTTPS (PyVmomi) | Username + password | Per sync run |
| State read + write | Tool ↔ NetBox | HTTPS (pynetbox) | v2 API Token (nbt_*) | Per sync run |
| Secret read | Tool ← Vault | HTTPS (hvac) | AppRole / Token / K8s | Per sync run |
| Trigger | Operator → Tool | CLI / cron | N/A | Every 15 min (configurable) |

### 1.3 User Classes

| Actor | Interaction | Notes |
|---|---|---|
| Platform Operator | Runs CLI, monitors logs, manages cron | Primary user |
| Infrastructure Engineer | Configures tool, sets up Vault, writes config.yaml | Setup + maintenance |
| NetBox Admin | Reviews synced data, manages NetBox instance | Read-only on tool |

---

## 2. Component Diagram

### 2.1 High-Level Component Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     Component Architecture (DDD Layers)                      │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │  CLI LAYER  (presentation)                                              │ │
│  │                                                                         │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │ │
│  │  │   app.py │ │  sync    │ │  check   │ │bootstrap │ │ config   │   │ │
│  │  │  (group) │ │ command  │ │ command  │ │ command  │ │ command  │   │ │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘   │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                      │                                       │
│                                      ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │  APPLICATION LAYER  (use cases)                                         │ │
│  │                                                                         │ │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ │ │
│  │  │ SyncEngine   │ │ DiffEngine   │ │ Dependency   │ │ Bootstrapper │ │ │
│  │  │ (orchestrate)│ │ (compute)    │ │ Resolver     │ │ (metadata)   │ │ │
│  │  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘ │ │
│  │  ┌──────────────┐                                                      │ │
│  │  │  EventLog    │                                                      │ │
│  │  └──────────────┘                                                      │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                      │                                       │
│                    ┌─────────────────┼─────────────────┐                     │
│                    ▼                 ▼                   ▼                     │
│  ┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────┐   │
│  │  DOMAIN LAYER       │ │  INFRASTRUCTURE    │ │  OBSERVABILITY     │   │
│  │  (core logic)       │ │  (adapters)        │ │  (reports)         │   │
│  │                     │ │                    │ │                    │   │
│  │  ┌──────────────┐  │ │  ┌──────────────┐  │ │  ┌──────────────┐  │   │
│  │  │ Entities     │  │ │  │ VSphereACL   │  │ │  │ ReportGen    │  │   │
│  │  │ Value Objects │  │ │  │ (PyVmomi)    │  │ │  │ (Rich/JSON)  │  │   │
│  │  │ Events       │  │ │  └──────────────┘  │ │  └──────────────┘  │   │
│  │  │ Ports        │  │ │  ┌──────────────┐  │ │                    │   │
│  │  │ Exceptions   │  │ │  │ NetBoxACL    │  │ │                    │   │
│  │  └──────────────┘  │ │  │ (pynetbox)   │  │ │                    │   │
│  │  ┌──────────────┐  │ │  └──────────────┘  │ │                    │   │
│  │  │ Config Model │  │ │  ┌──────────────┐  │ │                    │   │
│  │  │ (Pydantic)   │  │ │  │ VaultACL     │  │ │                    │   │
│  │  └──────────────┘  │ │  │ (hvac)       │  │ │                    │   │
│  │                     │ │  └──────────────┘  │ │                    │   │
│  │                     │ │  ┌──────────────┐  │ │                    │   │
│  │                     │ │  │ ConfigLoader │  │ │                    │   │
│  │                     │ │  │ (YAML+env)   │  │ │                    │   │
│  │                     │ │  └──────────────┘  │ │                    │   │
│  └─────────────────────┘ └─────────────────────┘ └─────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Component Details

#### CLI Layer

| Component | File | Responsibility | Dependencies |
|---|---|---|---|
| **app.py** | `cli/app.py` | Click group, global options (--config, --dry-run, --verbose) | ConfigLoader |
| **sync command** | `cli/commands/sync.py` | Entry point for `sync` subcommand | SyncEngine, ReportGenerator |
| **check command** | `cli/commands/check.py` | Validates connectivity to all backends | VSphereACL, NetBoxACL, VaultACL |
| **bootstrap command** | `cli/commands/bootstrap.py` | Creates prerequisite NetBox metadata | NetBoxACL (bootstrap_metadata) |
| **config command** | `cli/commands/config.py` | Prints effective configuration | ConfigLoader |

#### Application Layer

| Component | File | Responsibility | Dependencies |
|---|---|---|---|
| **SyncEngine** | `application/sync_engine.py` | Orchestrates full sync pipeline: collect → fetch → diff → apply → report | DiffEngine, DependencyResolver, VSphereACL, NetBoxACL, EventLog |
| **DiffEngine** | `application/diff_engine.py` | Computes creates/updates/unchanged by comparing desired vs existing | Domain entities |
| **DependencyResolver** | `application/dependency_resolver.py` | Ensures entity types are processed in topological order | DependencyOrder value object |
| **Bootstrapper** | `application/bootstrapper.py` | Creates prerequisite NetBox metadata (manufacturers, roles, types, custom fields) | NetBoxACL |
| **EventLog** | `application/event_log.py` | Collects DomainEvents during a sync run | DomainEvent |

#### Domain Layer

| Component | File | Responsibility | Dependencies |
|---|---|---|---|
| **Entities** | `domain/model/*.py` | Site, Cluster, Device, VLAN, Interface, IPAddress, InventoryItem | Value Objects |
| **Value Objects** | `domain/model/*.py` | ManagedObjectRef, ESXiVersion, MemoryBytes, CpuInfo, VLANTag, IPNetmask, Slug, NaturalKey | None |
| **Events** | `domain/events.py` | DomainEvent hierarchy: EntityCreated, EntityUpdated, EntityFailed, SyncStarted, SyncCompleted | None |
| **Ports** | `domain/ports.py` | Repository protocols (typing.Protocol): VSphereInventoryRepository, SiteRepository, DeviceRepository, etc. | Domain entities |
| **Exceptions** | `domain/exceptions.py` | SyncError, VSphereConnectionError, NetBoxAPIError, VaultAuthError, ConfigurationError | None |
| **Constants** | `domain/constants.py` | DEPENDENCY_ORDER, DEFAULT_INVENTORY_ROLES, DEFAULT_VSYNC_FIELDS | None |

#### Infrastructure Layer

| Component | File | Responsibility | Dependencies |
|---|---|---|---|
| **VSphereACL** | `infrastructure/vsphere/acl.py` | Translates PyVmomi API responses → domain objects | PyVmomi |
| **VSphereCollector** | `infrastructure/vsphere/collector.py` | Paginated collection of all vSphere entities | VSphereACL |
| **NetBoxACL** | `infrastructure/netbox/acl.py` | Translates domain objects ↔ NetBox API payloads | pynetbox |
| **NetBox Repositories** | `infrastructure/netbox/repositories/*.py` | Per-entity repository implementations | pynetbox, domain entities |
| **VaultACL** | `infrastructure/vault/acl.py` | Wraps hvac client, reads KV v2 secrets | hvac |
| **ConfigLoader** | `infrastructure/config/loader.py` | Loads YAML + env vars + CLI overrides → AppConfig | Pydantic, YAML |
| **SecretResolver** | `infrastructure/config/secret_resolver.py` | Resolves credentials from Vault or env vars | VaultACL |

### 2.3 Dependency Flow Diagram

```
┌──────────────┐
│   CLI Layer  │──── imports ────▶ Application Layer
└──────────────┘                        │
                                        │ imports
                                        ▼
                               ┌──────────────┐
                               │ Domain Layer  │
                               └──────────────┘
                                        ▲
                                        │ imports
                               ┌────────────────┐
                               │ Infrastructure  │
                               │    Layer        │
                               └────────────────┘
```

**Dependency Rule:** Upper layers import lower layers. Lower layers never import upper layers. Domain layer imports nothing from Infrastructure.

### 2.4 Interaction Sequence (Sync Run)

```
Operator        CLI         App          Domain       Infra        vCenter    NetBox     Vault
   │             │           │            │            │             │          │          │
   │── sync ────▶│           │            │            │             │          │          │
   │             │── load ──▶│            │            │             │          │          │
   │             │           │── load ────┼───────────▶│             │          │          │
   │             │           │            │            │── read ────┼──────────┼──────────│
   │             │           │            │            │◀── secrets ─┼──────────┼──────────│
   │             │           │            │            │             │          │          │
   │             │           │── connect ─┼───────────▶│             │          │          │
   │             │           │            │            │── SmartConnect ──────▶│          │
   │             │           │            │            │◀── OK ─────────────────│          │
   │             │           │            │            │             │          │          │
   │             │           │── bootstrap┼───────────▶│             │          │          │
   │             │           │            │            │── create CFs ─────────▶│          │
   │             │           │            │            │◀── done ───────────────│          │
   │             │           │            │            │             │          │          │
   │             │           │── collect ─┼───────────▶│             │          │          │
   │             │           │            │            │── retrieveProps ──────▶│          │
   │             │           │            │            │◀── hosts/clusters/etc ─│          │
   │             │           │            │            │             │          │          │
   │             │           │── fetch ───┼───────────▶│             │          │          │
   │             │           │            │            │── GET sites/devices ──▶│          │
   │             │           │            │            │◀── existing state ─────│          │
   │             │           │            │            │             │          │          │
   │             │           │── diff ────┼───────────▶│             │          │          │
   │             │           │            │◀── creates/updates ─────│          │          │
   │             │           │            │            │             │          │          │
   │             │           │── apply ───┼───────────▶│             │          │          │
   │             │           │            │            │── PATCH/POST ─────────▶│          │
   │             │           │            │            │◀── done ───────────────│          │
   │             │           │            │            │             │          │          │
   │             │           │── report ──┼───────────▶│             │          │          │
   │             │◀── table ─│            │            │             │          │          │
   │◀── output ──│           │            │            │             │          │          │
```

---

## 3. Database Design

### 3.1 Overview

This tool is **stateless** — it has no local database. NetBox is the system of record for all synced data. The tool reads from vSphere and writes to NetBox on each run.

### 3.2 NetBox Data Model (Tool's View)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      NetBox Data Model (Tool's View)                         │
│                                                                              │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────────────────────┐ │
│  │   Site       │◀────│   Cluster    │◀────│   Device                     │ │
│  │  (DCIM)     │     │  (Virtual)   │     │  (DCIM)                     │ │
│  │             │     │              │     │                              │ │
│  │ name (NK)   │     │ name + site  │     │ name (NK) = FQDN           │ │
│  │ slug        │     │  (NK)        │     │ role = "ESXi Server"        │ │
│  │ description │     │ type         │     │ device_type (FK)            │ │
│  │ cf: vcenter │     │  = "vSphere  │     │ site (FK)                   │ │
│  │  _mor       │     │   Cluster"   │     │ cluster (FK)                │ │
│  └──────────────┘     │ site (FK)    │     │ status                      │ │
│                       │ cf: vcenter  │     │ cf: vcenter_*               │ │
│                       │  _mor, _ha,  │     └──────────┬──────────────────┘ │
│                       │  _drs, _cpu, │                │                    │
│                       │  _memory     │       ┌────────┼────────┐          │
│                       └──────────────┘       │        │        │          │
│                                              ▼        ▼        ▼          │
│  ┌──────────────┐     ┌──────────────┐  ┌────────┐ ┌────────┐ ┌────────┐ │
│  │   VLAN       │     │  IPAddress   │  │Interfac│ │InvItem │ │InvItem │ │
│  │  (IPAM)     │     │  (IPAM)      │  │e (DCIM)│ │(HW)    │ │(Stor)  │ │
│  │             │     │              │  │(DCIM)  │ │(DCIM)  │ │(DCIM)  │ │
│  │ vid + site  │     │ address (NK) │  │        │ │        │ │        │ │
│  │  (NK)       │     │ status       │  │dev +   │ │dev +   │ │dev +   │ │
│  │ name        │     │ role         │  │name    │ │name +  │ │name +  │ │
│  │ site (FK)   │     │ interface    │  │(NK)    │ │role    │ │"Stor"  │ │
│  │ cf: vcenter │     │  (FK)        │  │type    │ │(NK)    │ │(NK)    │ │
│  │  _mor       │     │ dns_name     │  │mtu     │ │role    │ │role    │ │
│  └──────────────┘     │ description  │  │mac     │ │mfr     │ │desc    │ │
│                       └──────────────┘  │enabled │ │serial  │ │cf:     │ │
│                                         └────────┘ │part_id │ │storage │ │
│                                                    └────────┘ │_*      │ │
│                                                               └────────┘ │
│  NK = Natural Key    cf = Custom Field    FK = Foreign Key                │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.3 Custom Fields (Tool-Managed)

| Model | Field Name | Type | Content Type | Required | Filter Logic |
|---|---|---|---|---|---|
| dcim.Site | `vcenter_mor` | Text | extras.customfield | No | `cf_vcenter_mor` |
| virtualization.Cluster | `vcenter_mor` | Text | extras.customfield | No | `cf_vcenter_mor` |
| virtualization.Cluster | `vcenter_ha_enabled` | Boolean | extras.customfield | No | `cf_vcenter_ha_enabled` |
| virtualization.Cluster | `vcenter_drs_enabled` | Boolean | extras.customfield | No | `cf_vcenter_drs_enabled` |
| virtualization.Cluster | `vcenter_drs_level` | Text | extras.customfield | No | `cf_vcenter_drs_level` |
| virtualization.Cluster | `vcenter_cluster_cpu_mhz` | Integer | extras.customfield | No | `cf_vcenter_cluster_cpu_mhz` |
| virtualization.Cluster | `vcenter_cluster_memory_mb` | Integer | extras.customfield | No | `cf_vcenter_cluster_memory_mb` |
| dcim.Device | `vcenter_mor` | Text | extras.customfield | No | `cf_vcenter_mor` |
| dcim.Device | `vcenter_esxi_version` | Text | extras.customfield | No | `cf_vcenter_esxi_version` |
| dcim.Device | `vcenter_esxi_build` | Text | extras.customfield | No | `cf_vcenter_esxi_build` |
| dcim.Device | `vcenter_power_state` | Text | extras.customfield | No | `cf_vcenter_power_state` |
| dcim.Device | `vcenter_cpu_cores` | Integer | extras.customfield | No | `cf_vcenter_cpu_cores` |
| dcim.Device | `vcenter_cpu_threads` | Integer | extras.customfield | No | `cf_vcenter_cpu_threads` |
| dcim.Device | `vcenter_cpu_model` | Text | extras.customfield | No | `cf_vcenter_cpu_model` |
| dcim.Device | `vcenter_memory_bytes` | Integer | extras.customfield | No | `cf_vcenter_memory_bytes` |
| ipam.VLAN | `vcenter_mor` | Text | extras.customfield | No | `cf_vcenter_mor` |
| dcim.InventoryItem | `storage_free_bytes` | Integer | extras.customfield | No | `cf_storage_free_bytes` |
| dcim.InventoryItem | `storage_backend_type` | Text | extras.customfield | No | `cf_storage_backend_type` |
| dcim.InventoryItem | `storage_shared` | Boolean | extras.customfield | No | `cf_storage_shared` |

### 3.4 Natural Key Mapping

Each entity type has a natural key used for upsert semantics:

| Entity | Natural Key Fields | NetBox Lookup | Example |
|---|---|---|---|
| Site | `name` | `sites.get(name="DC1")` | `"DC1"` |
| Cluster | `name` + `site_name` | `clusters.get(name="ClusterA", site_id=1)` | `"ClusterA" + "DC1"` |
| Device | `name` | `devices.get(name="esxi-01a.example.com")` | `"esxi-01a.example.com"` |
| VLAN | `vid` + `site_name` | `vlans.get(vid=100, site_id=1)` | `100 + "DC1"` |
| Interface | `device_name` + `name` | `interfaces.get(device_id=1, name="vmk0")` | `"esxi-01a" + "vmk0"` |
| IPAddress | `address` | `ip_addresses.get(address="10.0.0.10/24")` | `"10.0.0.10/24"` |
| InventoryItem | `device_name` + `name` + `role` | `inventory_items.get(device_id=1, name="CPU-0", role_id=1)` | `"esxi-01a" + "CPU-0" + "CPU"` |

### 3.5 Local State Files

| File | Purpose | Format | Lifecycle |
|---|---|---|---|
| `/tmp/nvs-sync.lock` | Prevent concurrent runs | PID file | Created at start, deleted at exit |
| `config.yaml` | User-provided configuration | YAML | Persistent, user-managed |

---

## 4. API Design

### 4.1 vSphere API (PyVmomi — Read Only)

| Operation | PyVmomi Method | Returns | Pagination |
|---|---|---|---|
| Connect | `SmartConnect(host, user, pwd)` | `ServiceInstance` | N/A |
| Get content | `si.RetrieveContent()` | `ServiceInstanceContent` | N/A |
| Create view | `container_view.CreateContainerView()` | `ContainerView` | N/A |
| Retrieve props | `PropertyCollector.RetrievePropertiesEx()` | `ObjectSet[]` | `token` for next page |
| Continue retrieve | `PropertyCollector.ContinueRetrievePropertiesEx()` | `ObjectSet[]` | `None` = done |

**Entity retrieval:**

| Entity | PyVmomi Type | Key Properties |
|---|---|---|
| Datacenter | `Datacenter` | `name`, `hostFolder`, `vmFolder` |
| Cluster | `ClusterComputeResource` | `name`, `configuration`, `host`, `datastore` |
| Host | `HostSystem` | `name`, `config`, `hardware`, `runtime`, `network` |
| Port Group | `DistributedPortGroup` | `name`, `config.defaultPortConfig`, `vlan` |
| VMkernel | `HostVirtualNic` | `device`, `spec.mac`, `spec.mtu`, `spec.ip` |
| Datastore | `Datastore` | `name`, `summary`, `host`, `info` |

**Property filter per entity type:**

```python
HOST_PROPERTIES = [
    "name", "config.product", "hardware.cpuPkg", "hardware.memoryModules",
    "hardware.biosInfo", "runtime.connectionState", "runtime.powerState",
    "runtime.inMaintenanceMode", "config.network", "network",
    "config.storageDevice", "datastore", "parent"
]

CLUSTER_PROPERTIES = [
    "name", "configuration.drsConfig", "configuration.dasConfig",
    "host", "datastore", "parent"
]
```

### 4.2 NetBox REST API (pynetbox — Read + Write)

#### 4.2.1 Read Operations (Paginated)

| Entity | Endpoint | Query Params | Brief Mode |
|---|---|---|---|
| Sites | `GET /api/dcim/sites/` | `?limit=100&brief=True` | Yes |
| Clusters | `GET /api/virtualization/clusters/` | `?limit=100&brief=True&config_context=false` | Yes |
| Devices | `GET /api/dcim/devices/` | `?limit=100&brief=True&config_context=false` | Yes |
| VLANs | `GET /api/ipam/vlans/` | `?limit=100&brief=True` | Yes |
| Interfaces | `GET /api/dcim/interfaces/` | `?device=<name>&limit=100&brief=True` | Yes |
| IPAddresses | `GET /api/ipam/ip-addresses/` | `?limit=100&brief=True` | Yes |
| InventoryItems | `GET /api/dcim/inventory-items/` | `?device=<name>&limit=100&brief=True` | Yes |
| Manufacturers | `GET /api/dcim/manufacturers/` | `?limit=100` | No |
| DeviceRoles | `GET /api/dcim/device-roles/` | `?limit=100` | No |
| DeviceTypes | `GET /api/dcim/device-types/` | `?limit=100` | No |
| ClusterTypes | `GET /api/virtualization/cluster-types/` | `?limit=100` | No |
| CustomFields | `GET /api/extras/custom-fields/` | `?limit=100` | No |

#### 4.2.2 Write Operations

| Operation | Method | Endpoint | Payload |
|---|---|---|---|
| Create Site | `POST /api/dcim/sites/` | `{name, slug, description, custom_fields}` |
| Update Site | `PATCH /api/dcim/sites/{id}/` | `{description, custom_fields}` |
| Create Cluster | `POST /api/virtualization/clusters/` | `{name, type, site, group, custom_fields}` |
| Update Cluster | `PATCH /api/virtualization/clusters/{id}/` | `{custom_fields}` |
| Create Device | `POST /api/dcim/devices/` | `{name, device_type, device_role, site, cluster, status, custom_fields}` |
| Update Device | `PATCH /api/dcim/devices/{id}/` | `{status, custom_fields}` |
| Create VLAN | `POST /api/ipam/vlans/` | `{vid, name, site, description, custom_fields}` |
| Create Interface | `POST /api/dcim/interfaces/` | `{device, name, type, enabled, mtu, mac_address, description}` |
| Update Interface | `PATCH /api/dcim/interfaces/{id}/` | `{enabled, mtu}` |
| Create IPAddress | `POST /api/ipam/ip-addresses/` | `{address, interface, status, role, dns_name, description}` |
| Create InventoryItem | `POST /api/dcim/inventory-items/` | `{device, name, role, manufacturer, part_id, serial, description, discovered}` |
| Update InventoryItem | `PATCH /api/dcim/inventory-items/{id}/` | `{description, serial, part_id, manufacturer}` |
| Create Manufacturer | `POST /api/dcim/manufacturers/` | `{name, slug}` |
| Create DeviceRole | `POST /api/dcim/device-roles/` | `{name, slug}` |
| Create DeviceType | `POST /api/dcim/device-types/` | `{model, manufacturer, slug}` |
| Create ClusterType | `POST /api/virtualization/cluster-types/` | `{name, slug}` |
| Create CustomField | `POST /api/extras/custom-fields/` | `{content_types, name, type, label}` |

#### 4.2.3 Bulk Operations

The tool iterates and PATCHes per entity (NetBox has no true bulk API):

```python
for host in hosts:
    device = nb.dcim.devices.get(name=host.name)
    if device:
        device.custom_fields["vcenter_esxi_version"] = host.version.version
        device.save()
```

### 4.3 Vault API (hvac — Optional)

| Operation | hvac Method | Endpoint | Response |
|---|---|---|---|
| AppRole login | `client.auth.approle.login()` | `POST /v1/auth/approle/login` | `{auth: {client_token, ttl}}` |
| Token login | `client.token = token` | N/A | N/A |
| K8s login | `client.auth.kubernetes.login()` | `POST /v1/auth/kubernetes/login` | `{auth: {client_token, ttl}}` |
| Read KV v2 | `client.secrets.kv.v2.read_secret_version()` | `GET /v1/{mount}/data/{path}` | `{data: {data: {key: value}}}` |
| Token lookup | `client.token_lookup()` | `POST /v1/auth/token/lookup` | `{data: {ttl, ...}}` |
| Token renew | `client.renew_token()` | `POST /v1/auth/token/renew-self` | `{auth: {ttl}}` |

### 4.4 CLI Interface

```
netbox-vsphere-sync [OPTIONS] COMMAND [ARGS]...

Global Options:
  -c, --config FILE        Path to YAML config file  [env: NVS_CONFIG]
  --vcenter-host TEXT      vCenter hostname  [env: NVS_VCENTER_HOST]
  --vcenter-user TEXT      vCenter username  [env: NVS_VCENTER_USER]
  --vcenter-pass TEXT      vCenter password  [env: NVS_VCENTER_PASS]
  --netbox-url TEXT        NetBox base URL  [env: NVS_NETBOX_URL]
  --netbox-token TEXT      NetBox API token  [env: NVS_NETBOX_TOKEN]
  --vault-addr TEXT        Vault server address  [env: VAULT_ADDR]
  --vault-role-id TEXT     Vault AppRole RoleID  [env: VAULT_ROLE_ID]
  --vault-secret-id TEXT   Vault AppRole SecretID  [env: VAULT_SECRET_ID]
  --dry-run                Preview changes without applying
  --prune                  Remove orphaned objects (opt-in)
  --verbose / --quiet      Log verbosity
  --version                Show version and exit

Commands:
  sync       Run a full synchronization
  bootstrap  Create prerequisite NetBox objects only
  check      Validate connectivity to vCenter, NetBox, and Vault
  config     Print effective configuration and exit
```

---

## 5. Security Design

### 5.1 Authentication Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      Authentication Architecture                              │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                    Credential Resolution Order                         │  │
│  │                                                                        │  │
│  │   Priority 1 (highest): CLI flags                                      │  │
│  │     --vcenter-host, --vcenter-user, --vcenter-pass                    │  │
│  │     --netbox-url, --netbox-token                                       │  │
│  │                                                                        │  │
│  │   Priority 2: Environment variables                                    │  │
│  │     NVS_VCENTER_HOST, NVS_VCENTER_USER, NVS_VCENTER_PASS            │  │
│  │     NVS_NETBOX_URL, NVS_NETBOX_TOKEN                                  │  │
│  │                                                                        │  │
│  │   Priority 3: Vault secrets (if vault.enabled)                         │  │
│  │     kv-v2/vcenter/creds → VCENTER_USER, VCENTER_PASS                 │  │
│  │     kv-v2/netbox/api-token → NVS_NETBOX_TOKEN                        │  │
│  │                                                                        │  │
│  │   Priority 4: YAML config file                                         │  │
│  │     vcenter.host, vcenter.username, vcenter.password                  │  │
│  │     netbox.url, netbox.token                                          │  │
│  │                                                                        │  │
│  │   Priority 5 (lowest): Defaults                                        │  │
│  │     None (fails with actionable error)                                 │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐                    │
│  │   vCenter    │   │   NetBox     │   │   Vault      │                    │
│  │              │   │              │   │              │                    │
│  │ Auth:        │   │ Auth:        │   │ Auth:        │                    │
│  │ SmartConnect │   │ v2 API Token │   │ AppRole /    │                    │
│  │ (user+pass)  │   │ (nbt_*.*)    │   │ Token / K8s  │                    │
│  │              │   │              │   │              │                    │
│  │ Session:     │   │ Token:       │   │ Token:       │                    │
│  │ per-run      │   │ long-lived   │   │ 60 min TTL   │                    │
│  │              │   │ (managed     │   │ auto-renew   │                    │
│  │              │   │  externally) │   │ at 90%       │                    │
│  └──────────────┘   └──────────────┘   └──────────────┘                    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Credential Handling Rules

| Rule | Implementation |
|---|---|
| Never hardcode | All credentials from env, Vault, or config (with `${VAR}` interpolation) |
| Never log credentials | Mask with `****` in all log output; structlog processor filters sensitive keys |
| Never write to disk | Credentials exist only in memory during execution |
| Mask in verbose mode | `--verbose` shows `VCENTER_PASS=****`, `NVS_NETBOX_TOKEN=****` |
| No YAML secrets | Config file references env vars or Vault paths, never plaintext secrets |

### 5.3 TLS Configuration

| Endpoint | Default | Override | Verification |
|---|---|---|---|
| vCenter | `verify_ssl: true` | `--no-verify-vcenter` flag or `vcenter.verify_ssl: false` in YAML | SSL cert verification |
| NetBox | `verify_ssl: true` | `--no-verify-netbox` flag or `netbox.verify_ssl: false` in YAML | SSL cert verification |
| Vault | `ssl_verify: true` | `vault.ssl_verify: false` in YAML | SSL cert verification |

### 5.4 Lock File Security

```
Lock Acquisition:
1. Check if /tmp/nvs-sync.lock exists
2. If exists:
   a. Read PID from file
   b. Check if process with that PID is alive (os.kill(pid, 0))
   c. If alive: exit with warning (code 0) — another run in progress
   d. If dead (stale): overwrite lock file, proceed
3. If not exists: create lock file with current PID
4. Register atexit handler to delete lock file

Lock Release:
- atexit handler deletes /tmp/nvs-sync.lock
- SIGTERM handler also deletes lock file
- On crash: lock file contains stale PID, detected on next run
```

### 5.5 NetBox Permission Requirements

The NetBox API token must have these permissions:

| Endpoint | Method | Required Permission |
|---|---|---|
| `/api/dcim/sites/` | GET, POST, PATCH | `dcim.view_site`, `dcim.add_site`, `dcim.change_site` |
| `/api/dcim/devices/` | GET, POST, PATCH | `dcim.view_device`, `dcim.add_device`, `dcim.change_device` |
| `/api/dcim/interfaces/` | GET, POST, PATCH | `dcim.view_interface`, `dcim.add_interface`, `dcim.change_interface` |
| `/api/dcim/inventory-items/` | GET, POST, PATCH | `dcim.view_inventoryitem`, `dcim.add_inventoryitem`, `dcim.change_inventoryitem` |
| `/api/dcim/manufacturers/` | GET, POST | `dcim.view_manufacturer`, `dcim.add_manufacturer` |
| `/api/dcim/device-roles/` | GET, POST | `dcim.view_devicerole`, `dcim.add_devicerole` |
| `/api/dcim/device-types/` | GET, POST | `dcim.view_devicetype`, `dcim.add_devicetype` |
| `/api/virtualization/clusters/` | GET, POST, PATCH | `virtualization.view_cluster`, `virtualization.add_cluster`, `virtualization.change_cluster` |
| `/api/virtualization/cluster-types/` | GET, POST | `virtualization.view_clustertype`, `virtualization.add_clustertype` |
| `/api/ipam/vlans/` | GET, POST | `ipam.view_vlan`, `ipam.add_vlan` |
| `/api/ipam/ip-addresses/` | GET, POST | `ipam.view_ipaddress`, `ipam.add_ipaddress` |
| `/api/extras/custom-fields/` | GET, POST | `extras.view_customfield`, `extras.add_customfield` |

---

## 6. Deployment Design

### 6.1 Deployment Options

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      Deployment Topology Options                              │
│                                                                              │
│  Option 1: VM / Bare-metal + cron                                            │
│  ┌──────────────────────────────────────┐                                   │
│  │  Linux VM / Bare-metal server        │                                   │
│  │  ├── Python 3.11+                    │                                   │
│  │  ├── pip install netbox-vsphere-sync │                                   │
│  │  ├── /etc/netbox-vsphere-sync/       │                                   │
│  │  │   └── config.yaml                 │                                   │
│  │  ├── cron: */15 * * * *             │                                   │
│  │  └── /var/log/netbox-vsphere-sync.log│                                   │
│  └──────────────────────────────────────┘                                   │
│                                                                              │
│  Option 2: Docker container + cron                                           │
│  ┌──────────────────────────────────────┐                                   │
│  │  Docker Host / Docker Compose        │                                   │
│  │  ├── nvs-sync:latest (image)         │                                   │
│  │  ├── /config/config.yaml (bind mount)│                                   │
│  │  ├── /var/log/ (bind mount)          │                                   │
│  │  └── docker run + cron               │                                   │
│  └──────────────────────────────────────┘                                   │
│                                                                              │
│  Option 3: Kubernetes CronJob                                                │
│  ┌──────────────────────────────────────┐                                   │
│  │  Kubernetes cluster                  │                                   │
│  │  ├── CronJob: netbox-vsphere-sync    │                                   │
│  │  │   schedule: "*/15 * * * *"        │                                   │
│  │  │   image: nvs-sync:latest          │                                   │
│  │  │   env:                            │                                   │
│  │  │     - NVS_VCENTER_HOST            │                                   │
│  │  │     - NVS_VCENTER_USER            │                                   │
│  │  │     - NVS_VCENTER_PASS (from Secret)│                                  │
│  │  │     - NVS_NETBOX_URL              │                                   │
│  │  │     - NVS_NETBOX_TOKEN (from Secret)│                                 │
│  │  │   secrets:                        │                                   │
│  │  │     - nvs-vcenter-creds           │                                   │
│  │  │     - nvs-netbox-token            │                                   │
│  │  │   volumeMounts:                   │                                   │
│  │  │     - /etc/netbox-vsphere-sync    │                                   │
│  │  └── ConfigMap: nvs-config           │                                   │
│  └──────────────────────────────────────┘                                   │
│                                                                              │
│  Option 4: Kubernetes + Vault                                                │
│  ┌──────────────────────────────────────┐                                   │
│  │  Kubernetes cluster + HashiCorp Vault│                                   │
│  │  ├── CronJob (same as Option 3)      │                                   │
│  │  ├── ServiceAccount with K8s auth    │                                   │
│  │  ├── Vault K8s auth method           │                                   │
│  │  └── Secrets read from Vault at runtime│                                  │
│  └──────────────────────────────────────┘                                   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 6.2 Dockerfile

```dockerfile
FROM python:3.11-slim AS base

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY src/ src/

RUN useradd --create-home nvs
USER nvs

VOLUME ["/etc/netbox-vsphere-sync"]

ENTRYPOINT ["netbox-vsphere-sync"]
```

### 6.3 Kubernetes CronJob

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: netbox-vsphere-sync
  namespace: infrastructure
spec:
  schedule: "*/15 * * * *"
  concurrencyPolicy: Forbid
  successfulJobsHistoryLimit: 3
  failedJobsHistoryLimit: 3
  jobTemplate:
    spec:
      backoffLimit: 2
      activeDeadlineSeconds: 300
      template:
        spec:
          serviceAccountName: netbox-vsphere-sync
          restartPolicy: OnFailure
          containers:
            - name: nvs-sync
              image: registry.example.com/netbox-vsphere-sync:1.0.0
              args: ["sync", "--config", "/etc/nvs/config.yaml"]
              envFrom:
                - secretRef:
                    name: nvs-vcenter-creds
                - secretRef:
                    name: nvs-netbox-token
              volumeMounts:
                - name: config
                  mountPath: /etc/nvs
                  readOnly: true
              resources:
                requests:
                  cpu: 100m
                  memory: 128Mi
                limits:
                  cpu: 500m
                  memory: 256Mi
          volumes:
            - name: config
              configMap:
                name: nvs-config
```

### 6.4 Systemd Timer

```ini
[Unit]
Description=NetBox vSphere Sync
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/netbox-vsphere-sync sync \
    --config /etc/netbox-vsphere-sync/config.yaml
StandardOutput=append:/var/log/netbox-vsphere-sync.log
StandardError=append:/var/log/netbox-vsphere-sync.log
User=nvs
Group=nvs
```

```ini
[Unit]
Description=Run NetBox vSphere Sync every 15 minutes

[Timer]
OnBootSec=5min
OnUnitActiveSec=15min
Persistent=true

[Install]
WantedBy=timers.target
```

### 6.5 CI/CD Pipeline

```
Push to main ──▶ ┌──────────┐
                 │  Lint    │ ──▶ ruff check + ruff format --check
                 └────┬─────┘
                      │
                 ┌────▼─────┐
                 │ Typecheck│ ──▶ pyright --strict
                 └────┬─────┘
                      │
                 ┌────▼─────┐
                 │   Test   │ ──▶ pytest --cov=netbox_vsphere_sync
                 └────┬─────┘
                      │
                 ┌────▼─────┐
                 │  Build   │ ──▶ python -m build
                 └────┬─────┘
                      │
                 ┌────▼─────┐
                 │  Publish │ ──▶ twine upload (PyPI)
                 └──────────┘

Tag v1.x.x ──▶ Build Docker image ──▶ Push to registry
```

### 6.6 Network Requirements

| Source | Destination | Port | Protocol | Purpose |
|---|---|---|---|---|
| Tool host | vCenter | 443 | HTTPS | PyVmomi SmartConnect |
| Tool host | NetBox | 443 | HTTPS | REST API (pynetbox) |
| Tool host | Vault | 8200 | HTTPS | KV v2 secrets (optional) |
| Kubernetes pod | Vault | 8200 | HTTPS | K8s auth method (optional) |

### 6.7 Resource Requirements

| Metric | Value | Notes |
|---|---|---|
| CPU | 100-500m | Depends on inventory size |
| Memory | 128-256 MiB | vSphere collection is the main consumer |
| Disk | < 10 MiB | No local storage (stateless) |
| Network | Low bandwidth | API calls only, no bulk data transfer |
| Duration | < 5 min | For 500 ESXi hosts |
| Frequency | Every 15 min | Configurable via cron/scheduler |

---

> **End of Software Architecture.** This document should be reviewed alongside
> the SRS (`docs/SRS.md`), Vision (`docs/vision.md`), and Domain Model
> (`docs/domains.md`) for complete context.
