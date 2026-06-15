from netbox_vsphere_sync.application.dependency_resolver import DependencyResolver


class TestDependencyResolver:
    def setup_method(self) -> None:
        self.resolver = DependencyResolver()

    def test_resolve_orders_correctly(self) -> None:
        result = self.resolver.resolve({"device", "site", "vlan"})
        assert result == ["site", "device", "vlan"]
        assert result.index("site") < result.index("device")
        assert result.index("device") < result.index("vlan")

    def test_resolve_empty_set(self) -> None:
        assert self.resolver.resolve(set()) == []

    def test_dependencies_for_site(self) -> None:
        assert self.resolver.dependencies_for("site") == []

    def test_dependencies_for_device(self) -> None:
        deps = self.resolver.dependencies_for("device")
        assert "site" in deps
        assert "cluster" in deps
        assert "device_role" in deps

    def test_dependencies_for_ip_address(self) -> None:
        deps = self.resolver.dependencies_for("ip_address")
        assert "interface" in deps
        assert "device" in deps
        assert "site" in deps

    def test_sort(self) -> None:
        items = [("device", "esxi-01"), ("site", "DC1"), ("vlan", "100")]
        sorted_items = self.resolver.sort(items)
        assert sorted_items[0][0] == "site"
        assert sorted_items[1][0] == "device"
        assert sorted_items[2][0] == "vlan"
