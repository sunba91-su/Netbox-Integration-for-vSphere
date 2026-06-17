from __future__ import annotations

from netbox_vsphere_sync.domain.ports import NetBoxBootstrap
from netbox_vsphere_sync.infrastructure.netbox.client import NetBoxClient


class NetBoxBootstrapRepository(NetBoxBootstrap):
    def __init__(self, client: NetBoxClient) -> None:
        self._client = client

    def ensure_manufacturer(self, name: str) -> None:
        existing = self._client.get_by_field("dcim.manufacturers", "name", name)
        if existing:
            return
        self._client.create("dcim.manufacturers", {"name": name, "slug": self._slug(name)})

    def ensure_device_role(self, name: str, color: str) -> None:
        existing = self._client.get_by_field("dcim.device_roles", "name", name)
        if existing:
            return
        self._client.create(
            "dcim.device_roles",
            {"name": name, "slug": self._slug(name), "color": color},
        )

    def ensure_cluster_type(self, name: str) -> None:
        # Cluster types endpoint not available in all NetBox versions
        # Skip if not available
        try:
            existing = self._client.get_by_field("dcim.cluster_types", "name", name)
            if existing:
                return
            self._client.create("dcim.cluster_types", {"name": name, "slug": self._slug(name)})
        except Exception as exc:
            # Endpoint not available in this NetBox version, skip
            import structlog
            log = structlog.get_logger(__name__)
            log.debug("cluster_types_endpoint_unavailable", error=str(exc))

    def ensure_custom_fields(self) -> None:
        # Custom fields endpoint doesn't support brief parameter
        existing = self._client.list_all("extras.custom_fields", brief=False, exclude_config_context=False)
        existing_names = {d.get("name") for d in existing}

        from netbox_vsphere_sync.domain.constants import CUSTOM_FIELD_DEFINITIONS

        for cf_def in CUSTOM_FIELD_DEFINITIONS:
            if cf_def.name in existing_names:
                continue
            self._client.create(
                "extras.custom_fields",
                {
                    "name": cf_def.name,
                    "label": cf_def.label,
                    "content_types": cf_def.content_types,
                    "type": cf_def.data_type,
                },
            )

    def _slug(self, name: str) -> str:
        return name.lower().replace(" ", "-").replace("_", "-")
