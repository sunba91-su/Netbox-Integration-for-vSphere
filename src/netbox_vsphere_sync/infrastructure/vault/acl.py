from __future__ import annotations

from netbox_vsphere_sync.infrastructure.vault.client import VaultClient


class VaultACL:
    def __init__(self, client: VaultClient) -> None:
        self._client = client

    def resolve_credentials(self, path: str, fields: list[str]) -> dict[str, str]:
        secret = self._client.read_secret(path)
        if not secret:
            return {}

        return {field: secret.get(field, "") for field in fields}

    def is_available(self) -> bool:
        return self._client is not None
