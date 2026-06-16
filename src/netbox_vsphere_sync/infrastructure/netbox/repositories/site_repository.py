from __future__ import annotations

from netbox_vsphere_sync.domain.model.vsphere import Site
from netbox_vsphere_sync.domain.ports import SiteRepository
from netbox_vsphere_sync.infrastructure.netbox.acl import NetBoxACL
from netbox_vsphere_sync.infrastructure.netbox.client import NetBoxClient

ENDPOINT = "dcim.sites"


class NetBoxSiteRepository(SiteRepository):
    def __init__(self, client: NetBoxClient, acl: NetBoxACL) -> None:
        self._client = client
        self._acl = acl

    def list_all(self) -> list[Site]:
        data_list = self._client.list_all(ENDPOINT, brief=True, exclude_config_context=True)
        return [self._acl.to_site(d) for d in data_list if d.get("name")]

    def find_by_name(self, name: str) -> Site | None:
        data = self._client.get_by_field(
            ENDPOINT, "name", name, brief=True, exclude_config_context=True
        )
        if data:
            return self._acl.to_site(data)
        return None

    def create(self, site: Site) -> Site:
        payload = self._acl.to_netbox_site(site)
        data = self._client.create(ENDPOINT, payload)
        return self._acl.to_site(data)

    def update(self, site: Site) -> Site:
        existing = self.find_by_name(site.name)
        if not existing:
            return self.create(site)
        payload = self._acl.to_netbox_site(site)
        data = self._client.update(ENDPOINT, getattr(existing, "id", 0), payload)
        return self._acl.to_site(data)
