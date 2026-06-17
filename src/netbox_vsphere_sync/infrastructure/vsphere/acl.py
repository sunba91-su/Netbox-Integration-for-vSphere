from __future__ import annotations

from pyVmomi import vim

from netbox_vsphere_sync.domain.model.vsphere import (
    Cluster,
    Datastore,
    HostHardware,
    HostSystem,
    Interface,
    IpAddress,
    PortGroup,
    Site,
    VSphereMOR,
)


class VSphereACL:
    def to_site(self, dc: vim.Datacenter) -> Site:
        mor = self._mor(dc)
        name = dc.name
        description = ""
        facility = ""
        location = ""

        if dc.vmFolder and dc.vmFolder.childEntity:
            pass

        return Site(
            name=name,
            description=description,
            facility=facility,
            physical_address=location,
            mor=mor,
            custom_fields={"nvs_vsphere_mor": mor.value if mor else ""},
        )

    def to_cluster(self, cluster: vim.ClusterComputeResource, dc_name: str) -> Cluster:
        mor = self._mor(cluster)
        return Cluster(
            name=cluster.name,
            site=dc_name,
            mor=mor,
            datacenter_name=dc_name,
            ha_enabled=bool(cluster.configuration.dasConfig.enabled)
            if cluster.configuration.dasConfig
            else False,
            drs_enabled=bool(cluster.configuration.drsConfig.enabled)
            if cluster.configuration.drsConfig
            else False,
            custom_fields={"nvs_vsphere_mor": mor.value if mor else ""},
        )

    def to_host(
        self,
        host: vim.HostSystem,
        site_name: str,
        cluster_name: str | None,
        vcenter_host: str,
    ) -> HostSystem:
        mor = self._mor(host)
        hardware = self._host_hardware(host)
        summary = host.summary

        return HostSystem(
            name=host.name,
            site=site_name,
            cluster=cluster_name,
            mor=mor,
            hardware=hardware,
            bios_uuid=summary.hardware.uuid or "",
            esxi_version=summary.config.product.version or "",
            power_state=str(host.runtime.powerState),
            connection_state=str(host.runtime.connectionState),
            vcenter_host=vcenter_host,
            maintenance_mode=bool(host.runtime.inMaintenanceMode),
            custom_fields={
                "nvs_vsphere_mor": mor.value if mor else "",
                "nvs_bios_uuid": summary.hardware.uuid or "",
                "nvs_esxi_version": summary.config.product.version or "",
                "nvs_power_state": str(host.runtime.powerState),
                "nvs_connection_state": str(host.runtime.connectionState),
                "nvs_vcenter": vcenter_host,
            },
        )

    def to_port_group(self, pg: vim.dvs.DistributedVirtualPortgroup) -> PortGroup:
        mor = self._mor(pg)
        vlan_id: int | None = None
        try:
            vlan_id = pg.config.defaultPortConfig.vlan.vlanId
        except Exception:
            pass

        return PortGroup(
            name=pg.name,
            vlan_id=vlan_id,
            switch_type="distributed",
            switch_name=pg.config.distributedVirtualSwitch.name,
            mor=mor,
            hosts=[],
        )

    def to_standard_port_group(self, pg: vim.host.PortGroup, host_name: str) -> PortGroup:
        vlan_id: int | None = pg.spec.vlanId if pg.spec.vlanId else None
        return PortGroup(
            name=pg.spec.name,
            vlan_id=vlan_id,
            switch_type="standard",
            switch_name=pg.spec.name,
            hosts=[host_name],
        )

    def to_datastore(self, ds: vim.Datastore, host_name: str) -> Datastore:
        mor = self._mor(ds)
        capacity = int(ds.summary.capacity) if ds.summary.capacity else 0
        free = int(ds.summary.freeSpace) if ds.summary.freeSpace else 0
        ds_type = str(ds.summary.type) if ds.summary.type else "vmfs"

        return Datastore(
            name=ds.name,
            device=host_name,
            capacity_bytes=capacity,
            free_bytes=free,
            datastore_type=ds_type,
            role="Storage",
            mor=mor,
            description=f"Capacity: {self._human_size(capacity)}, "
            f"Free: {self._human_size(free)}, Type: {ds_type}",
            custom_fields={
                "nvs_vsphere_mor": mor.value if mor else "",
            },
        )

    def to_interface(
        self,
        name: str,
        device_name: str,
        mac: str,
        mtu: int,
        enabled: bool,
    ) -> Interface:
        return Interface(
            name=name,
            device=device_name,
            enabled=enabled,
            mtu=mtu,
            mac_address=mac or "",
        )

    def to_ip_address(
        self,
        address: str,
        prefix: int,
        interface_name: str,
        device_name: str,
        role: str | None = None,
    ) -> IpAddress:
        return IpAddress(
            address=address,
            prefix_length=prefix,
            interface=interface_name,
            device=device_name,
            role=role,
        )

    def _host_hardware(self, host: vim.HostSystem) -> HostHardware | None:
        hardware = host.hardware
        if not hardware:
            return None
        cpu_info = hardware.cpuInfo
        sys_info = hardware.systemInfo
        return HostHardware(
            cpu_model=getattr(cpu_info, "cpuModel", getattr(cpu_info, "model", "")) or "",
            cpu_cores=getattr(cpu_info, "numCpuCores", 0) or 0,
            cpu_sockets=getattr(cpu_info, "numCpuPkgs", 0) or 0,
            memory_gb=float(getattr(hardware, "memorySize", 0) or 0) / (1024**3),
            model=getattr(sys_info, "model", "") or "",
            serial=getattr(sys_info, "serialNumber", "") or "",
        )

    def _mor(self, obj: object) -> VSphereMOR | None:
        if hasattr(obj, "_moId") and hasattr(obj, "__class__"):
            return VSphereMOR(
                value=obj._moId,  # type: ignore[union-attr]
                type=obj.__class__.__name__,  # type: ignore[union-attr]
            )
        return None

    def _human_size(self, bytes_val: int) -> str:
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if bytes_val < 1024:
                return f"{bytes_val:.1f} {unit}"
            bytes_val /= 1024
        return f"{bytes_val:.1f} PB"
