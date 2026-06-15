from __future__ import annotations

from pyVmomi import vim

from netbox_vsphere_sync.domain.model.vsphere import (
    Cluster,
    Datastore,
    HostSystem,
    PortGroup,
    Site,
)
from netbox_vsphere_sync.domain.ports import VSphereCollector as VSphereCollectorPort
from netbox_vsphere_sync.infrastructure.vsphere.acl import VSphereACL
from netbox_vsphere_sync.infrastructure.vsphere.client import VSphereClient


class VSphereCollector(VSphereCollectorPort):
    def __init__(
        self,
        client: VSphereClient,
        acl: VSphereACL,
        vcenter_host: str,
    ) -> None:
        self._client = client
        self._acl = acl
        self._vcenter_host = vcenter_host

    def collect_sites(self) -> list[Site]:
        sites: list[Site] = []
        for dc in self._client.datacenters:
            site = self._acl.to_site(dc)
            sites.append(site)
        return sites

    def collect_clusters(self) -> list[Cluster]:
        clusters: list[Cluster] = []
        for dc in self._client.datacenters:
            dc_name = dc.name
            folder = dc.hostFolder
            cluster_refs = self._collect_objects(folder, vim.ClusterComputeResource)
            for cluster in cluster_refs:
                clusters.append(self._acl.to_cluster(cluster, dc_name))
        return clusters

    def collect_hosts(self) -> list[HostSystem]:
        hosts: list[HostSystem] = []
        for dc in self._client.datacenters:
            dc_name = dc.name
            folder = dc.hostFolder
            compute_refs = self._collect_objects(folder, vim.ClusterComputeResource)
            for compute in compute_refs:
                cluster_name = compute.name
                for host in compute.host:
                    hosts.append(self._acl.to_host(host, dc_name, cluster_name, self._vcenter_host))
        return hosts

    def collect_port_groups(self) -> list[PortGroup]:
        port_groups: list[PortGroup] = []
        for dc in self._client.datacenters:
            dvs_folder = dc.networkFolder
            dv_pgs = self._collect_objects(dvs_folder, vim.dvs.DistributedVirtualPortgroup)
            for pg in dv_pgs:
                port_groups.append(self._acl.to_port_group(pg))

            for host in self._collect_hosts_in_dc(dc):
                if host.config and host.config.network:
                    for pg in host.config.network.portgroup:
                        port_groups.append(self._acl.to_standard_port_group(pg, host.name))
        return port_groups

    def collect_datastores(self) -> list[Datastore]:
        datastores: list[Datastore] = []
        for dc in self._client.datacenters:
            for host in self._collect_hosts_in_dc(dc):
                if host.datastore:
                    for ds in host.datastore:
                        datastores.append(self._acl.to_datastore(ds, host.name))
        return datastores

    def _collect_objects(self, folder: vim.Folder, obj_type: type) -> list:
        view = self._client.service_instance.content.viewManager.CreateContainerView(
            container=folder,
            type=[obj_type],
            recursive=True,
        )
        result = list(view.view)
        view.DestroyView()
        return result

    def _collect_hosts_in_dc(self, dc: vim.Datacenter) -> list[vim.HostSystem]:
        hosts: list[vim.HostSystem] = []
        folder = dc.hostFolder
        compute_refs = self._collect_objects(folder, vim.ClusterComputeResource)
        for compute in compute_refs:
            hosts.extend(compute.host)
        return hosts
