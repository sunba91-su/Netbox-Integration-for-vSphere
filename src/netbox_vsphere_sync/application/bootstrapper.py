import structlog

from netbox_vsphere_sync.application.event_log import EventLog
from netbox_vsphere_sync.domain.constants import (
    CLUSTER_TYPE_VSPHERE,
    CUSTOM_FIELD_DEFINITIONS,
    DEVICE_ROLE_ESXI,
    MANUFACTURER_VMWARE,
)
from netbox_vsphere_sync.domain.events import BootstrapCreated, BootstrapSkipped
from netbox_vsphere_sync.domain.exceptions import BootstrapError
from netbox_vsphere_sync.domain.model.config import BootstrapConfig
from netbox_vsphere_sync.domain.ports import NetBoxBootstrap


class Bootstrapper:
    def __init__(
        self,
        bootstrap: NetBoxBootstrap,
        config: BootstrapConfig,
        event_log: EventLog,
    ) -> None:
        self._bootstrap = bootstrap
        self._config = config
        self._event_log = event_log
        self._log = structlog.get_logger(__name__)

    def run(self) -> None:
        if not self._config.enabled:
            self._log.debug("bootstrap.disabled")
            return

        self._log.info("bootstrap.start")
        try:
            self._ensure_manufacturer()
            self._ensure_device_role()
            self._ensure_cluster_type()
            self._ensure_custom_fields()
            self._log.info("bootstrap.complete")
        except Exception as exc:
            self._log.error("bootstrap.failed", error=str(exc))
            raise BootstrapError(f"Bootstrap failed: {exc}") from exc

    def _ensure_manufacturer(self) -> None:
        if not self._config.create_manufacturer:
            return
        try:
            self._bootstrap.ensure_manufacturer(MANUFACTURER_VMWARE)
            self._log.info(
                "bootstrap.object_created",
                object_type="manufacturer",
                name=MANUFACTURER_VMWARE,
            )
            self._event_log.record(
                BootstrapCreated(object_type="manufacturer", name=MANUFACTURER_VMWARE)
            )
        except Exception:
            self._log.debug(
                "bootstrap.object_exists",
                object_type="manufacturer",
                name=MANUFACTURER_VMWARE,
            )
            self._event_log.record(
                BootstrapSkipped(
                    object_type="manufacturer",
                    name=MANUFACTURER_VMWARE,
                    reason="Already exists",
                )
            )

    def _ensure_device_role(self) -> None:
        if not self._config.create_device_role:
            return
        try:
            self._bootstrap.ensure_device_role(DEVICE_ROLE_ESXI, color="4630e3")
            self._log.info(
                "bootstrap.object_created",
                object_type="device_role",
                name=DEVICE_ROLE_ESXI,
            )
            self._event_log.record(
                BootstrapCreated(object_type="device_role", name=DEVICE_ROLE_ESXI)
            )
        except Exception:
            self._log.debug(
                "bootstrap.object_exists",
                object_type="device_role",
                name=DEVICE_ROLE_ESXI,
            )
            self._event_log.record(
                BootstrapSkipped(
                    object_type="device_role",
                    name=DEVICE_ROLE_ESXI,
                    reason="Already exists",
                )
            )

    def _ensure_cluster_type(self) -> None:
        if not self._config.create_cluster_type:
            return
        try:
            self._bootstrap.ensure_cluster_type(CLUSTER_TYPE_VSPHERE)
            self._log.info(
                "bootstrap.object_created",
                object_type="cluster_type",
                name=CLUSTER_TYPE_VSPHERE,
            )
            self._event_log.record(
                BootstrapCreated(object_type="cluster_type", name=CLUSTER_TYPE_VSPHERE)
            )
        except Exception:
            self._log.debug(
                "bootstrap.object_exists",
                object_type="cluster_type",
                name=CLUSTER_TYPE_VSPHERE,
            )
            self._event_log.record(
                BootstrapSkipped(
                    object_type="cluster_type",
                    name=CLUSTER_TYPE_VSPHERE,
                    reason="Already exists",
                )
            )

    def _ensure_custom_fields(self) -> None:
        if not self._config.create_custom_fields:
            return
        for cf_def in CUSTOM_FIELD_DEFINITIONS:
            try:
                self._bootstrap.ensure_custom_fields()
                self._log.info(
                    "bootstrap.object_created",
                    object_type="custom_field",
                    name=cf_def.name,
                )
                self._event_log.record(
                    BootstrapCreated(object_type="custom_field", name=cf_def.name)
                )
                return
            except Exception:
                self._log.debug(
                    "bootstrap.object_exists",
                    object_type="custom_field",
                    name=cf_def.name,
                )
                self._event_log.record(
                    BootstrapSkipped(
                        object_type="custom_field",
                        name=cf_def.name,
                        reason="Already exists or failed",
                    )
                )
