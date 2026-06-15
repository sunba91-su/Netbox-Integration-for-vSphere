from netbox_vsphere_sync.domain.model.vsphere import (
    Cluster,
    Datastore,
    HostHardware,
    HostSystem,
    Interface,
    IpAddress,
    PortGroup,
    Site,
    Vlan,
    VSphereMOR,
)


class TestValueObjects:
    def test_mor_creation(self) -> None:
        mor = VSphereMOR(value="host-123", type="HostSystem")
        assert mor.value == "host-123"
        assert mor.type == "HostSystem"

    def test_mor_immutability(self) -> None:
        mor = VSphereMOR(value="host-123", type="HostSystem")
        assert mor.value == "host-123"

    def test_hardware_creation(self) -> None:
        hw = HostHardware(
            cpu_model="Intel Xeon",
            cpu_cores=32,
            cpu_sockets=2,
            memory_gb=256.0,
            model="ProLiant DL380",
            serial="ABC123",
        )
        assert hw.cpu_cores == 32
        assert hw.memory_gb == 256.0


class TestEntities:
    def test_site_defaults(self) -> None:
        site = Site(name="DC1")
        assert site.name == "DC1"
        assert site.description == ""
        assert site.custom_fields == {}

    def test_site_with_custom_fields(self) -> None:
        site = Site(
            name="DC1",
            description="Primary datacenter",
            custom_fields={"nvs_vsphere_mor": "datacenter-123"},
        )
        assert site.custom_fields["nvs_vsphere_mor"] == "datacenter-123"

    def test_cluster_creation(self) -> None:
        cluster = Cluster(name="Cluster1", site="DC1")
        assert cluster.name == "Cluster1"
        assert cluster.site == "DC1"
        assert cluster.ha_enabled is False

    def test_host_system_creation(self) -> None:
        host = HostSystem(
            name="esxi-01.example.com",
            site="DC1",
            cluster="Cluster1",
            bios_uuid="ABC-DEF-123",
            esxi_version="8.0.2",
            power_state="poweredOn",
            vcenter_host="vc01.example.com",
        )
        assert host.name == "esxi-01.example.com"
        assert host.power_state == "poweredOn"
        assert host.maintenance_mode is False

    def test_interface_creation(self) -> None:
        iface = Interface(name="vmk0", device="esxi-01")
        assert iface.name == "vmk0"
        assert iface.enabled is True
        assert iface.mtu == 1500

    def test_ip_address_creation(self) -> None:
        ip = IpAddress(
            address="10.0.0.1",
            prefix_length=24,
            interface="vmk0",
            device="esxi-01",
            role="anycast",
        )
        assert ip.address == "10.0.0.1"
        assert ip.role == "anycast"

    def test_port_group_creation(self) -> None:
        pg = PortGroup(name="vMotion", vlan_id=100)
        assert pg.name == "vMotion"
        assert pg.vlan_id == 100
        assert pg.switch_type == "standard"

    def test_vlan_creation(self) -> None:
        vlan = Vlan(site="DC1", vid=100, name="Management")
        assert vlan.vid == 100
        assert vlan.status == "active"

    def test_datastore_creation(self) -> None:
        ds = Datastore(
            name="ds-01",
            device="esxi-01",
            capacity_bytes=1073741824,
            free_bytes=536870912,
        )
        assert ds.name == "ds-01"
        assert ds.capacity_bytes == 1073741824
        assert ds.role == "Storage"

    def test_interface_with_ip_addresses(self) -> None:
        ip = IpAddress(address="10.0.0.1", prefix_length=24, interface="vmk0", device="esxi-01")
        iface = Interface(name="vmk0", device="esxi-01", ip_addresses=[ip])
        assert len(iface.ip_addresses) == 1
        assert iface.ip_addresses[0].address == "10.0.0.1"
