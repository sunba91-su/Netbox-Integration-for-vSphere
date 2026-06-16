from __future__ import annotations

import pynetbox
import structlog

from netbox_vsphere_sync.domain.exceptions import NetBoxConnectionError
from netbox_vsphere_sync.domain.model.config import NetBoxConfig

log = structlog.get_logger(__name__)


class NetBoxClient:
    def __init__(self, config: NetBoxConfig) -> None:
        self._config = config
        self._api: pynetbox.api | None = None

    def connect(self) -> None:
        log.info("netbox.connect.start", url=self._config.url)
        try:
            self._api = pynetbox.api(
                url=self._config.url,
                token=self._config.token,
            )
            self._api.http_session.verify = self._config.verify_ssl
            self._api.status()
            log.info("netbox.connect.complete", url=self._config.url)
        except Exception as exc:
            log.error("netbox.connect.failed", url=self._config.url, error=str(exc))
            raise NetBoxConnectionError(
                f"Failed to connect to NetBox at {self._config.url}: {exc}"
            ) from exc

    @property
    def api(self) -> pynetbox.api:
        if self._api is None:
            raise NetBoxConnectionError("Not connected to NetBox")
        return self._api

    def list_all(self, endpoint: str) -> list[dict]:
        log.debug("netbox.list_all.start", endpoint=endpoint)
        try:
            app_model = endpoint.split(".")
            if len(app_model) != 2:
                return []
            app = getattr(self.api, app_model[0])
            model = getattr(app, app_model[1])
            items = [dict(item) for item in model.all()]
            log.debug("netbox.list_all.complete", endpoint=endpoint, count=len(items))
            return items
        except Exception as exc:
            log.warning("netbox.list_all.failed", endpoint=endpoint, error=str(exc))
            raise NetBoxConnectionError(f"Failed to list {endpoint}: {exc}") from exc

    def get_by_field(self, endpoint: str, field: str, value: object) -> dict | None:
        log.debug("netbox.get_by_field.start", endpoint=endpoint, field=field)
        try:
            app_model = endpoint.split(".")
            if len(app_model) != 2:
                return None
            app = getattr(self.api, app_model[0])
            model = getattr(app, app_model[1])
            result = model.get(**{field: value})
            found = dict(result) if result else None
            log.debug(
                "netbox.get_by_field.complete",
                endpoint=endpoint,
                field=field,
                found=found is not None,
            )
            return found
        except Exception as exc:
            log.warning(
                "netbox.get_by_field.failed",
                endpoint=endpoint,
                field=field,
                error=str(exc),
            )
            return None

    def create(self, endpoint: str, data: dict) -> dict:
        log.debug("netbox.create.start", endpoint=endpoint)
        try:
            app_model = endpoint.split(".")
            app = getattr(self.api, app_model[0])
            model = getattr(app, app_model[1])
            result = model.create(data)
            log.info("netbox.create.complete", endpoint=endpoint)
            return dict(result) if result else {}
        except Exception as exc:
            log.warning("netbox.create.failed", endpoint=endpoint, error=str(exc))
            raise NetBoxConnectionError(f"Failed to create {endpoint}: {exc}") from exc

    def update(self, endpoint: str, netbox_id: int, data: dict) -> dict:
        log.debug("netbox.update.start", endpoint=endpoint, netbox_id=netbox_id)
        try:
            app_model = endpoint.split(".")
            app = getattr(self.api, app_model[0])
            model = getattr(app, app_model[1])
            obj = model.get(netbox_id)
            if obj:
                result = obj.update(data)
                log.info("netbox.update.complete", endpoint=endpoint, netbox_id=netbox_id)
                return dict(result) if result else {}
            log.warning("netbox.update.not_found", endpoint=endpoint, netbox_id=netbox_id)
            return {}
        except Exception as exc:
            log.warning(
                "netbox.update.failed",
                endpoint=endpoint,
                netbox_id=netbox_id,
                error=str(exc),
            )
            raise NetBoxConnectionError(
                f"Failed to update {endpoint} id={netbox_id}: {exc}"
            ) from exc
