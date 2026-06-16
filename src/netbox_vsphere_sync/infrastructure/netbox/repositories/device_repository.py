from __future__ import annotations

from netbox_vsphere_sync.domain.model.vsphere import HostSystem
from netbox_vsphere_sync.domain.ports import DeviceRepository
from netbox_vsphere_sync.infrastructure.netbox.acl import NetBoxACL
from netbox_vsphere_sync.infrastructure.netbox.client import NetBoxClient

ENDPOINT = "dcim.devices"


class NetBoxDeviceRepository(DeviceRepository):
    def __init__(self, client: NetBoxClient, acl: NetBoxACL) -> None:
        self._client = client
        self._acl = acl

    def list_all(self) -> list[HostSystem]:
        data_list = self._client.list_all(ENDPOINT, brief=True, exclude_config_context=True)
        return [self._acl.to_host(d) for d in data_list if d.get("name")]

    def find_by_natural_key(self, site: str, name: str) -> HostSystem | None:
        data = self._client.get_by_field(
            ENDPOINT, "name", name, brief=True, exclude_config_context=True
        )
        if data:
            return self._acl.to_host(data)
        return None

    def create(self, device: HostSystem) -> HostSystem:
        payload = self._acl.to_netbox_device(device, site_id=0, role_id=0, manufacturer_id=0)
        data = self._client.create(ENDPOINT, payload)
        return self._acl.to_host(data)

    def update(self, device: HostSystem) -> HostSystem:
        existing = self.find_by_natural_key(device.site, device.name)
        if not existing:
            return self.create(device)
        payload = self._acl.to_netbox_device(device, site_id=0, role_id=0, manufacturer_id=0)
        data = self._client.update(ENDPOINT, getattr(existing, "id", 0), payload)
        return self._acl.to_host(data)

    def delete(self, netbox_id: int) -> bool:
        return self._client.delete(ENDPOINT, netbox_id)
