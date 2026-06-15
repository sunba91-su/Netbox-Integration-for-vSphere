from __future__ import annotations

from dataclasses import dataclass

DEFAULT_LOCK_PATH: str = "/tmp/nvs-sync.lock"
DEFAULT_POLL_INTERVAL_SECONDS: int = 1800
DEFAULT_NETBOX_PAGE_SIZE: int = 100
VAULT_TOKEN_TTL_SECONDS: int = 3600
VAULT_RENEW_THRESHOLD: float = 0.9

MANUFACTURER_VMWARE: str = "VMware Inc"
DEVICE_ROLE_ESXI: str = "ESXi Server"
CLUSTER_TYPE_VSPHERE: str = "vSphere Cluster"

STATUS_ACTIVE: str = "active"
STATUS_OFFLINE: str = "offline"
STATUS_DECOMMISSIONING: str = "decommissioning"

POWER_STATE_ON: str = "poweredOn"
POWER_STATE_OFF: str = "poweredOff"

CUSTOM_FIELD_PREFIX: str = "nvs_"

DEPENDENCY_ORDER: list[str] = [
    "site",
    "cluster_type",
    "manufacturer",
    "device_role",
    "cluster",
    "device",
    "vlan",
    "interface",
    "ip_address",
    "inventory_item",
]


@dataclass(frozen=True)
class NetBoxCustomFieldDef:
    name: str
    label: str
    content_types: list[str]
    data_type: str


CUSTOM_FIELD_DEFINITIONS: list[NetBoxCustomFieldDef] = [
    NetBoxCustomFieldDef(
        name="nvs_vsphere_mor",
        label="vSphere MOR",
        content_types=[
            "dcim.device",
            "dcim.cluster",
            "dcim.interface",
            "dcim.inventoryitem",
            "ipam.vlan",
        ],
        data_type="text",
    ),
    NetBoxCustomFieldDef(
        name="nvs_bios_uuid",
        label="BIOS UUID",
        content_types=["dcim.device"],
        data_type="text",
    ),
    NetBoxCustomFieldDef(
        name="nvs_esxi_version",
        label="ESXi Version",
        content_types=["dcim.device"],
        data_type="text",
    ),
    NetBoxCustomFieldDef(
        name="nvs_power_state",
        label="Power State",
        content_types=["dcim.device"],
        data_type="text",
    ),
    NetBoxCustomFieldDef(
        name="nvs_connection_state",
        label="Connection State",
        content_types=["dcim.device"],
        data_type="text",
    ),
    NetBoxCustomFieldDef(
        name="nvs_vcenter",
        label="vCenter Host",
        content_types=["dcim.device"],
        data_type="text",
    ),
    NetBoxCustomFieldDef(
        name="nvs_datacenter",
        label="vSphere Datacenter",
        content_types=["dcim.cluster"],
        data_type="text",
    ),
    NetBoxCustomFieldDef(
        name="nvs_mac_address",
        label="MAC Address",
        content_types=["dcim.interface"],
        data_type="text",
    ),
]
