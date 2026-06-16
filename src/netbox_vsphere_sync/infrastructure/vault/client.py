from __future__ import annotations

import time

import hvac
import structlog

from netbox_vsphere_sync.domain.exceptions import VaultConnectionError
from netbox_vsphere_sync.domain.model.config import VaultConfig

log = structlog.get_logger(__name__)


class VaultClient:
    def __init__(self, config: VaultConfig) -> None:
        self._config = config
        self._client: hvac.Client | None = None
        self._token_expires_at: float = 0

    def connect(self) -> None:
        if not self._config.enabled:
            log.debug("vault.connect.skipped", reason="disabled")
            return

        log.info("vault.connect.start", url=self._config.url)
        try:
            self._client = hvac.Client(
                url=self._config.url,
                verify=self._config.verify_ssl,
            )

            auth = self._config.auth
            log.debug("vault.auth.method", method=auth.method)
            if auth.method == "token":
                pass
            elif auth.method == "approle":
                role_id = self._get_env("VAULT_ROLE_ID", "")
                secret_id = self._get_env("VAULT_SECRET_ID", "")
                if role_id and secret_id:
                    self._client.auth.approle.login(role_id=role_id, secret_id=secret_id)
            elif auth.method == "kubernetes":
                role = self._get_env("VAULT_K8S_ROLE", "")
                jwt_path = self._get_env(
                    "VAULT_K8S_JWT_PATH", "/var/run/secrets/kubernetes.io/serviceaccount/token"
                )
                if role:
                    with open(jwt_path) as f:
                        jwt = f.read().strip()
                    self._client.auth.kubernetes.login(role=role, jwt=jwt)

            if not self._client.is_authenticated():
                log.error("vault.auth.failed")
                raise VaultConnectionError("Vault authentication failed")

            self._schedule_renewal()
            log.info("vault.connect.complete")

        except VaultConnectionError:
            raise
        except Exception as exc:
            log.error("vault.connect.failed", error=str(exc))
            raise VaultConnectionError(f"Vault connection failed: {exc}") from exc

    def read_secret(self, path: str) -> dict[str, str] | None:
        if not self._client or not self._config.enabled:
            return None

        self._ensure_token()

        try:
            full_path = f"{self._config.auth.path_prefix}/{path}"
            log.debug("vault.read_secret.start", path=full_path)
            response = self._client.secrets.kv.v2.read_secret_version(
                path=full_path,
                mount_point=self._config.auth.mount_point,
            )
            data: dict = response.get("data", {}).get("data", {})
            log.debug("vault.read_secret.complete", path=full_path, keys=list(data.keys()))
            return {str(k): str(v) for k, v in data.items()}
        except Exception as exc:
            log.warning("vault.read_secret.failed", path=path, error=str(exc))
            return None

    def _ensure_token(self) -> None:
        if self._client and self._token_expires_at > 0:
            if time.time() >= self._token_expires_at:
                log.debug("vault.token.renewing")
                self._client.renew_token()
                log.debug("vault.token.renewed")

    def _schedule_renewal(self) -> None:
        if self._client and self._client.token:
            try:
                lookup = self._client.lookup_token()
                ttl = lookup.get("data", {}).get("ttl", 3600)
                self._token_expires_at = time.time() + int(ttl) * 0.9
                log.debug("vault.token.scheduled_renewal", ttl=ttl)
            except Exception:
                self._token_expires_at = time.time() + 3240
                log.debug("vault.token.scheduled_renewal_fallback")

    def _get_env(self, key: str, default: str) -> str:
        import os

        return os.environ.get(key, default)
