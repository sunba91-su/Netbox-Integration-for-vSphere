from __future__ import annotations

from netbox_vsphere_sync.domain.model.vsphere import Cluster
from netbox_vsphere_sync.domain.ports import ClusterRepository
from netbox_vsphere_sync.infrastructure.netbox.acl import NetBoxACL
from netbox_vsphere_sync.infrastructure.netbox.client import NetBoxClient

ENDPOINT = "dcim.clusters"


class NetBoxClusterRepository(ClusterRepository):
    def __init__(self, client: NetBoxClient, acl: NetBoxACL) -> None:
        self._client = client
        self._acl = acl

    def list_all(self) -> list[Cluster]:
        data_list = self._client.list_all(ENDPOINT)
        return [self._acl.to_cluster(d) for d in data_list if d.get("name")]

    def find_by_natural_key(self, site: str, name: str) -> Cluster | None:
        data = self._client.get_by_field(ENDPOINT, "name", name)
        if data:
            return self._acl.to_cluster(data)
        return None

    def create(self, cluster: Cluster) -> Cluster:
        payload = self._acl.to_netbox_cluster(cluster, cluster_type_id=0, site_id=0)
        data = self._client.create(ENDPOINT, payload)
        return self._acl.to_cluster(data)

    def update(self, cluster: Cluster) -> Cluster:
        existing = self.find_by_natural_key(cluster.site, cluster.name)
        if not existing:
            return self.create(cluster)
        payload = self._acl.to_netbox_cluster(cluster, cluster_type_id=0, site_id=0)
        data = self._client.update(ENDPOINT, getattr(existing, "id", 0), payload)
        return self._acl.to_cluster(data)
