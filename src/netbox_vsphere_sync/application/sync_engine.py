from __future__ import annotations

import time

from netbox_vsphere_sync.application.bootstrapper import Bootstrapper
from netbox_vsphere_sync.application.dependency_resolver import DependencyResolver
from netbox_vsphere_sync.application.diff_engine import DiffEngine, DiffResult, DomainEntity
from netbox_vsphere_sync.application.event_log import EventLog
from netbox_vsphere_sync.domain.events import (
    EntityCreated,
    EntityPruned,
    EntitySkipped,
    EntityUpdated,
    SyncCompleted,
    SyncError,
    SyncStarted,
)
from netbox_vsphere_sync.domain.exceptions import (
    ConnectionError,
)
from netbox_vsphere_sync.domain.exceptions import (
    SyncError as SyncDomainError,
)
from netbox_vsphere_sync.domain.model.config import SyncConfig
from netbox_vsphere_sync.domain.model.vsphere import (
    Cluster,
    Datastore,
    HostSystem,
    Interface,
    IpAddress,
    PortGroup,
    Site,
    Vlan,
)
from netbox_vsphere_sync.domain.ports import (
    ClusterRepository,
    DeviceRepository,
    InterfaceRepository,
    InventoryItemRepository,
    IpAddressRepository,
    LockManager,
    SiteRepository,
    VlanRepository,
    VSphereCollector,
)

ENTITY_TYPE_MAP: dict[type, str] = {
    Site: "site",
    Cluster: "cluster",
    HostSystem: "device",
    Interface: "interface",
    IpAddress: "ip_address",
    Vlan: "vlan",
    Datastore: "inventory_item",
    PortGroup: "portgroup",
}


