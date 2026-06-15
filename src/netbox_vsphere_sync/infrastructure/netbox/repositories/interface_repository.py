from __future__ import annotations

from netbox_vsphere_sync.domain.model.vsphere import Interface
from netbox_vsphere_sync.domain.ports import InterfaceRepository
from netbox_vsphere_sync.infrastructure.netbox.acl import NetBoxACL
from netbox_vsphere_sync.infrastructure.netbox.client import NetBoxClient

ENDPOINT = "dcim.interfaces"


class NetBoxInterfaceRepository(InterfaceRepository):
    def __init__(self, client: NetBoxClient, acl: NetBoxACL) -> None:
        self._client = client
        self._acl = acl

    def list_all(self) -> list[Interface]:
        data_list = self._client.list_all(ENDPOINT)
        return [self._acl.to_interface(d) for d in data_list if d.get("name")]

    def find_by_natural_key(self, device: str, name: str) -> Interface | None:
        data = self._client.get_by_field(ENDPOINT, "name", name)
        if data:
            return self._acl.to_interface(data)
        return None

    def create(self, interface: Interface) -> Interface:
        payload = self._acl.to_netbox_interface(interface, device_id=0)
        data = self._client.create(ENDPOINT, payload)
        return self._acl.to_interface(data)

    def update(self, interface: Interface) -> Interface:
        existing = self.find_by_natural_key(interface.device, interface.name)
        if not existing:
            return self.create(interface)
        payload = self._acl.to_netbox_interface(interface, device_id=0)
        data = self._client.update(ENDPOINT, getattr(existing, "id", 0), payload)
        return self._acl.to_interface(data)
