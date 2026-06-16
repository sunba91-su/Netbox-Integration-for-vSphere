from __future__ import annotations

from netbox_vsphere_sync.domain.model.vsphere import IpAddress
from netbox_vsphere_sync.domain.ports import IpAddressRepository
from netbox_vsphere_sync.infrastructure.netbox.acl import NetBoxACL
from netbox_vsphere_sync.infrastructure.netbox.client import NetBoxClient

ENDPOINT = "ipam.ip_addresses"


class NetBoxIpAddressRepository(IpAddressRepository):
    def __init__(self, client: NetBoxClient, acl: NetBoxACL) -> None:
        self._client = client
        self._acl = acl

    def list_all(self) -> list[IpAddress]:
        data_list = self._client.list_all(ENDPOINT, brief=True, exclude_config_context=True)
        return [self._acl.to_ip_address(d) for d in data_list if d.get("address")]

    def find_by_natural_key(self, address: str, device: str, interface: str) -> IpAddress | None:
        data = self._client.get_by_field(
            ENDPOINT, "address", address, brief=True, exclude_config_context=True
        )
        if data:
            return self._acl.to_ip_address(data)
        return None

    def create(self, ip_address: IpAddress) -> IpAddress:
        payload = self._acl.to_netbox_ip_address(ip_address, interface_id=0)
        data = self._client.create(ENDPOINT, payload)
        return self._acl.to_ip_address(data)

    def update(self, ip_address: IpAddress) -> IpAddress:
        existing = self.find_by_natural_key(
            ip_address.address, ip_address.device, ip_address.interface
        )
        if not existing:
            return self.create(ip_address)
        payload = self._acl.to_netbox_ip_address(ip_address, interface_id=0)
        data = self._client.update(ENDPOINT, getattr(existing, "id", 0), payload)
        return self._acl.to_ip_address(data)