class SyncEngine:
    def __init__(
        self,
        collector: VSphereCollector,
        site_repo: SiteRepository,
        cluster_repo: ClusterRepository,
        device_repo: DeviceRepository,
        interface_repo: InterfaceRepository,
        ip_repo: IpAddressRepository,
        vlan_repo: VlanRepository,
        inventory_repo: InventoryItemRepository,
        bootstrapper: Bootstrapper,
        lock_manager: LockManager,
        diff_engine: DiffEngine,
        dependency_resolver: DependencyResolver,
        event_log: EventLog,
        config: SyncConfig,
    ) -> None:
        self._collector = collector
        self._site_repo = site_repo
        self._cluster_repo = cluster_repo
        self._device_repo = device_repo
        self._interface_repo = interface_repo
        self._ip_repo = ip_repo
        self._vlan_repo = vlan_repo
        self._inventory_repo = inventory_repo
        self._bootstrapper = bootstrapper
        self._lock_manager = lock_manager
        self._diff_engine = diff_engine
        self._dependency_resolver = dependency_resolver
        self._event_log = event_log
        self._config = config

    def run(self) -> int:
        start_time = time.monotonic()
        self._event_log.record(
            SyncStarted(
                config_path="",
                dry_run=self._config.dry_run,
                prune=self._config.prune,
            )
        )

        try:
            if not self._lock_manager.acquire():
                self._event_log.record(
                    EntitySkipped(
                        entity_type="sync",
                        natural_key="global",
                        reason="Another sync in progress",
                    )
                )
                return 0

            self._bootstrapper.run()

            vsphere_data = self._collect_all()
            netbox_data = self._fetch_all()

            diff = self._diff_engine.compute(vsphere_data, netbox_data)

            if not self._config.dry_run:
                self._apply_diff(diff)

            self._handle_prune(diff)

        except (ConnectionError, SyncDomainError) as exc:
            self._event_log.record(
                SyncError(
                    error_message=str(exc),
                    exception_type=type(exc).__name__,
                )
            )
            return 2
        finally:
            self._lock_manager.release()

        duration = time.monotonic() - start_time
        self._event_log.record(
            SyncCompleted(
                duration_seconds=duration,
                created_count=self._event_log.created_count,
                updated_count=self._event_log.updated_count,
                skipped_count=self._event_log.skipped_count,
                pruned_count=self._event_log.pruned_count,
                error_count=self._event_log.error_count,
            )
        )

        if self._event_log.error_count > 0:
            return 1
        return 0

    def _collect_all(self) -> list[DomainEntity]:
        entities: list[DomainEntity] = []
        entities.extend(self._collector.collect_sites())
        entities.extend(self._collector.collect_clusters())
        entities.extend(self._collector.collect_hosts())
        entities.extend(self._collector.collect_port_groups())
        entities.extend(self._collector.collect_datastores())
        return entities

    def _fetch_all(self) -> list[DomainEntity]:
        entities: list[DomainEntity] = []
        try:
            entities.extend(self._site_repo.list_all())
        except Exception as exc:
            self._event_log.record(
                SyncError(
                    entity_type="site", error_message=str(exc), exception_type=type(exc).__name__
                )
            )
        try:
            entities.extend(self._cluster_repo.list_all())
        except Exception as exc:
            self._event_log.record(
                SyncError(
                    entity_type="cluster", error_message=str(exc), exception_type=type(exc).__name__
                )
            )
        try:
            entities.extend(self._device_repo.list_all())
        except Exception as exc:
            self._event_log.record(
                SyncError(
                    entity_type="device", error_message=str(exc), exception_type=type(exc).__name__
                )
            )
        try:
            entities.extend(self._interface_repo.list_all())
        except Exception as exc:
            self._event_log.record(
                SyncError(
                    entity_type="interface",
                    error_message=str(exc),
                    exception_type=type(exc).__name__,
                )
            )
        try:
            entities.extend(self._ip_repo.list_all())
        except Exception as exc:
            self._event_log.record(
                SyncError(
                    entity_type="ip_address",
                    error_message=str(exc),
                    exception_type=type(exc).__name__,
                )
            )
        try:
            entities.extend(self._vlan_repo.list_all())
        except Exception as exc:
            self._event_log.record(
                SyncError(
                    entity_type="vlan", error_message=str(exc), exception_type=type(exc).__name__
                )
            )
        try:
            entities.extend(self._inventory_repo.list_all())
        except Exception as exc:
            self._event_log.record(
                SyncError(
                    entity_type="inventory_item",
                    error_message=str(exc),
                    exception_type=type(exc).__name__,
                )
            )
        return entities

    def _apply_diff(self, diff: DiffResult) -> None:
        entity_types = self._dependency_resolver.resolve(
            {self._diff_engine.entity_type(e) for e in diff.to_create}
            | {self._diff_engine.entity_type(e) for e, _ in diff.to_update}
        )

        for entity_type in entity_types:
            self._apply_entity_type(entity_type, diff)

    def _apply_entity_type(self, entity_type: str, diff: DiffResult) -> None:
        for entity in diff.to_create:
            if self._diff_engine.entity_type(entity) != entity_type:
                continue
            try:
                key = self._diff_engine.natural_key(entity)
                created = self._create_entity(entity)
                self._event_log.record(
                    EntityCreated(
                        entity_type=entity_type,
                        natural_key=key,
                        netbox_id=getattr(created, "id", None),
                    )
                )
            except Exception as exc:
                self._event_log.record(
                    SyncError(
                        entity_type=entity_type,
                        natural_key=self._diff_engine.natural_key(entity),
                        error_message=str(exc),
                        exception_type=type(exc).__name__,
                    )
                )

        for nb_entity, vs_entity in diff.to_update:
            if self._diff_engine.entity_type(vs_entity) != entity_type:
                continue
            try:
                key = self._diff_engine.natural_key(vs_entity)
                changes = self._diff_engine.compute_changes(vs_entity, nb_entity)
                updated = self._update_entity(vs_entity)
                self._event_log.record(
                    EntityUpdated(
                        entity_type=entity_type,
                        natural_key=key,
                        netbox_id=getattr(updated, "id", 0),
                        changes=changes,
                    )
                )
            except Exception as exc:
                self._event_log.record(
                    SyncError(
                        entity_type=entity_type,
                        natural_key=self._diff_engine.natural_key(vs_entity),
                        error_message=str(exc),
                        exception_type=type(exc).__name__,
                    )
                )

    def _create_entity(self, entity: DomainEntity) -> DomainEntity:
        match entity:
            case Site():
                return self._site_repo.create(entity)
            case Cluster():
                return self._cluster_repo.create(entity)
            case HostSystem():
                return self._device_repo.create(entity)
            case Interface():
                return self._interface_repo.create(entity)
            case IpAddress():
                return self._ip_repo.create(entity)
            case Vlan():
                return self._vlan_repo.create(entity)
            case Datastore():
                return self._inventory_repo.create(entity)
            case _:
                return entity

    def _update_entity(self, entity: DomainEntity) -> DomainEntity:
        match entity:
            case Site():
                return self._site_repo.update(entity)
            case Cluster():
                return self._cluster_repo.update(entity)
            case HostSystem():
                return self._device_repo.update(entity)
            case Interface():
                return self._interface_repo.update(entity)
            case IpAddress():
                return self._ip_repo.update(entity)
            case Vlan():
                return self._vlan_repo.update(entity)
            case Datastore():
                return self._inventory_repo.update(entity)
            case _:
                return entity

    def _handle_prune(self, diff: DiffResult) -> None:
        if not self._config.prune:
            return
        for entity_type, natural_key, new_status in diff.to_prune:
            try:
                self._event_log.record(
                    EntityPruned(
                        entity_type=entity_type,
                        natural_key=natural_key,
                        new_status=new_status,
                    )
                )
            except Exception as exc:
                self._event_log.record(
                    SyncError(
                        entity_type=entity_type,
                        natural_key=natural_key,
                        error_message=str(exc),
                        exception_type=type(exc).__name__,
                    )
                )
