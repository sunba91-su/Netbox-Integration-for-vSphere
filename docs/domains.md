# Domain Model: NetBox Integration for vSphere

> **Domain-Driven Design (DDD) approach for structuring the sync tool.**
>
> *This document defines bounded contexts, aggregates, entities, value objects,
> domain services, domain events, and repository ports. It is the blueprint
> for all source code organisation.*

---

## Table of Contents

1. [DDD Approach](#1-ddd-approach)
2. [Context Map](#2-context-map)
3. [Bounded Context: vSphere Inventory](#3-bounded-context-vsphere-inventory)
4. [Bounded Context: NetBox CMDB](#4-bounded-context-netbox-cmdb)
5. [Bounded Context: Sync Orchestration](#5-bounded-context-sync-orchestration)
6. [Bounded Context: Configuration & Secrets](#6-bounded-context-configuration--secrets)
7. [Bounded Context: Observability](#7-bounded-context-observability)
8. [Aggregate Design](#8-aggregate-design)
9. [Domain Events](#9-domain-events)
10. [Repository Ports](#10-repository-ports)
11. [Anti-Corruption Layers](#11-anti-corruption-layers)
12. [Revised Project Structure](#12-revised-project-structure)
13. [Implementation Guidelines](#13-implementation-guidelines)

---

## 1. DDD Approach

### 1.1 Why DDD for a CLI Sync Tool?

A CLI tool that synchronises two external systems (vSphere, NetBox) benefits
from DDD for three reasons:

1. **The sync logic is the core domain.** It contains non-trivial business
   rules (dependency ordering, natural key resolution, diff computation,
   idempotency). These rules are the hardest part of the system and deserve
   dedicated modelling.

2. **External systems change.** vSphere and NetBox APIs evolve. DDD's
   Anti-Corruption Layer (ACL) pattern isolates the core domain from API
   specifics, so an API change touches only one adapter.

3. **Testability.** Domain logic is tested without mocking APIs. Repository
   ports (Protocol-based) make the domain fully unit-testable.

### 1.2 Layers

```
┌─────────────────────────────────────────────────────────────┐
│  CLI Layer  (Click commands)                                │
├─────────────────────────────────────────────────────────────┤
│  Application Layer  (Sync Engine, Bootstrapper)             │
├─────────────────────────────────────────────────────────────┤
│  Domain Layer  (Aggregates, Entities, Value Objects, Events)│
├─────────────────────────────────────────────────────────────┤
│  Infrastructure Layer  (ACLs, Repository Impl, Vault, HTTP) │
└─────────────────────────────────────────────────────────────┘
```

**Dependency rule:** Upper layers import lower layers. Lower layers never
import upper layers. The Domain layer imports nothing from Infrastructure.

### 1.3 Modelling Conventions

| Concept | Python Type | Convention |
|---|---|---|
| **Value Object** | `@dataclass(frozen=True)` | Immutable, hashable, no identity. Equality by value. |
| **Entity** | `@dataclass` | Has identity (natural key or ID). Equality by key. |
| **Aggregate** | Entity (root) + contained entities | Transactional consistency boundary. |
| **Repository Port** | `typing.Protocol` | Structural subtyping. Implemented in Infrastructure. |
| **Domain Service** | Plain class or function | Business logic that does not belong to a single entity. |
| **Domain Event** | `@dataclass(frozen=True)` | Records something that happened. Collected by EventLog. |
| **ACL** | Plain class | Wraps external API, returns domain objects only. |

---

## 2. Context Map

### 2.1 Bounded Contexts

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Context Map                                  │
│                                                                      │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐      │
│  │  vSphere     │─────▶│    Sync      │◀─────│  NetBox      │      │
│  │  Inventory   │      │  Orchestration│      │  CMDB        │      │
│  │  (Read ACL)  │      │  (Core)       │      │  (Write ACL) │      │
│  └──────────────┘      └──────┬───────┘      └──────────────┘      │
│                               │                                      │
│                    ┌──────────┴──────────┐                          │
│                    │                     │                           │
│              ┌─────┴──────┐      ┌───────┴──────┐                  │
│              │ Config &   │      │ Observability│                  │
│              │ Secrets    │      │ (Reports)    │                  │
│              └────────────┘      └──────────────┘                  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 Relationships

| From | To | Relationship | Mechanism |
|---|---|---|---|
| vSphere Inventory | Sync Orchestration | **ACL (Provider)** | Sync imports domain objects from vSphere context; vSphere returns domain objects. |
| NetBox CMDB | Sync Orchestration | **ACL (Provider)** | Sync imports domain objects from NetBox context; NetBox returns domain objects. |
| Sync Orchestration | vSphere Inventory | **ACL (Consumer)** | Sync calls VSphereACL to collect inventory. |
| Sync Orchestration | NetBox CMDB | **ACL (Consumer)** | Sync calls NetBoxACL to read/write state. |
| Sync Orchestration | Config & Secrets | **Conformist** | Sync reads config values; config shapes the domain. |
| Sync Orchestration | Observability | **Publisher** | Sync emits DomainEvents; Observability subscribes (EventLog). |

### 2.3 Ubiquitous Language

| vSphere Term | NetBox Term | Domain Term | Meaning |
|---|---|---|---|
| Datacenter | Site | `Site` | Top-level location container |
| ClusterComputeResource | Cluster | `Cluster` | Group of ESXi hosts |
| HostSystem | Device | `ESXiHost` | Physical ESXi server |
| DistributedPortGroup | VLAN | `PortGroup` | Network segment |
| HostVirtualNic | Interface | `VMkernelInterface` | VMkernel network adapter |
| HostIPConfig | IPAddress | `HostIPAddress` | IP assigned to vmk |
| Hardware components | InventoryItem | `HardwareComponent` | CPU, DIMM, NIC, etc. |
| Datastore | InventoryItem | `Datastore` | Shared storage |
| — | Manufacturer | `Manufacturer` | Hardware vendor |
| — | DeviceType | `DeviceType` | Hardware model |
| — | DeviceRole | `DeviceRole` | Function (ESXi Server) |
| — | ClusterType | `ClusterType` | vSphere Cluster |
| ConnectionState | Status | `ConnectionStatus` | Host reachability |
| VLAN Tag | VLAN VID | `VLANTag` | 802.1Q tag |
| — | Slug | `Slug` | URL-safe identifier |

---

## 3. Bounded Context: vSphere Inventory

> **Purpose:** Read-only view of the vSphere environment. Translates PyVmomi
> API responses into domain objects. Never writes to vSphere.

### 3.1 Value Objects

```python
@dataclass(frozen=True)
class ManagedObjectRef:
    """vSphere managed object reference (e.g., 'host-123')."""
    type: str
    value: str

    def __post_init__(self):
        if not self.type or not self.value:
            raise ValueError("ManagedObjectRef requires non-empty type and value")

@dataclass(frozen=True)
class ESXiVersion:
    """ESXi version string (e.g., '8.0.3', '7.0.3')."""
    version: str
    build: str

    @property
    def major_minor(self) -> str:
        parts = self.version.split(".")
        return ".".join(parts[:2]) if len(parts) >= 2 else self.version

@dataclass(frozen=True)
class MemoryBytes:
    """Memory size in bytes with human-readable formatting."""
    bytes: int

    def __post_init__(self):
        if self.bytes < 0:
            raise ValueError(f"Memory cannot be negative: {self.bytes}")

    @property
    def human_readable(self) -> str:
        gb = self.bytes / (1024 ** 3)
        return f"{gb:.1f} GiB"

@dataclass(frozen=True)
class CpuInfo:
    """CPU topology extracted from HostSystem."""
    cores: int
    threads: int
    model: str
    vendor: str

    @property
    def hyperthreading(self) -> bool:
        return self.threads > self.cores

@dataclass(frozen=True)
class PowerState:
    """ESXi host power state."""
    state: str

    @property
    def is_on(self) -> bool:
        return self.state == "poweredOn"

@dataclass(frozen=True)
class ConnectionStatus:
    """vSphere connection state mapped to domain status."""
    state: str

    @property
    def is_healthy(self) -> bool:
        return self.state == "connected"

    @property
    def is_maintenance(self) -> bool:
        return self.state == "maintenance"

@dataclass(frozen=True)
class ClusterCapabilities:
    """vSphere cluster feature flags."""
    ha_enabled: bool
    drs_enabled: bool
    drs_automation_level: str

@dataclass(frozen=True)
class StorageCapacity:
    """Datastore capacity in bytes."""
    total_bytes: int
    free_bytes: int

    @property
    def used_bytes(self) -> int:
        return self.total_bytes - self.free_bytes

    @property
    def usage_percent(self) -> float:
        return (self.used_bytes / self.total_bytes * 100) if self.total_bytes > 0 else 0.0

@dataclass(frozen=True)
class VLANTag:
    """802.1Q VLAN tag. 0 = untagged."""
    vid: int

    def __post_init__(self):
        if not 0 <= self.vid <= 4094:
            raise ValueError(f"Invalid VLAN ID: {self.vid}")

    @property
    def is_untagged(self) -> bool:
        return self.vid == 0

@dataclass(frozen=True)
class IPNetmask:
    """IP address with subnet mask."""
    address: str
    prefix_length: int

    def __post_init__(self):
        if not 0 <= self.prefix_length <= 128:
            raise ValueError(f"Invalid prefix length: {self.prefix_length}")

    @property
    def cidr(self) -> str:
        return f"{self.address}/{self.prefix_length}"

    @property
    def is_link_local(self) -> bool:
        return self.address.startswith("169.254.") or self.address.startswith("fe80:")

@dataclass(frozen=True)
class DatastoreType:
    """Storage backend type."""
    type: str

@dataclass(frozen=True)
class HardwareComponentInfo:
    """Single hardware component extracted from HostSystem."""
    component_type: str
    name: str
    vendor: str
    model: str
    serial: str
    part_number: str

@dataclass(frozen=True)
class VMkernelServiceTag:
    """Service assigned to a VMkernel interface."""
    tag: str

    @property
    def is_management(self) -> bool:
        return self.tag == "management"

    @property
    def is_anycast(self) -> bool:
        return self.tag in ("vmotion", "vsan", "faultToleranceLogging", "vSphereReplication")
```

### 3.2 Entities

```python
@dataclass
class DatacenterInfo:
    """vSphere Datacenter (read-only snapshot)."""
    name: str
    path: str
    mor: ManagedObjectRef

@dataclass
class ClusterInfo:
    """vSphere ClusterComputeResource (read-only snapshot)."""
    name: str
    datacenter_name: str
    capabilities: ClusterCapabilities
    total_cpu_mhz: int
    total_memory_bytes: int
    mor: ManagedObjectRef

@dataclass
class HostInfo:
    """vSphere HostSystem (read-only snapshot)."""
    name: str
    datacenter_name: str
    cluster_name: str
    version: ESXiVersion
    connection_status: ConnectionStatus
    power_state: PowerState
    cpu: CpuInfo
    memory: MemoryBytes
    mor: ManagedObjectRef
    interfaces: list["VMkernelNicInfo"] = field(default_factory=list)
    hardware: list[HardwareComponentInfo] = field(default_factory=list)
    datastores: list["DatastoreInfo"] = field(default_factory=list)

@dataclass
class PortGroupInfo:
    """vSphere Port Group (distributed or standard)."""
    name: str
    datacenter_name: str
    vlan_tag: VLANTag
    portgroup_type: str
    mor: ManagedObjectRef

@dataclass
class VMkernelNicInfo:
    """vSphere VMkernel NIC."""
    device_name: str
    mac_address: str
    mtu: int
    portgroup_name: str
    enabled: bool
    service_tags: list[VMkernelServiceTag] = field(default_factory=list)
    ip_addresses: list[IPNetmask] = field(default_factory=list)

@dataclass
class DatastoreInfo:
    """vSphere Datastore (read-only snapshot)."""
    name: str
    datacenter_name: str
    datastore_type: DatastoreType
    capacity: StorageCapacity
    multiple_host_access: bool
    mounted_hosts: list[str]
    mor: ManagedObjectRef
```

### 3.3 Repository Port

```python
class VSphereInventoryRepository(Protocol):
    """Port: read-only access to vSphere inventory."""

    def find_datacenters(self) -> list[DatacenterInfo]: ...
    def find_clusters(self, datacenter: str) -> list[ClusterInfo]: ...
    def find_hosts(self, datacenter: str) -> list[HostInfo]: ...
    def find_port_groups(self, datacenter: str) -> list[PortGroupInfo]: ...
    def find_datastores(self, datacenter: str) -> list[DatastoreInfo]: ...
    def is_reachable(self) -> bool: ...
```

### 3.4 ACL (Anti-Corruption Layer)

```python
class VSphereACL:
    """Translates PyVmomi API responses into domain objects."""

    def __init__(self, host: str, user: str, password: str, verify_ssl: bool = True):
        self._host = host
        self._user = user
        self._password = password
        self._verify_ssl = verify_ssl
        self._si: Optional[ServiceInstance] = None

    def connect(self) -> None:
        self._si = SmartConnect(
            host=self._host,
            user=self._user,
            pwd=self._password,
            disableSslCertValidation=not self._verify_ssl,
        )

    def is_reachable(self) -> bool:
        try:
            return self._si is not None and self._si.RetrieveContent() is not None
        except Exception:
            return False

    def find_hosts(self, datacenter: str) -> list[HostInfo]:
        view = self._create_view([HostSystem], datacenter)
        props = self._retrieve_properties(view, [
            "name", "config", "hardware", "runtime", "network"
        ])
        return [self._to_host_domain(h) for h in props]

    def _to_host_domain(self, raw) -> HostInfo:
        return HostInfo(
            name=raw.name,
            mor=ManagedObjectRef(type="HostSystem", value=str(raw._moId)),
        )
```

---

## 4. Bounded Context: NetBox CMDB

> **Purpose:** Read and write to NetBox via REST API. Translates between domain
> objects and NetBox API payloads.

### 4.1 Value Objects

```python
@dataclass(frozen=True)
class Slug:
    """URL-safe identifier derived from a name."""
    value: str

    def __post_init__(self):
        import re
        if not re.match(r"^[a-z0-9]([a-z0-9\-]*[a-z0-9])?$", self.value):
            raise ValueError(f"Invalid slug: {self.value}")

    @classmethod
    def from_name(cls, name: str) -> "Slug":
        slug = name.lower().replace(" ", "-").replace("_", "-")
        slug = re.sub(r"[^a-z0-9\-]", "", slug)
        slug = re.sub(r"-+", "-", slug).strip("-")
        return cls(value=slug)

@dataclass(frozen=True)
class DeviceRoleName:
    name: str

@dataclass(frozen=True)
class ManufacturerName:
    name: str

@dataclass(frozen=True)
class ClusterTypeName:
    name: str

@dataclass(frozen=True)
class InventoryItemRoleName:
    name: str

@dataclass(frozen=True)
class NetBoxStatus:
    """NetBox object status."""
    status: str

    @property
    def is_active(self) -> bool:
        return self.status == "active"

@dataclass(frozen=True)
class CustomField:
    """NetBox custom field value."""
    key: str
    value: Any

@dataclass(frozen=True)
class NaturalKey:
    """Composite key used to match domain objects to NetBox records."""
    fields: tuple[tuple[str, Any], ...]

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "NaturalKey":
        return cls(fields=tuple(sorted(d.items())))

    def matches(self, other: "NaturalKey") -> bool:
        return self.fields == other.fields
```

### 4.2 Entities

```python
@dataclass
class Site:
    """NetBox Site, mapped from vSphere Datacenter."""
    name: str
    slug: Slug
    description: str = ""
    netbox_id: Optional[int] = None
    vcenter_mor: Optional[str] = None
    custom_fields: list[CustomField] = field(default_factory=list)

    def natural_key(self) -> NaturalKey:
        return NaturalKey.from_dict({"name": self.name})

@dataclass
class Cluster:
    """NetBox Cluster, mapped from vSphere ClusterComputeResource."""
    name: str
    site_name: str
    cluster_type: str = "vSphere Cluster"
    group: Optional[str] = None
    netbox_id: Optional[int] = None
    vcenter_mor: Optional[str] = None
    ha_enabled: Optional[bool] = None
    drs_enabled: Optional[bool] = None
    drs_level: Optional[str] = None
    cpu_mhz: Optional[int] = None
    memory_mb: Optional[int] = None

    def natural_key(self) -> NaturalKey:
        return NaturalKey.from_dict({"name": self.name, "site_name": self.site_name})

@dataclass
class Device:
    """NetBox Device, mapped from vSphere HostSystem."""
    name: str
    site_name: str
    cluster_name: str
    device_type_model: str
    manufacturer_name: str
    role: str = "ESXi Server"
    status: NetBoxStatus = NetBoxStatus(status="active")
    netbox_id: Optional[int] = None
    vcenter_mor: Optional[str] = None
    esxi_version: Optional[str] = None
    esxi_build: Optional[str] = None
    power_state: Optional[str] = None
    cpu_cores: Optional[int] = None
    cpu_threads: Optional[int] = None
    cpu_model: Optional[str] = None
    memory_bytes: Optional[int] = None

    def natural_key(self) -> NaturalKey:
        return NaturalKey.from_dict({"name": self.name})

@dataclass
class VLAN:
    """NetBox VLAN, mapped from vSphere Port Group."""
    vid: int
    name: str
    site_name: str
    description: str = ""
    netbox_id: Optional[int] = None
    vcenter_mor: Optional[str] = None

    def natural_key(self) -> NaturalKey:
        return NaturalKey.from_dict({"vid": self.vid, "site_name": self.site_name})

@dataclass
class Interface:
    """NetBox Interface, mapped from vSphere VMkernelNic."""
    device_name: str
    name: str
    type: str = "virtual"
    enabled: bool = True
    mtu: Optional[int] = None
    mac_address: Optional[str] = None
    description: str = ""
    netbox_id: Optional[int] = None

    def natural_key(self) -> NaturalKey:
        return NaturalKey.from_dict({"device_name": self.device_name, "name": self.name})

@dataclass
class IPAddress:
    """NetBox IPAddress, mapped from vSphere VMkernel IP."""
    address: str
    interface_name: str
    device_name: str
    status: str = "active"
    role: Optional[str] = None
    dns_name: Optional[str] = None
    description: str = ""
    netbox_id: Optional[int] = None

    def natural_key(self) -> NaturalKey:
        return NaturalKey.from_dict({"address": self.address})

@dataclass
class InventoryItem:
    """NetBox InventoryItem, mapped from vSphere hardware or datastore."""
    device_name: str
    name: str
    role: str
    manufacturer_name: Optional[str] = None
    part_id: Optional[str] = None
    serial: Optional[str] = None
    description: str = ""
    discovered: bool = True
    netbox_id: Optional[int] = None

    def natural_key(self) -> NaturalKey:
        return NaturalKey.from_dict({
            "device_name": self.device_name,
            "name": self.name,
            "role": self.role,
        })
```

### 4.3 Repository Ports

```python
class SiteRepository(Protocol):
    def find_all(self) -> list[Site]: ...
    def find_by_name(self, name: str) -> Optional[Site]: ...
    def upsert(self, site: Site) -> Site: ...

class ClusterRepository(Protocol):
    def find_all(self, site_name: Optional[str] = None) -> list[Cluster]: ...
    def find_by_natural_key(self, key: NaturalKey) -> Optional[Cluster]: ...
    def upsert(self, cluster: Cluster) -> Cluster: ...

class DeviceRepository(Protocol):
    def find_all(self, site_name: Optional[str] = None) -> list[Device]: ...
    def find_by_name(self, name: str) -> Optional[Device]: ...
    def upsert(self, device: Device) -> Device: ...

class VLANRepository(Protocol):
    def find_all(self, site_name: Optional[str] = None) -> list[VLAN]: ...
    def find_by_natural_key(self, key: NaturalKey) -> Optional[VLAN]: ...
    def upsert(self, vlan: VLAN) -> VLAN: ...

class InterfaceRepository(Protocol):
    def find_all(self, device_name: str) -> list[Interface]: ...
    def find_by_natural_key(self, key: NaturalKey) -> Optional[Interface]: ...
    def upsert(self, interface: Interface) -> Interface: ...

class IPAddressRepository(Protocol):
    def find_all(self, interface_name: Optional[str] = None) -> list[IPAddress]: ...
    def find_by_natural_key(self, key: NaturalKey) -> Optional[IPAddress]: ...
    def upsert(self, ip: IPAddress) -> IPAddress: ...

class InventoryItemRepository(Protocol):
    def find_all(self, device_name: Optional[str] = None) -> list[InventoryItem]: ...
    def find_by_natural_key(self, key: NaturalKey) -> Optional[InventoryItem]: ...
    def upsert(self, item: InventoryItem) -> InventoryItem: ...

class ManufacturerRepository(Protocol):
    def find_or_create(self, name: str) -> int: ...

class DeviceTypeRepository(Protocol):
    def find_or_create(self, model: str, manufacturer_id: int) -> int: ...

class DeviceRoleRepository(Protocol):
    def find_or_create(self, name: str) -> int: ...

class ClusterTypeRepository(Protocol):
    def find_or_create(self, name: str) -> int: ...
```

### 4.4 ACL

```python
class NetBoxACL:
    """Translates domain objects to/from NetBox API payloads."""

    def __init__(self, url: str, token: str, timeout: int = 30):
        self._api = pynetbox.api(url, token=token)
        self._timeout = timeout

    @property
    def sites(self) -> "NetBoxSiteRepository": ...
    @property
    def clusters(self) -> "NetBoxClusterRepository": ...
    @property
    def devices(self) -> "NetBoxDeviceRepository": ...
    @property
    def vlans(self) -> "NetBoxVlanRepository": ...
    @property
    def interfaces(self) -> "NetBoxInterfaceRepository": ...
    @property
    def ip_addresses(self) -> "NetBoxIPAddressRepository": ...
    @property
    def inventory_items(self) -> "NetBoxInventoryItemRepository": ...
    @property
    def manufacturers(self) -> "NetBoxManufacturerRepository": ...
    @property
    def device_types(self) -> "NetBoxDeviceTypeRepository": ...
    @property
    def device_roles(self) -> "NetBoxDeviceRoleRepository": ...
    @property
    def cluster_types(self) -> "NetBoxClusterTypeRepository": ...

    def is_reachable(self) -> bool:
        try:
            self._api.status()
            return True
        except Exception:
            return False

    def bootstrap_metadata(self) -> None:
        self.manufacturers.find_or_create("VMware Inc")
        self.device_roles.find_or_create("ESXi Server")
        self.cluster_types.find_or_create("vSphere Cluster")
```

---

## 5. Bounded Context: Sync Orchestration

> **Purpose:** The core domain. Orchestrates the sync pipeline, computes
> diffs, applies changes in dependency order, and emits domain events.

### 5.1 Value Objects

```python
@dataclass(frozen=True)
class SyncMode:
    """Sync execution mode."""
    dry_run: bool = False
    prune: bool = False

    @classmethod
    def live(cls) -> "SyncMode":
        return cls(dry_run=False, prune=False)

    @classmethod
    def preview(cls) -> "SyncMode":
        return cls(dry_run=True, prune=False)

@dataclass(frozen=True)
class BatchSize:
    """Number of objects per NetBox bulk API call."""
    size: int = 100

    def __post_init__(self):
        if not 1 <= self.size <= 1000:
            raise ValueError(f"Batch size must be 1-1000, got {self.size}")

@dataclass(frozen=True)
class EntityDiff:
    """Diff for a single entity type."""
    entity_type: str
    creates: int = 0
    updates: int = 0
    unchanged: int = 0
    errors: int = 0
    error_details: tuple[str, ...] = ()

@dataclass(frozen=True)
class SyncDuration:
    """Elapsed time for a sync run."""
    seconds: float

    @property
    def human_readable(self) -> str:
        if self.seconds < 60:
            return f"{self.seconds:.1f}s"
        minutes = int(self.seconds // 60)
        secs = self.seconds % 60
        return f"{minutes}m {secs:.0f}s"

@dataclass(frozen=True)
class DependencyOrder:
    """Immutable sequence of entity types to sync."""
    order: tuple[str, ...] = (
        "site",
        "cluster",
        "device",
        "vlan",
        "interface",
        "ip_address",
        "inventory_item",
    )
```

### 5.2 Entities

```python
@dataclass
class SyncRun:
    """Aggregate root for a single sync execution."""
    run_id: str
    started_at: datetime
    mode: SyncMode
    results: list[EntityDiff] = field(default_factory=list)
    completed_at: Optional[datetime] = None
    failed: bool = False
    error_message: Optional[str] = None

    def add_result(self, result: EntityDiff) -> None:
        self.results.append(result)

    def complete(self) -> None:
        self.completed_at = datetime.now(timezone.utc)

    def fail(self, message: str) -> None:
        self.failed = True
        self.error_message = message
        self.complete()

    @property
    def duration(self) -> SyncDuration:
        if self.completed_at is None:
            return SyncDuration(seconds=0)
        return SyncDuration(
            seconds=(self.completed_at - self.started_at).total_seconds()
        )

    @property
    def total_created(self) -> int:
        return sum(r.creates for r in self.results)

    @property
    def total_updated(self) -> int:
        return sum(r.updates for r in self.results)

    @property
    def total_errors(self) -> int:
        return sum(r.errors for r in self.results)

    @property
    def summary(self) -> dict[str, int]:
        return {
            "created": self.total_created,
            "updated": self.total_updated,
            "errors": self.total_errors,
        }
```

### 5.3 Domain Services

```python
class DiffEngine:
    """Computes the diff between vSphere inventory and NetBox state."""

    def compute_site_diff(
        self,
        desired: list[DatacenterInfo],
        existing: list[Site],
    ) -> list[tuple[str, Optional[Site], Optional[DatacenterInfo]]]:
        ...

    def compute_device_diff(
        self,
        desired: list[HostInfo],
        existing: list[Device],
    ) -> list[tuple[str, Optional[Device], Optional[HostInfo]]]:
        ...

    def _should_update(self, existing, desired) -> bool:
        ...


class DependencyResolver:
    """Ensures entities are synced in topological order."""

    def __init__(self, order: DependencyOrder):
        self._order = order

    def resolve(
        self,
        vsphere_inventory: dict[str, list],
        netbox_state: dict[str, list],
    ) -> list[tuple[str, list, list]]:
        for entity_type in self._order.order:
            desired = vsphere_inventory.get(entity_type, [])
            existing = netbox_state.get(entity_type, [])
            if desired:
                yield (entity_type, desired, existing)


class SyncEngine:
    """Orchestrates the full sync pipeline."""

    def __init__(
        self,
        vsphere: VSphereInventoryRepository,
        netbox: NetBoxACL,
        mode: SyncMode,
        batch_size: BatchSize,
        event_log: "EventLog",
    ):
        self._vsphere = vsphere
        self._netbox = netbox
        self._mode = mode
        self._batch_size = batch_size
        self._event_log = event_log
        self._diff_engine = DiffEngine()
        self._resolver = DependencyResolver(DependencyOrder())

    def run(self) -> SyncRun:
        sync_run = SyncRun(
            run_id=str(uuid4()),
            started_at=datetime.now(timezone.utc),
            mode=self._mode,
        )
        try:
            inventory = self._collect_vsphere()
            netbox_state = self._fetch_netbox()
            if not self._mode.dry_run:
                self._netbox.bootstrap_metadata()
            for entity_type, desired, existing in self._resolver.resolve(
                inventory, netbox_state
            ):
                result = self._sync_entity_type(entity_type, desired, existing)
                sync_run.add_result(result)
            sync_run.complete()
        except Exception as e:
            sync_run.fail(str(e))
        return sync_run

    def _collect_vsphere(self) -> dict[str, list]: ...
    def _fetch_netbox(self) -> dict[str, list]: ...
    def _sync_entity_type(self, entity_type, desired, existing) -> EntityDiff: ...
```

---

## 6. Bounded Context: Configuration & Secrets

> **Purpose:** Load configuration from YAML, environment variables, and
> HashiCorp Vault. Resolve credentials with precedence rules.

### 6.1 Value Objects

```python
@dataclass(frozen=True)
class VSphereConfig:
    host: str
    username: str
    password: str
    verify_ssl: bool = True

@dataclass(frozen=True)
class NetBoxConfig:
    url: str
    token: str
    verify_ssl: bool = True
    timeout: int = 30

@dataclass(frozen=True)
class VaultAuthMethod:
    method: str

    def __post_init__(self):
        if self.method not in ("token", "approle", "kubernetes"):
            raise ValueError(f"Invalid auth method: {self.method}")

@dataclass(frozen=True)
class VaultConfig:
    enabled: bool
    addr: str = ""
    verify_ssl: bool = True
    namespace: str = ""
    auth_method: VaultAuthMethod = VaultAuthMethod(method="token")
    role_id: str = ""
    secret_id: str = ""

@dataclass(frozen=True)
class SyncConfig:
    entities: tuple[str, ...] = ("host", "cluster", "network", "interface", "inventory", "storage")
    dry_run: bool = False
    prune: bool = False
    batch_size: int = 100
    timeout: int = 60

@dataclass(frozen=True)
class VLANAllocationConfig:
    strategy: str = "from_portgroup"
    reserved_range_start: int = 4000
    reserved_range_end: int = 4094

@dataclass(frozen=True)
class RoleMappingRule:
    prefix: str
    role: str

@dataclass(frozen=True)
class IPAddressRoleConfig:
    rules: tuple[RoleMappingRule, ...] = ()
    default_role: Optional[str] = None
```

### 6.2 Domain Service

```python
class ConfigLoader:
    """Loads and merges configuration from multiple sources."""
    def load(
        self,
        config_path: Optional[str] = None,
        cli_overrides: Optional[dict] = None,
    ) -> "AppConfig": ...

class SecretResolver:
    """Resolves credentials from Vault or environment."""
    def __init__(self, vault_config: VaultConfig): ...
    def resolve(self) -> dict[str, str]: ...
```

### 6.3 Aggregate (Configuration)

```python
@dataclass
class AppConfig:
    """Root configuration aggregate. Combines all config sources."""
    vsphere: VSphereConfig
    netbox: NetBoxConfig
    vault: VaultConfig
    sync: SyncConfig
    vlan_allocation: VLANAllocationConfig
    ipaddress_role: IPAddressRoleConfig

    @classmethod
    def load(cls, config_path: Optional[str] = None, **overrides) -> "AppConfig": ...
```

---

## 7. Bounded Context: Observability

> **Purpose:** Generate human-readable reports, structured logs, and metrics.

### 7.1 Value Objects

```python
@dataclass(frozen=True)
class ReportRow:
    """Single row in the sync report table."""
    entity: str
    created: int
    updated: int
    deactivated: int
    errors: int

@dataclass(frozen=True)
class SyncReport:
    """Complete sync report output."""
    timestamp: datetime
    vcenter_host: str
    netbox_url: str
    datacenter_count: int
    rows: tuple[ReportRow, ...]
    duration: SyncDuration
    exit_code: int

@dataclass(frozen=True)
class LogContext:
    """Structured logging context."""
    run_id: str
    entity_type: str
    entity_name: str
    action: str
```

### 7.2 Domain Service

```python
class ReportGenerator:
    """Generates the sync report from SyncRun data."""
    def generate(self, sync_run: SyncRun, config: AppConfig) -> SyncReport: ...
    def render_console(self, report: SyncReport) -> str: ...
    def render_json(self, report: SyncReport) -> dict: ...

class EventLog:
    """Collects domain events during a sync run."""
    def __init__(self) -> None:
        self._events: list[DomainEvent] = []

    def record(self, event: DomainEvent) -> None: ...
    @property
    def events(self) -> list[DomainEvent]: ...
```

---

## 8. Aggregate Design

### 8.1 Design Rationale

Each NetBox entity type is a **separate aggregate** because:

1. **API isolation:** Each entity is created/updated via its own API endpoint.
   There is no cross-entity transaction in NetBox's REST API.
2. **Dependency order:** The sync engine enforces order externally (not via
   aggregate invariants).
3. **Natural key consistency:** Each aggregate's natural key is self-contained.

### 8.2 Aggregate Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    NetBox CMDB Context                       │
│                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ Site        │  │ Cluster     │  │ Device              │ │
│  │ (Aggregate  │  │ (Aggregate  │  │ (Aggregate Root)    │ │
│  │  Root)      │  │  Root)      │  │                     │ │
│  │             │  │             │  │ ┌─────────────────┐ │ │
│  │ name        │  │ name        │  │ │ Interface       │ │ │
│  │ slug        │  │ site_name   │  │ │ (Entity)        │ │ │
│  │ description │  │ type        │  │ ├─────────────────┤ │ │
│  │ netbox_id   │  │ netbox_id   │  │ │ InventoryItem   │ │ │
│  │             │  │             │  │ │ (Entity)        │ │ │
│  └─────────────┘  └─────────────┘  │ └─────────────────┘ │ │
│                                     │                     │ │
│  ┌─────────────┐  ┌─────────────┐  │ name               │ │
│  │ VLAN        │  │ IPAddress   │  │ site_name          │ │
│  │ (Aggregate  │  │ (Aggregate  │  │ cluster_name       │ │
│  │  Root)      │  │  Root)      │  │ device_type_model  │ │
│  │             │  │             │  │ manufacturer_name  │ │
│  │ vid         │  │ address     │  │ status             │ │
│  │ name        │  │ interface   │  │ netbox_id          │ │
│  │ site_name   │  │ device_name │  └─────────────────────┘ │
│  │ netbox_id   │  │ role        │                           │
│  └─────────────┘  │ netbox_id   │                           │
│                   └─────────────┘                           │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 8.3 Aggregate Details

| Aggregate Root | Natural Key | Contained Entities | Invariants |
|---|---|---|---|
| **Site** | `name` | None | Slug must be unique. Name must not collide with unmanaged sites. |
| **Cluster** | `name` + `site_name` | None | Must reference existing Site. Type must be "vSphere Cluster". |
| **Device** | `name` (FQDN) | Interface, InventoryItem | Must reference existing Site + Cluster. Status from connection state. |
| **VLAN** | `vid` + `site_name` | None | VID must be 0–4094. Must reference existing Site. |
| **Interface** | `device_name` + `name` | None | Must reference existing Device. Name matches vmk pattern. |
| **IPAddress** | `address` (CIDR) | None | Must reference existing Interface. Status is "active". Role from decision matrix. |
| **InventoryItem** | `device_name` + `name` + `role` | None | Must reference existing Device. Role from allowed list. |

---

## 9. Domain Events

### 9.1 Event Hierarchy

```python
@dataclass(frozen=True)
class DomainEvent:
    """Base class for all domain events."""
    occurred_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

@dataclass(frozen=True)
class SyncStarted(DomainEvent):
    run_id: str
    mode: str

@dataclass(frozen=True)
class SyncCompleted(DomainEvent):
    run_id: str
    created: int
    updated: int
    unchanged: int
    errors: int
    duration_seconds: float

@dataclass(frozen=True)
class SyncFailed(DomainEvent):
    run_id: str
    error: str

@dataclass(frozen=True)
class EntityEvent(DomainEvent):
    """Base for entity-level events."""
    entity_type: str
    entity_name: str

@dataclass(frozen=True)
class EntityCreated(EntityEvent):
    netbox_id: Optional[int] = None

@dataclass(frozen=True)
class EntityUpdated(EntityEvent):
    changed_fields: frozenset[str] = frozenset()

@dataclass(frozen=True)
class EntitySkipped(EntityEvent):
    reason: str = "unchanged"

@dataclass(frozen=True)
class EntityFailed(EntityEvent):
    error: str = ""

@dataclass(frozen=True)
class MetadataBootstrapped(DomainEvent):
    object_type: str
    object_name: str

@dataclass(frozen=True)
class MetadataExists(DomainEvent):
    object_type: str
    object_name: str
```

---

## 10. Repository Ports

### 10.1 Port Definitions (Domain Layer)

All ports are defined as `typing.Protocol` in the domain layer.

```python
class Repository(Protocol):
    """Base protocol for all repositories."""
    def find_all(self, **filters) -> list: ...
    def find_by_natural_key(self, key: NaturalKey) -> Optional: ...
    def upsert(self, entity) -> Optional: ...
    def delete(self, entity) -> None: ...

class SiteRepository(Repository): ...
class ClusterRepository(Repository): ...
class DeviceRepository(Repository): ...
class VLANRepository(Repository): ...
class InterfaceRepository(Repository): ...
class IPAddressRepository(Repository): ...
class InventoryItemRepository(Repository): ...
```

---

## 11. Anti-Corruption Layers

### 11.1 ACL Boundaries

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   PyVmomi    │────▶│  VSphereACL  │────▶│   Domain     │
│   API        │     │  (translate) │     │   Objects    │
└──────────────┘     └──────────────┘     └──────────────┘

┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   pynetbox   │◀────│  NetBoxACL   │◀────│   Domain     │
│   API        │     │  (translate) │     │   Objects    │
└──────────────┘     └──────────────┘     └──────────────┘

┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   hvac       │────▶│  VaultACL    │────▶│   Secrets    │
│   API        │     │  (translate) │     │   (dict)     │
└──────────────┘     └──────────────┘     └──────────────┘
```

### 11.2 ACL Responsibilities

| ACL | Input | Output | Error Handling |
|---|---|---|---|
| **VSphereACL** | PyVmomi `HostSystem`, `Datacenter`, etc. | `HostInfo`, `DatacenterInfo`, etc. | Wraps `pyVmomi` exceptions into `VSphereConnectionError` |
| **NetBoxACL** | Domain objects (Site, Device, etc.) | NetBox API payloads | Wraps `pynetbox` exceptions into `NetBoxAPIError` |
| **VaultACL** | Vault config | `dict[str, str]` (secrets) | Wraps `hvac` exceptions into `VaultAuthError` |

### 11.3 ACL Error Types

```python
class SyncError(Exception): ...
class VSphereConnectionError(SyncError): ...
class NetBoxAPIError(SyncError): ...
class VaultAuthError(SyncError): ...
class ConfigurationError(SyncError): ...
```

---

## 12. Revised Project Structure

```
netbox-vsphere-sync/
├── pyproject.toml
├── Makefile
├── README.md
├── LICENSE
├── .gitignore
├── ruff.toml
├── pyrightconfig.json
├── .pre-commit-config.yaml
│
├── src/
│   └── netbox_vsphere_sync/
│       ├── __init__.py
│       ├── domain/
│       │   ├── __init__.py
│       │   ├── model/
│       │   │   ├── __init__.py
│       │   │   ├── natural_key.py
│       │   │   ├── site.py
│       │   │   ├── cluster.py
│       │   │   ├── host.py
│       │   │   ├── network.py
│       │   │   ├── inventory.py
│       │   │   ├── vsphere/
│       │   │   │   ├── __init__.py
│       │   │   │   ├── datacenter.py
│       │   │   │   ├── cluster.py
│       │   │   │   ├── host.py
│       │   │   │   ├── portgroup.py
│       │   │   │   ├── vmknic.py
│       │   │   │   ├── datastore.py
│       │   │   │   └── hardware.py
│       │   │   └── config/
│       │   │       ├── __init__.py
│       │   │       ├── vsphere.py
│       │   │       ├── netbox.py
│       │   │       ├── vault.py
│       │   │       ├── sync.py
│       │   │       └── vlan.py
│       │   ├── events.py
│       │   ├── ports.py
│       │   ├── exceptions.py
│       │   └── constants.py
│       │
│       ├── application/
│       │   ├── __init__.py
│       │   ├── sync_engine.py
│       │   ├── diff_engine.py
│       │   ├── dependency_resolver.py
│       │   ├── bootstrapper.py
│       │   └── event_log.py
│       │
│       ├── infrastructure/
│       │   ├── __init__.py
│       │   ├── netbox/
│       │   │   ├── __init__.py
│       │   │   ├── acl.py
│       │   │   ├── client.py
│       │   │   └── repositories/
│       │   │       ├── __init__.py
│       │   │       ├── site.py
│       │   │       ├── cluster.py
│       │   │       ├── device.py
│       │   │       ├── vlan.py
│       │   │       ├── interface.py
│       │   │       ├── ip_address.py
│       │   │       └── inventory_item.py
│       │   ├── vsphere/
│       │   │   ├── __init__.py
│       │   │   ├── acl.py
│       │   │   └── collector.py
│       │   ├── vault/
│       │   │   ├── __init__.py
│       │   │   ├── acl.py
│       │   │   └── client.py
│       │   └── config/
│       │       ├── __init__.py
│       │       ├── loader.py
│       │       └── secret_resolver.py
│       │
│       ├── cli/
│       │   ├── __init__.py
│       │   ├── __main__.py
│       │   ├── app.py
│       │   └── commands/
│       │       ├── __init__.py
│       │       ├── sync.py
│       │       ├── check.py
│       │       ├── bootstrap.py
│       │       └── config.py
│       │
│       └── report/
│           ├── __init__.py
│           ├── generator.py
│           └── console.py
│
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── domain/
    │   ├── __init__.py
    │   ├── test_events.py
    │   ├── test_natural_key.py
    │   └── model/
    │       ├── __init__.py
    │       ├── test_site.py
    │       ├── test_cluster.py
    │       ├── test_host.py
    │       ├── test_network.py
    │       └── test_inventory.py
    ├── application/
    │   ├── __init__.py
    │   ├── test_sync_engine.py
    │   ├── test_diff_engine.py
    │   └── test_dependency_resolver.py
    ├── infrastructure/
    │   ├── __init__.py
    │   ├── netbox/
    │   │   ├── __init__.py
    │   │   └── test_repositories.py
    │   └── vsphere/
    │       ├── __init__.py
    │       └── test_collector.py
    └── cli/
        ├── __init__.py
        └── test_commands.py
```

---

## 13. Implementation Guidelines

### 13.1 Dependency Injection

The CLI layer wires everything together:

```python
@click.command()
@click.option("--dry-run", is_flag=True)
@click.option("--config", "config_path")
def sync(dry_run: bool, config_path: str):
    config = ConfigLoader().load(config_path, dry_run=dry_run)
    secrets = SecretResolver(config.vault).resolve()

    vsphere_acl = VSphereACL(
        host=config.vsphere.host,
        user=config.vsphere.username,
        password=config.vsphere.password,
    )
    netbox_acl = NetBoxACL(
        url=config.netbox.url,
        token=config.netbox.token,
    )

    site_repo = NetBoxSiteRepository(netbox_acl.api)
    device_repo = NetBoxDeviceRepository(netbox_acl.api)

    event_log = EventLog()

    engine = SyncEngine(
        vsphere=vsphere_acl,
        netbox=netbox_acl,
        mode=SyncMode.live() if not dry_run else SyncMode.preview(),
        batch_size=BatchSize(config.sync.batch_size),
        event_log=event_log,
    )
    sync_run = engine.run()

    report = ReportGenerator().generate(sync_run, config)
    click.echo(ReportGenerator().render_console(report))
```

### 13.2 Testing Strategy

| Layer | Test Type | Mocking |
|---|---|---|
| **Domain** | Unit tests | No mocks needed — pure value objects and entities |
| **Application** | Unit tests | Mock repository ports (Protocol stubs) |
| **Infrastructure** | Integration tests | Mock external APIs (vcrpy for NetBox, pytest fixtures for vSphere) |
| **CLI** | Acceptance tests | Full mock stack via Click's `CliRunner` |

### 13.3 Key Invariants to Enforce

| Invariant | Enforcement |
|---|---|
| Natural key uniqueness | Repository `find_by_natural_key` returns Optional; upsert checks before write |
| Dependency order | DependencyResolver yields types in topological order |
| No deletions by default | Prune mode must be explicitly enabled |
| Idempotent sync | DiffEngine compares all updatable fields; skips if unchanged |
| Vault token refresh | VaultClient checks TTL at 90% expiry before each read |

---

> **Design statement.** *The domain model isolates sync business rules from
> external API specifics. Each bounded context has a clear responsibility:
> vSphere reads, NetBox writes, Sync orchestrates, Config resolves secrets,
> Observability reports. Repository ports (Protocol-based) make the domain
> fully testable without API mocking. Anti-corruption layers ensure that API
> changes touch only one adapter, never the core domain.*
