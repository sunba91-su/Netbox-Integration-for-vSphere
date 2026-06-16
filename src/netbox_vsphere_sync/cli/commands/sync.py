from __future__ import annotations

import click

from netbox_vsphere_sync.application.bootstrapper import Bootstrapper
from netbox_vsphere_sync.application.dependency_resolver import DependencyResolver
from netbox_vsphere_sync.application.diff_engine import DiffEngine
from netbox_vsphere_sync.application.event_log import EventLog
from netbox_vsphere_sync.application.sync_engine import SyncEngine
from netbox_vsphere_sync.infrastructure.config.loader import ConfigLoader
from netbox_vsphere_sync.infrastructure.config.lock_manager import PidLockManager
from netbox_vsphere_sync.infrastructure.config.secret_resolver import SecretResolver
from netbox_vsphere_sync.infrastructure.netbox.acl import NetBoxACL
from netbox_vsphere_sync.infrastructure.netbox.client import NetBoxClient
from netbox_vsphere_sync.infrastructure.netbox.repositories.bootstrap_repository import (
    NetBoxBootstrapRepository,
)
from netbox_vsphere_sync.infrastructure.netbox.repositories.cluster_repository import (
    NetBoxClusterRepository,
)
from netbox_vsphere_sync.infrastructure.netbox.repositories.device_repository import (
    NetBoxDeviceRepository,
)
from netbox_vsphere_sync.infrastructure.netbox.repositories.interface_repository import (
    NetBoxInterfaceRepository,
)
from netbox_vsphere_sync.infrastructure.netbox.repositories.inventory_item_repository import (
    NetBoxInventoryItemRepository,
)
from netbox_vsphere_sync.infrastructure.netbox.repositories.ip_address_repository import (
    NetBoxIpAddressRepository,
)
from netbox_vsphere_sync.infrastructure.netbox.repositories.site_repository import (
    NetBoxSiteRepository,
)
from netbox_vsphere_sync.infrastructure.netbox.repositories.vlan_repository import (
    NetBoxVlanRepository,
)
from netbox_vsphere_sync.infrastructure.vault.client import VaultClient
from netbox_vsphere_sync.infrastructure.vsphere.acl import VSphereACL
from netbox_vsphere_sync.infrastructure.vsphere.client import VSphereClient
from netbox_vsphere_sync.infrastructure.vsphere.collector import VSphereCollector
from netbox_vsphere_sync.report.console import ConsoleReporter
from netbox_vsphere_sync.report.logging_config import configure_logging


@click.command(name="sync")
@click.option(
    "--config",
    "-c",
    required=True,
    envvar="NVS_CONFIG",
    help="Path to YAML config file",
)
@click.option("--dry-run", is_flag=True, help="Preview changes without writing")
@click.option("--prune", is_flag=True, help="Deactivate orphaned objects")
@click.option(
    "--vcenter-username",
    envvar="NVS_VCENTER_USERNAME",
    help="vCenter username",
)
@click.option(
    "--vcenter-password",
    envvar="NVS_VCENTER_PASSWORD",
    help="vCenter password",
)
@click.option(
    "--netbox-token",
    envvar="NVS_NETBOX_TOKEN",
    help="NetBox API token",
)
@click.option("--vcenter-insecure", is_flag=True, help="Disable vCenter TLS verification")
@click.option("--netbox-insecure", is_flag=True, help="Disable NetBox TLS verification")
@click.option("--verbose", is_flag=True, help="Enable debug logging")
@click.option(
    "--log-format",
    type=click.Choice(["console", "json"]),
    default="console",
    help="Log output format (default: console)",
)
def sync_command(
    config: str,
    dry_run: bool,
    prune: bool,
    vcenter_username: str | None,
    vcenter_password: str | None,
    netbox_token: str | None,
    vcenter_insecure: bool,
    netbox_insecure: bool,
    verbose: bool,
    log_format: str,
) -> None:
    configure_logging(
        log_level="DEBUG" if verbose else None,
        log_format=log_format,  # type: ignore[arg-type]
    )
    event_log = EventLog()

    try:
        config_loader = ConfigLoader(config)
        app_config = config_loader.load()

        if dry_run:
            app_config.sync.dry_run = True
        if prune:
            app_config.sync.prune = True

        vault_client: VaultClient | None = None
        if app_config.vault.enabled:
            vault_client = VaultClient(app_config.vault)
            vault_client.connect()

        secret_resolver = SecretResolver(app_config, vault_client)

        vcenter_overrides: dict[str, str] = {}
        if vcenter_username:
            vcenter_overrides["username"] = vcenter_username
        if vcenter_password:
            vcenter_overrides["password"] = vcenter_password
        vcenter_config = secret_resolver.resolve_vcenter(vcenter_overrides)

        netbox_overrides: dict[str, str] = {}
        if netbox_token:
            netbox_overrides["token"] = netbox_token
        netbox_config = secret_resolver.resolve_netbox(netbox_overrides)

        if vcenter_insecure:
            vcenter_config.verify_ssl = False
        if netbox_insecure:
            netbox_config.verify_ssl = False

        vsphere_client = VSphereClient(vcenter_config)
        vsphere_client.connect()

        netbox_client = NetBoxClient(netbox_config)
        netbox_client.connect()

        vsphere_acl = VSphereACL()
        netbox_acl = NetBoxACL()

        collector = VSphereCollector(
            client=vsphere_client,
            acl=vsphere_acl,
            vcenter_host=vcenter_config.host,
        )

        site_repo = NetBoxSiteRepository(netbox_client, netbox_acl)
        cluster_repo = NetBoxClusterRepository(netbox_client, netbox_acl)
        device_repo = NetBoxDeviceRepository(netbox_client, netbox_acl)
        interface_repo = NetBoxInterfaceRepository(netbox_client, netbox_acl)
        ip_repo = NetBoxIpAddressRepository(netbox_client, netbox_acl)
        vlan_repo = NetBoxVlanRepository(netbox_client, netbox_acl)
        inventory_repo = NetBoxInventoryItemRepository(netbox_client, netbox_acl)

        bootstrap_repo = NetBoxBootstrapRepository(netbox_client)
        bootstrapper = Bootstrapper(bootstrap_repo, app_config.bootstrap, event_log)

        lock_manager = PidLockManager()
        diff_engine = DiffEngine()
        dependency_resolver = DependencyResolver()

        engine = SyncEngine(
            collector=collector,
            site_repo=site_repo,
            cluster_repo=cluster_repo,
            device_repo=device_repo,
            interface_repo=interface_repo,
            ip_repo=ip_repo,
            vlan_repo=vlan_repo,
            inventory_repo=inventory_repo,
            bootstrapper=bootstrapper,
            lock_manager=lock_manager,
            diff_engine=diff_engine,
            dependency_resolver=dependency_resolver,
            event_log=event_log,
            config=app_config.sync,
        )

        exit_code = engine.run()

        reporter = ConsoleReporter(event_log)
        reporter.render()

        if exit_code != 0:
            click.secho(f"Sync completed with exit code {exit_code}", fg="red")

    except Exception as exc:
        click.secho(f"Fatal error: {exc}", fg="red", err=True)
        raise SystemExit(2) from exc
