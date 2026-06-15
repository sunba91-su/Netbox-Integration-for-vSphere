from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_core.core_schema import ValidationInfo


class VCenterConfig(BaseModel):
    host: str = ""
    username: str = Field(default="", validation_alias="NVS_VCENTER_USERNAME")
    password: str = Field(default="", validation_alias="NVS_VCENTER_PASSWORD")
    verify_ssl: bool = True

    @model_validator(mode="after")
    def check_required(self) -> VCenterConfig:
        if not self.host:
            raise ValueError("vcenter.host is required")
        if not self.username:
            raise ValueError("vcenter.username is required")
        if not self.password:
            raise ValueError("vcenter.password is required")
        return self


class NetBoxConfig(BaseModel):
    url: str = ""
    token: str = Field(default="", validation_alias="NVS_NETBOX_TOKEN")
    verify_ssl: bool = True
    page_size: int = 100

    @model_validator(mode="after")
    def check_required(self) -> NetBoxConfig:
        if not self.url:
            raise ValueError("netbox.url is required")
        if not self.token:
            raise ValueError("netbox.token is required")
        return self


class VaultAuthConfig(BaseModel):
    method: Literal["token", "approle", "kubernetes"] = "token"
    mount_point: str = "secret"
    path_prefix: str = "nvs/sync"


class VaultConfig(BaseModel):
    enabled: bool = False
    url: str = ""
    verify_ssl: bool = True
    auth: VaultAuthConfig = VaultAuthConfig()

    @model_validator(mode="after")
    def check_url_if_enabled(self) -> VaultConfig:
        if self.enabled and not self.url:
            raise ValueError("vault.url is required when vault is enabled")
        return self


class VlanAllocationConfig(BaseModel):
    strategy: Literal["from_portgroup", "reserved_range", "auto_allocate"] = "from_portgroup"
    range_start: int = 3000
    range_end: int = 3999

    @field_validator("range_end")
    @classmethod
    def check_range(cls, v: int, info: ValidationInfo) -> int:
        range_start: int = info.data.get("range_start", 3000)  # type: ignore[no-untyped-call]
        if v <= range_start:
            raise ValueError("range_end must be greater than range_start")
        return v


class IpAddressRoleRule(BaseModel):
    pattern: str = ""
    role: str | None = None


class SyncConfig(BaseModel):
    prune: bool = False
    dry_run: bool = False
    vlan_allocation: VlanAllocationConfig = VlanAllocationConfig()
    ipaddress_role_mapping: list[IpAddressRoleRule] = []


class BootstrapConfig(BaseModel):
    enabled: bool = True
    create_manufacturer: bool = True
    create_device_role: bool = True
    create_cluster_type: bool = True
    create_custom_fields: bool = True


class InventoryRoleConfig(BaseModel):
    storage: str = "Storage"


class AppConfig(BaseModel):
    vcenter: VCenterConfig
    netbox: NetBoxConfig
    vault: VaultConfig = VaultConfig()
    sync: SyncConfig = SyncConfig()
    bootstrap: BootstrapConfig = BootstrapConfig()
    inventory_roles: InventoryRoleConfig = InventoryRoleConfig()
