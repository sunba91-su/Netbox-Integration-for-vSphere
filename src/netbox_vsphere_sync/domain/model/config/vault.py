from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, model_validator


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
