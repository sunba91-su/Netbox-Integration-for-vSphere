from __future__ import annotations

from pydantic import BaseModel

from netbox_vsphere_sync.domain.model.config.bootstrap import BootstrapConfig
from netbox_vsphere_sync.domain.model.config.inventory import InventoryRoleConfig
from netbox_vsphere_sync.domain.model.config.netbox import NetBoxConfig
from netbox_vsphere_sync.domain.model.config.sync import SyncConfig
from netbox_vsphere_sync.domain.model.config.vault import VaultConfig
from netbox_vsphere_sync.domain.model.config.vcenter import VCenterConfig


class AppConfig(BaseModel):
    vcenter: VCenterConfig
    netbox: NetBoxConfig
    vault: VaultConfig = VaultConfig()
    sync: SyncConfig = SyncConfig()
    bootstrap: BootstrapConfig = BootstrapConfig()
    inventory_roles: InventoryRoleConfig = InventoryRoleConfig()
