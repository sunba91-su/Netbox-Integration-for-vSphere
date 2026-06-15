from __future__ import annotations

from netbox_vsphere_sync.domain.model.vsphere import (
    Cluster,
    Datastore,
    HostSystem,
    Interface,
    IpAddress,
    Site,
    Vlan,
)


class NetBoxACL:
    def to_site(self, data: dict) -> Site:
        return Site(
            name=data.get("name", ""),
            description=data.get("description", "") or "",
            facility=data.get("facility", "") or "",
            physical_address=data.get("physical_address", "") or "",
            custom_fields=self._custom_fields(data),
        )

    def to_cluster(self, data: dict) -> Cluster:
        site_name = ""
        if data.get("site"):
            site_data = data["site"]
            site_name = site_data if isinstance(site_data, str) else site_data.get("name", "")

        return Cluster(
            name=data.get("name", ""),
            site=site_name,
            datacenter_name=self._cf(data, "nvs_datacenter"),
            ha_enabled=False,
            drs_enabled=False,
            custom_fields=self._custom_fields(data),
        )

    def to_host(self, data: dict) -> HostSystem:
        site_name = ""
        if data.get("site"):
            site_data = data["site"]
            site_name = site_data if isinstance(site_data, str) else site_data.get("name", "")

        cluster_name = None
        if data.get("cluster"):
            cluster_data = data["cluster"]
            cluster_name = (
                cluster_data if isinstance(cluster_data, str) else cluster_data.get("name", "")
            )

        return HostSystem(
            name=data.get("name", ""),
            site=site_name,
            cluster=cluster_name,
            bios_uuid=self._cf(data, "nvs_bios_uuid"),
            esxi_version=self._cf(data, "nvs_esxi_version"),
            power_state=self._cf(data, "nvs_power_state"),
            connection_state=self._cf(data, "nvs_connection_state"),
            vcenter_host=self._cf(data, "nvs_vcenter"),
            maintenance_mode=data.get("status", "") == "offline",
            custom_fields=self._custom_fields(data),
        )

    def to_interface(self, data: dict) -> Interface:
        device_name = ""
        if data.get("device"):
            device_data = data["device"]
            device_name = (
                device_data if isinstance(device_data, str) else device_data.get("name", "")
            )

        return Interface(
            name=data.get("name", ""),
            device=device_name,
            enabled=data.get("enabled", True),
            mtu=data.get("mtu", 1500) or 1500,
            mac_address=data.get("mac_address", "") or "",
            description=data.get("description", "") or "",
            custom_fields=self._custom_fields(data),
        )

    def to_ip_address(self, data: dict) -> IpAddress:
        address = data.get("address", "")
        interface_name = ""
        device_name = ""

        if data.get("assigned_object"):
            assigned = data["assigned_object"]
            interface_name = assigned.get("name", "")
            if assigned.get("device"):
                device_data = assigned["device"]
                device_name = (
                    device_data if isinstance(device_data, str) else device_data.get("name", "")
                )

        prefix = 32
        if "/" in address:
            prefix = int(address.split("/")[1])

        return IpAddress(
            address=address.split("/")[0] if "/" in address else address,
            prefix_length=prefix,
            interface=interface_name,
            device=device_name,
            role=data.get("role", None),
            dns_name=data.get("dns_name", "") or "",
            description=data.get("description", "") or "",
        )

    def to_vlan(self, data: dict) -> Vlan:
        site_name = ""
        if data.get("site"):
            site_data = data["site"]
            site_name = site_data if isinstance(site_data, str) else site_data.get("name", "")

        return Vlan(
            vid=data.get("vid", 0),
            name=data.get("name", "") or "",
            site=site_name,
            status=(
                data.get("status", {}).get("value", "active")
                if isinstance(data.get("status"), dict)
                else "active"
            ),
            description=data.get("description", "") or "",
            custom_fields=self._custom_fields(data),
        )

    def to_inventory_item(self, data: dict) -> Datastore:
        device_name = ""
        if data.get("device"):
            device_data = data["device"]
            device_name = (
                device_data if isinstance(device_data, str) else device_data.get("name", "")
            )

        return Datastore(
            name=data.get("name", ""),
            device=device_name,
            role=(
                data.get("role", {}).get("name", "Storage")
                if isinstance(data.get("role"), dict)
                else "Storage"
            ),
            description=data.get("description", "") or "",
            custom_fields=self._custom_fields(data),
        )

    def to_netbox_site(self, site: Site) -> dict:
        result: dict = {
            "name": site.name,
            "description": site.description,
            "facility": site.facility,
            "physical_address": site.physical_address,
        }
        if site.custom_fields:
            result["custom_fields"] = site.custom_fields
        return self._clean(result)

    def to_netbox_cluster(
        self, cluster: Cluster, cluster_type_id: int, site_id: int | None
    ) -> dict:
        result: dict = {
            "name": cluster.name,
            "cluster_type": cluster_type_id,
        }
        if site_id:
            result["site"] = site_id
        if cluster.custom_fields:
            result["custom_fields"] = cluster.custom_fields
        return self._clean(result)

    def to_netbox_device(
        self,
        device: HostSystem,
        site_id: int,
        role_id: int,
        manufacturer_id: int,
        cluster_id: int | None = None,
    ) -> dict:
        status = "offline" if device.maintenance_mode else "active"
        result: dict = {
            "name": device.name,
            "site": site_id,
            "device_role": role_id,
            "manufacturer": manufacturer_id,
            "status": status,
            "serial": device.hardware.serial if device.hardware else "",
            "asset_tag": device.bios_uuid or None,
        }
        if cluster_id:
            result["cluster"] = cluster_id
        if device.custom_fields:
            result["custom_fields"] = device.custom_fields
        return self._clean(result)

    def to_netbox_interface(self, interface: Interface, device_id: int) -> dict:
        result: dict = {
            "name": interface.name,
            "device": device_id,
            "enabled": interface.enabled,
            "mtu": interface.mtu,
            "type": interface.interface_type,
        }
        if interface.mac_address:
            result["mac_address"] = interface.mac_address
        if interface.description:
            result["description"] = interface.description
        if interface.custom_fields:
            result["custom_fields"] = interface.custom_fields
        return self._clean(result)

    def to_netbox_ip_address(self, ip: IpAddress, interface_id: int) -> dict:
        result: dict = {
            "address": f"{ip.address}/{ip.prefix_length}",
            "assigned_object_id": interface_id,
            "assigned_object_type": "dcim.interface",
        }
        if ip.role:
            result["role"] = ip.role
        if ip.dns_name:
            result["dns_name"] = ip.dns_name
        if ip.description:
            result["description"] = ip.description
        return self._clean(result)

    def to_netbox_vlan(self, vlan: Vlan, site_id: int | None = None) -> dict:
        result: dict = {
            "vid": vlan.vid,
            "name": vlan.name or f"VLAN{vlan.vid}",
            "status": vlan.status,
        }
        if site_id:
            result["site"] = site_id
        return self._clean(result)

    def to_netbox_inventory_item(
        self, item: Datastore, device_id: int, role_id: int | None = None
    ) -> dict:
        result: dict = {
            "name": item.name,
            "device": device_id,
            "description": item.description,
        }
        if role_id:
            result["role"] = role_id
        if item.custom_fields:
            result["custom_fields"] = item.custom_fields
        return self._clean(result)

    def _cf(self, data: dict, key: str) -> str:
        cfs = data.get("custom_fields", {}) or {}
        return str(cfs.get(key, "")) if cfs else ""

    def _custom_fields(self, data: dict) -> dict[str, str]:
        cfs = data.get("custom_fields", {}) or {}
        return {str(k): str(v) for k, v in cfs.items()}

    def _clean(self, data: dict) -> dict:
        return {k: v for k, v in data.items() if v is not None and v != ""}
