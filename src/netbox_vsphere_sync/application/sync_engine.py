from __future__ import annotations

import time

import structlog

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
        self._log = structlog.get_logger(__name__)

    def run(self) -> int:
        start_time = time.monotonic()
        self._log.info(
            "sync.start",
            dry_run=self._config.dry_run,
            prune=self._config.prune,
        )
        self._event_log.record(
            SyncStarted(
                config_path="",
                dry_run=self._config.dry_run,
                prune=self._config.prune,
            )
        )

        try:
            if not self._lock_manager.acquire():
                self._log.warning("sync.lock_acquired", acquired=False)
                self._event_log.record(
                    EntitySkipped(
                        entity_type="sync",
                        natural_key="global",
                        reason="Another sync in progress",
                    )
                )
                return 0

            self._log.debug("sync.lock_acquired", acquired=True)
            self._bootstrapper.run()

            vsphere_data = self._collect_all()
            netbox_data = self._fetch_all()

            diff = self._diff_engine.compute(vsphere_data, netbox_data)
            self._log.info(
                "sync.diff_computed",
                to_create=len(diff.to_create),
                to_update=len(diff.to_update),
                to_skip=len(diff.to_skip),
                to_prune=len(diff.to_prune),
            )

            if not self._config.dry_run:
                self._apply_diff(diff)

            self._handle_prune(diff)

        except (ConnectionError, SyncDomainError) as exc:
            self._log.error("sync.error", error=str(exc), exception_type=type(exc).__name__)
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
        self._log.info(
            "sync.completed",
            duration_seconds=round(duration, 2),
            created_count=self._event_log.created_count,
            updated_count=self._event_log.updated_count,
            skipped_count=self._event_log.skipped_count,
            pruned_count=self._event_log.pruned_count,
            error_count=self._event_log.error_count,
        )
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
        self._log.debug("sync.collect_vsphere.start")
        entities: list[DomainEntity] = []
        entities.extend(self._collector.collect_sites())
        entities.extend(self._collector.collect_clusters())
        entities.extend(self._collector.collect_hosts())
        entities.extend(self._collector.collect_port_groups())
        entities.extend(self._collector.collect_datastores())
        self._log.debug("sync.collect_vsphere.complete", entity_count=len(entities))
        return entities

    def _fetch_all(self) -> list[DomainEntity]:
        self._log.debug("sync.fetch_netbox.start")
        entities: list[DomainEntity] = []
        try:
            entities.extend(self._site_repo.list_all())
        except Exception as exc:
            self._log.warning("sync.fetch_netbox.failed", entity_type="site", error=str(exc))
            self._event_log.record(
                SyncError(
                    entity_type="site", error_message=str(exc), exception_type=type(exc).__name__
                )
            )
        try:
            entities.extend(self._cluster_repo.list_all())
        except Exception as exc:
            self._log.warning("sync.fetch_netbox.failed", entity_type="cluster", error=str(exc))
            self._event_log.record(
                SyncError(
                    entity_type="cluster", error_message=str(exc), exception_type=type(exc).__name__
                )
            )
        try:
            entities.extend(self._device_repo.list_all())
        except Exception as exc:
            self._log.warning("sync.fetch_netbox.failed", entity_type="device", error=str(exc))
            self._event_log.record(
                SyncError(
                    entity_type="device", error_message=str(exc), exception_type=type(exc).__name__
                )
            )
        try:
            entities.extend(self._interface_repo.list_all())
        except Exception as exc:
            self._log.warning("sync.fetch_netbox.failed", entity_type="interface", error=str(exc))
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
            self._log.warning("sync.fetch_netbox.failed", entity_type="ip_address", error=str(exc))
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
            self._log.warning("sync.fetch_netbox.failed", entity_type="vlan", error=str(exc))
            self._event_log.record(
                SyncError(
                    entity_type="vlan", error_message=str(exc), exception_type=type(exc).__name__
                )
            )
        try:
            entities.extend(self._inventory_repo.list_all())
        except Exception as exc:
            self._log.warning(
                "sync.fetch_netbox.failed",
                entity_type="inventory_item",
                error=str(exc),
            )
            self._event_log.record(
                SyncError(
                    entity_type="inventory_item",
                    error_message=str(exc),
                    exception_type=type(exc).__name__,
                )
            )
        self._log.debug("sync.fetch_netbox.complete", entity_count=len(entities))
        return entities

    def _apply_diff(self, diff: DiffResult) -> None:
        self._log.debug("sync.apply_diff.start")
        entity_types = self._dependency_resolver.resolve(
            {self._diff_engine.entity_type(e) for e in diff.to_create}
            | {self._diff_engine.entity_type(e) for e, _ in diff.to_update}
        )

        for entity_type in entity_types:
            self._apply_entity_type(entity_type, diff)
        self._log.debug("sync.apply_diff.complete")

    def _apply_entity_type(self, entity_type: str, diff: DiffResult) -> None:
        for entity in diff.to_create:
            if self._diff_engine.entity_type(entity) != entity_type:
                continue
            try:
                key = self._diff_engine.natural_key(entity)
                created = self._create_entity(entity)
                self._log.info("entity.created", entity_type=entity_type, natural_key=key)
                self._event_log.record(
                    EntityCreated(
                        entity_type=entity_type,
                        natural_key=key,
                        netbox_id=getattr(created, "id", None),
                    )
                )
            except Exception as exc:
                self._log.warning(
                    "entity.create_failed",
                    entity_type=entity_type,
                    natural_key=self._diff_engine.natural_key(entity),
                    error=str(exc),
                )
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
                self._log.info(
                    "entity.updated",
                    entity_type=entity_type,
                    natural_key=key,
                    changed_fields=list(changes.keys()),
                )
                self._event_log.record(
                    EntityUpdated(
                        entity_type=entity_type,
                        natural_key=key,
                        netbox_id=getattr(updated, "id", 0),
                        changes=changes,
                    )
                )
            except Exception as exc:
                self._log.warning(
                    "entity.update_failed",
                    entity_type=entity_type,
                    natural_key=self._diff_engine.natural_key(vs_entity),
                    error=str(exc),
                )
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
        self._log.debug("sync.prune.start", prune_count=len(diff.to_prune))

        repo_map = {
            "site": self._site_repo,
            "cluster": self._cluster_repo,
            "device": self._device_repo,
            "interface": self._interface_repo,
            "ip_address": self._ip_repo,
            "vlan": self._vlan_repo,
            "inventory_item": self._inventory_repo,
        }

        for entity_type, natural_key, new_status in diff.to_prune:
            try:
                repo = repo_map.get(entity_type)
                if not repo:
                    self._log.warning(
                        "entity.prune_unsupported",
                        entity_type=entity_type,
                        natural_key=natural_key,
                    )
                    continue

                # Type ignore: repo_map contains different repository types
                existing = repo.find_by_natural_key(  # type: ignore[union-attr]
                    *self._parse_natural_key(entity_type, natural_key)  # type: ignore[arg-type]
                )
                if existing:
                    netbox_id = getattr(existing, "id", None)  # type: ignore[arg-type]
                    if netbox_id:
                        repo.delete(netbox_id)  # type: ignore[union-attr]
                        self._log.info(
                            "entity.pruned",
                            entity_type=entity_type,
                            natural_key=natural_key,
                            new_status=new_status,
                            netbox_id=netbox_id,
                        )
                        self._event_log.record(
                            EntityPruned(
                                entity_type=entity_type,
                                natural_key=natural_key,
                                new_status=new_status,
                            )
                        )
                    else:
                        self._log.warning(
                            "entity.prune_no_id",
                            entity_type=entity_type,
                            natural_key=natural_key,
                        )
                else:
                    self._log.warning(
                        "entity.prune_not_found",
                        entity_type=entity_type,
                        natural_key=natural_key,
                    )

            except Exception as exc:
                self._log.warning(
                    "entity.prune_failed",
                    entity_type=entity_type,
                    natural_key=natural_key,
                    error=str(exc),
                )
                self._event_log.record(
                    SyncError(
                        entity_type=entity_type,
                        natural_key=natural_key,
                        error_message=str(exc),
                        exception_type=type(exc).__name__,
                    )
                )

    def _parse_natural_key(self, entity_type: str, natural_key: str) -> tuple[str, ...]:
        parts = natural_key.split(":")
        if entity_type == "site":
            return (parts[1],)
        elif entity_type == "cluster":
            return (parts[1], parts[2])
        elif entity_type == "device":
            return (parts[1], parts[2])
        elif entity_type == "interface":
            return (parts[1], parts[2])
        elif entity_type == "ip_address":
            return (parts[1], parts[2], parts[3])
        elif entity_type == "vlan":
            return (parts[1], str(int(parts[2])))
        elif entity_type == "inventory_item":
            return (parts[1], parts[2], parts[3])
        return (natural_key,)
