from __future__ import annotations

import pynetbox

from netbox_vsphere_sync.domain.exceptions import NetBoxConnectionError
from netbox_vsphere_sync.domain.model.config import NetBoxConfig


class NetBoxClient:
    def __init__(self, config: NetBoxConfig) -> None:
        self._config = config
        self._api: pynetbox.api | None = None

    def connect(self) -> None:
        try:
            self._api = pynetbox.api(
                url=self._config.url,
                token=self._config.token,
            )
            self._api.http_session.verify = self._config.verify_ssl
            self._api.status()
        except Exception as exc:
            raise NetBoxConnectionError(
                f"Failed to connect to NetBox at {self._config.url}: {exc}"
            ) from exc

    @property
    def api(self) -> pynetbox.api:
        if self._api is None:
            raise NetBoxConnectionError("Not connected to NetBox")
        return self._api

    def list_all(self, endpoint: str) -> list[dict]:
        try:
            app_model = endpoint.split(".")
            if len(app_model) != 2:
                return []
            app = getattr(self.api, app_model[0])
            model = getattr(app, app_model[1])
            return [dict(item) for item in model.all()]
        except Exception as exc:
            raise NetBoxConnectionError(f"Failed to list {endpoint}: {exc}") from exc

    def get_by_field(self, endpoint: str, field: str, value: object) -> dict | None:
        try:
            app_model = endpoint.split(".")
            if len(app_model) != 2:
                return None
            app = getattr(self.api, app_model[0])
            model = getattr(app, app_model[1])
            result = model.get(**{field: value})
            return dict(result) if result else None
        except Exception:
            return None

    def create(self, endpoint: str, data: dict) -> dict:
        try:
            app_model = endpoint.split(".")
            app = getattr(self.api, app_model[0])
            model = getattr(app, app_model[1])
            result = model.create(data)
            return dict(result) if result else {}
        except Exception as exc:
            raise NetBoxConnectionError(f"Failed to create {endpoint}: {exc}") from exc

    def update(self, endpoint: str, netbox_id: int, data: dict) -> dict:
        try:
            app_model = endpoint.split(".")
            app = getattr(self.api, app_model[0])
            model = getattr(app, app_model[1])
            obj = model.get(netbox_id)
            if obj:
                result = obj.update(data)
                return dict(result) if result else {}
            return {}
        except Exception as exc:
            raise NetBoxConnectionError(
                f"Failed to update {endpoint} id={netbox_id}: {exc}"
            ) from exc
