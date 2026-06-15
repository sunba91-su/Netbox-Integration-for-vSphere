from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from netbox_vsphere_sync.application.bootstrapper import Bootstrapper
from netbox_vsphere_sync.application.dependency_resolver import DependencyResolver
from netbox_vsphere_sync.application.diff_engine import DiffEngine
from netbox_vsphere_sync.application.event_log import EventLog
from netbox_vsphere_sync.application.sync_engine import SyncEngine
from netbox_vsphere_sync.domain.model.config import (
    AppConfig,
    BootstrapConfig,
    NetBoxConfig,
    SyncConfig,
    VCenterConfig,
)


@pytest.fixture
def event_log() -> EventLog:
    return EventLog()


@pytest.fixture
def diff_engine() -> DiffEngine:
    return DiffEngine()


@pytest.fixture
def dependency_resolver() -> DependencyResolver:
    return DependencyResolver()


@pytest.fixture
def sync_config() -> SyncConfig:
    return SyncConfig(dry_run=True, prune=False)


@pytest.fixture
def bootstrap_config() -> BootstrapConfig:
    return BootstrapConfig(enabled=False)


@pytest.fixture
def vcenter_config() -> VCenterConfig:
    return VCenterConfig(
        host="vcenter.example.com",
        username="admin",
        password="password",
    )


@pytest.fixture
def netbox_config() -> NetBoxConfig:
    return NetBoxConfig(
        url="https://netbox.example.com",
        token="abc123",
    )


@pytest.fixture
def app_config(vcenter_config: VCenterConfig, netbox_config: NetBoxConfig) -> AppConfig:
    return AppConfig(
        vcenter=vcenter_config,
        netbox=netbox_config,
    )


@pytest.fixture
def mock_collector() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_site_repo() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_cluster_repo() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_device_repo() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_interface_repo() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_ip_repo() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_vlan_repo() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_inventory_repo() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_lock_manager() -> MagicMock:
    lock = MagicMock()
    lock.acquire.return_value = True
    return lock


@pytest.fixture
def mock_bootstrap() -> MagicMock:
    return MagicMock()


@pytest.fixture
def sync_engine(
    mock_collector: MagicMock,
    mock_site_repo: MagicMock,
    mock_cluster_repo: MagicMock,
    mock_device_repo: MagicMock,
    mock_interface_repo: MagicMock,
    mock_ip_repo: MagicMock,
    mock_vlan_repo: MagicMock,
    mock_inventory_repo: MagicMock,
    mock_lock_manager: MagicMock,
    mock_bootstrap: MagicMock,
    diff_engine: DiffEngine,
    dependency_resolver: DependencyResolver,
    event_log: EventLog,
    sync_config: SyncConfig,
    bootstrap_config: BootstrapConfig,
) -> SyncEngine:
    bootstrapper = Bootstrapper(mock_bootstrap, bootstrap_config, event_log)
    return SyncEngine(
        collector=mock_collector,
        site_repo=mock_site_repo,
        cluster_repo=mock_cluster_repo,
        device_repo=mock_device_repo,
        interface_repo=mock_interface_repo,
        ip_repo=mock_ip_repo,
        vlan_repo=mock_vlan_repo,
        inventory_repo=mock_inventory_repo,
        bootstrapper=bootstrapper,
        lock_manager=mock_lock_manager,
        diff_engine=diff_engine,
        dependency_resolver=dependency_resolver,
        event_log=event_log,
        config=sync_config,
    )
