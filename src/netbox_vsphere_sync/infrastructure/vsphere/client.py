from __future__ import annotations

import structlog
from pyVim.connect import Disconnect, SmartConnect
from pyVmomi import vim

from netbox_vsphere_sync.domain.exceptions import VCenterConnectionError
from netbox_vsphere_sync.domain.model.config import VCenterConfig

log = structlog.get_logger(__name__)


class VSphereClient:
    def __init__(self, config: VCenterConfig) -> None:
        self._config = config
        self._si: vim.ServiceInstance | None = None

    def connect(self) -> None:
        log.info("vsphere.connect.start", host=self._config.host)
        try:
            self._si = SmartConnect(
                host=self._config.host,
                user=self._config.username,
                pwd=self._config.password,
                ssl=not self._config.verify_ssl,
            )
            log.info("vsphere.connect.complete", host=self._config.host)
        except Exception as exc:
            log.error("vsphere.connect.failed", host=self._config.host, error=str(exc))
            raise VCenterConnectionError(
                f"Failed to connect to vCenter at {self._config.host}: {exc}"
            ) from exc

    def disconnect(self) -> None:
        if self._si:
            try:
                Disconnect(self._si)
                log.info("vsphere.disconnect.complete")
            except Exception as exc:
                log.warning("vsphere.disconnect.error", error=str(exc))
            self._si = None

    @property
    def service_instance(self) -> vim.ServiceInstance:
        if self._si is None:
            raise VCenterConnectionError("Not connected to vCenter")
        return self._si

    @property
    def root_folder(self) -> vim.Folder:
        return self.service_instance.content.rootFolder

    @property
    def datacenters(self) -> list[vim.Datacenter]:
        container = self.service_instance.content.viewManager.CreateContainerView(
            container=self.root_folder,
            type=[vim.Datacenter],
            recursive=True,
        )
        return list(container.view)  # type: ignore[no-any-return]

    def collect_properties(
        self,
        obj_type: type,
        properties: list[str],
        container: vim.Folder | None = None,
    ) -> list[dict]:
        if container is None:
            container = self.root_folder

        log.debug(
            "vsphere.collect_properties.start",
            obj_type=obj_type.__name__,
            properties=properties,
        )

        view_ref = self.service_instance.content.viewManager.CreateContainerView(
            container=container,
            type=[obj_type],
            recursive=True,
        )

        try:
            collector = self.service_instance.content.propertyCollector
            traversal_spec = vim.TraversalSpec(
                name="traverseEntities",
                path="view",
                skip=False,
                type=vim.view.ContainerView,
            )
            obj_spec = vim.ObjectSpec(
                obj=view_ref,
                skip=True,
                selectSet=[traversal_spec],
            )
            prop_spec = vim.PropertySpec(
                type=obj_type,
                all=False,
                pathSet=properties,
            )
            filter_spec = vim.PropertyFilterSpec(
                objectSet=[obj_spec],
                propSet=[prop_spec],
            )

            results = collector.RetrieveProperties(specSet=[filter_spec])
            collected = [
                {prop: self._extract_value(obj, prop) for prop in properties} for obj in results
            ]
            log.debug(
                "vsphere.collect_properties.complete",
                obj_type=obj_type.__name__,
                count=len(collected),
            )
            return collected
        finally:
            view_ref.DestroyView()

    def _extract_value(self, obj, prop: str) -> object:
        parts = prop.split(".")
        current = obj
        for part in parts:
            if hasattr(current, part):
                current = getattr(current, part)
            else:
                return None
        return current
