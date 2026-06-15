from dataclasses import dataclass, field


@dataclass(frozen=True)
class VSphereMOR:
    value: str
    type: str


@dataclass(frozen=True)
class HostHardware:
    cpu_model: str
    cpu_cores: int
    cpu_sockets: int
    memory_gb: float
    model: str
    serial: str


@dataclass(frozen=True)
class NetworkAddress:
    ip_address: str
    prefix_length: int
    subnet_mask: str | None = None
    gateway: str | None = None


@dataclass
class Site:
    name: str
    description: str = ""
    facility: str = ""
    physical_address: str = ""
    mor: VSphereMOR | None = None
    custom_fields: dict[str, str] = field(default_factory=lambda: dict[str, str]())


@dataclass
class Cluster:
    name: str
    site: str
    mor: VSphereMOR | None = None
    datacenter_name: str = ""
    ha_enabled: bool = False
    drs_enabled: bool = False
    custom_fields: dict[str, str] = field(default_factory=lambda: dict[str, str]())


@dataclass
class HostSystem:
    name: str
    site: str
    cluster: str | None = None
    mor: VSphereMOR | None = None
    hardware: HostHardware | None = None
    bios_uuid: str = ""
    esxi_version: str = ""
    power_state: str = ""
    connection_state: str = ""
    vcenter_host: str = ""
    maintenance_mode: bool = False
    custom_fields: dict[str, str] = field(default_factory=lambda: dict[str, str]())


@dataclass
class IpAddress:
    address: str
    prefix_length: int
    interface: str
    device: str
    role: str | None = None
    dns_name: str = ""
    description: str = ""
    mor: VSphereMOR | None = None
    custom_fields: dict[str, str] = field(default_factory=lambda: dict[str, str]())


@dataclass
class Interface:
    name: str
    device: str
    enabled: bool = True
    mtu: int = 1500
    mac_address: str = ""
    interface_type: str = "other"
    description: str = ""
    mor: VSphereMOR | None = None
    custom_fields: dict[str, str] = field(default_factory=lambda: dict[str, str]())
    ip_addresses: list[IpAddress] = field(default_factory=lambda: list[IpAddress]())


@dataclass
class PortGroup:
    name: str
    vlan_id: int | None = None
    switch_type: str = "standard"
    switch_name: str = ""
    mor: VSphereMOR | None = None
    hosts: list[str] = field(default_factory=lambda: list[str]())


@dataclass
class Vlan:
    site: str
    vid: int
    name: str = ""
    status: str = "active"
    description: str = ""
    mor: VSphereMOR | None = None
    custom_fields: dict[str, str] = field(default_factory=lambda: dict[str, str]())


@dataclass
class Datastore:
    name: str
    device: str
    capacity_bytes: int = 0
    free_bytes: int = 0
    datastore_type: str = "vmfs"
    role: str = "Storage"
    mor: VSphereMOR | None = None
    description: str = ""
    custom_fields: dict[str, str] = field(default_factory=lambda: dict[str, str]())
