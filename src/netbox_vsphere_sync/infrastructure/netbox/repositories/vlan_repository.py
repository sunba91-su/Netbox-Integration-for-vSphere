from __future__ import annotations

from netbox_vsphere_sync.domain.model.vsphere import Vlan
from netbox_vsphere_sync.domain.ports import VlanRepository
from netbox_vsphere_sync.infrastructure.netbox.acl import NetBoxACL
from netbox_vsphere_sync.infrastructure.netbox.client import NetBoxClient

ENDPOINT = "ipam.vlans"


class NetBoxVlanRepository(VlanRepository):
    def __init__(self, client: NetBoxClient, acl: NetBoxACL) -> None:
        self._client = client
        self._acl = acl

    def list_all(self) -> list[Vlan]:
        data_list = self._client.list_all(ENDPOINT)
        return [self._acl.to_vlan(d) for d in data_list if d.get("vid")]

    def find_by_natural_key(self, site: str, vid: int) -> Vlan | None:
        data = self._client.get_by_field(ENDPOINT, "vid", vid)
        if data:
            return self._acl.to_vlan(data)
        return None

    def create(self, vlan: Vlan) -> Vlan:
        payload = self._acl.to_netbox_vlan(vlan)
        data = self._client.create(ENDPOINT, payload)
        return self._acl.to_vlan(data)

    def update(self, vlan: Vlan) -> Vlan:
        existing = self.find_by_natural_key(vlan.site, vlan.vid)
        if not existing:
            return self.create(vlan)
        payload = self._acl.to_netbox_vlan(vlan)
        data = self._client.update(ENDPOINT, getattr(existing, "id", 0), payload)
        return self._acl.to_vlan(data)
