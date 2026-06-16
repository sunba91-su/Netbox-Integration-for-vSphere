from __future__ import annotations

from netbox_vsphere_sync.domain.model.vsphere import Datastore
from netbox_vsphere_sync.domain.ports import InventoryItemRepository
from netbox_vsphere_sync.infrastructure.netbox.acl import NetBoxACL
from netbox_vsphere_sync.infrastructure.netbox.client import NetBoxClient

ENDPOINT = "dcim.inventory_items"


class NetBoxInventoryItemRepository(InventoryItemRepository):
    def __init__(self, client: NetBoxClient, acl: NetBoxACL) -> None:
        self._client = client
        self._acl = acl

    def list_all(self) -> list[Datastore]:
        data_list = self._client.list_all(ENDPOINT, brief=True, exclude_config_context=True)
        return [self._acl.to_inventory_item(d) for d in data_list if d.get("name")]

    def find_by_natural_key(self, device: str, name: str, role: str) -> Datastore | None:
        data = self._client.get_by_field(
            ENDPOINT, "name", name, brief=True, exclude_config_context=True
        )
        if data:
            return self._acl.to_inventory_item(data)
        return None

    def create(self, item: Datastore) -> Datastore:
        payload = self._acl.to_netbox_inventory_item(item, device_id=0)
        data = self._client.create(ENDPOINT, payload)
        return self._acl.to_inventory_item(data)

    def update(self, item: Datastore) -> Datastore:
        existing = self.find_by_natural_key(item.device, item.name, item.role)
        if not existing:
            return self.create(item)
        payload = self._acl.to_netbox_inventory_item(item, device_id=0)
        data = self._client.update(ENDPOINT, getattr(existing, "id", 0), payload)
        return self._acl.to_inventory_item(data)

    def delete(self, netbox_id: int) -> bool:
        return self._client.delete(ENDPOINT, netbox_id)
