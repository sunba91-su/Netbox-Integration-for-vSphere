from __future__ import annotations

from netbox_vsphere_sync.domain.exceptions import CredentialNotFoundError
from netbox_vsphere_sync.domain.model.config import (
    AppConfig,
    NetBoxConfig,
    VCenterConfig,
)
from netbox_vsphere_sync.infrastructure.vault.client import VaultClient


class SecretResolver:
    def __init__(
        self,
        config: AppConfig,
        vault_client: VaultClient | None = None,
    ) -> None:
        self._config = config
        self._vault_client = vault_client

    def resolve_vcenter(self, cli_overrides: dict[str, str] | None = None) -> VCenterConfig:
        resolved = self._config.vcenter.model_copy()

        if cli_overrides:
            for key, value in cli_overrides.items():
                if hasattr(resolved, key) and value:
                    setattr(resolved, key, value)

        if not resolved.password and self._vault_client:
            secret = self._vault_client.read_secret("vcenter")
            if secret:
                resolved.password = secret.get("password", "")
                if not resolved.username:
                    resolved.username = secret.get("username", "")

        if not resolved.username or not resolved.password:
            raise CredentialNotFoundError(
                "vCenter credentials not resolved. Provide via CLI, "
                "env vars, Vault, or config file."
            )

        return resolved

    def resolve_netbox(self, cli_overrides: dict[str, str] | None = None) -> NetBoxConfig:
        resolved = self._config.netbox.model_copy()

        if cli_overrides:
            for key, value in cli_overrides.items():
                if hasattr(resolved, key) and value:
                    setattr(resolved, key, value)

        if not resolved.token and self._vault_client:
            secret = self._vault_client.read_secret("netbox")
            if secret:
                resolved.token = secret.get("token", "")

        if not resolved.token:
            raise CredentialNotFoundError(
                "NetBox token not resolved. Provide via CLI, env vars, Vault, or config file."
            )

        return resolved
