from __future__ import annotations

from pydantic import BaseModel

from netbox_vsphere_sync.domain.model.config.network import (
    IpAddressRoleRule,
    VlanAllocationConfig,
)


class SyncConfig(BaseModel):
    prune: bool = False
    dry_run: bool = False
    vlan_allocation: VlanAllocationConfig = VlanAllocationConfig()
    ipaddress_role_mapping: list[IpAddressRoleRule] = []
