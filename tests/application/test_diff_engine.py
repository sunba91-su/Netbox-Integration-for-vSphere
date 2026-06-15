from netbox_vsphere_sync.application.diff_engine import DiffEngine
from netbox_vsphere_sync.domain.model.vsphere import (
    HostSystem,
    Site,
)


class TestDiffEngine:
    def setup_method(self) -> None:
        self.engine = DiffEngine()

    def test_natural_key_site(self) -> None:
        site = Site(name="DC1")
        assert self.engine.natural_key(site) == "site:DC1"

    def test_natural_key_device(self) -> None:
        device = HostSystem(name="esxi-01", site="DC1")
        assert self.engine.natural_key(device) == "device:DC1:esxi-01"

    def test_compute_no_changes(self) -> None:
        result = self.engine.compute([], [])
        assert len(result.to_create) == 0
        assert len(result.to_update) == 0
        assert len(result.to_skip) == 0

    def test_compute_create_new(self) -> None:
        site = Site(name="DC1")
        result = self.engine.compute([site], [])
        assert len(result.to_create) == 1
        assert result.to_create[0].name == "DC1"

    def test_compute_skip_unchanged(self) -> None:
        vs_site = Site(name="DC1", description="Original")
        nb_site = Site(name="DC1", description="Original")
        result = self.engine.compute([vs_site], [nb_site])
        assert len(result.to_create) == 0
        assert len(result.to_update) == 0
        assert len(result.to_skip) == 1

    def test_compute_update_changed(self) -> None:
        vs_site = Site(name="DC1", description="Updated")
        nb_site = Site(name="DC1", description="Original")
        result = self.engine.compute([vs_site], [nb_site])
        assert len(result.to_update) == 1
        nb, vs = result.to_update[0]
        assert nb.description == "Original"
        assert vs.description == "Updated"

    def test_compute_prune_orphan(self) -> None:
        nb_site = Site(name="DC1", description="Orphan")
        result = self.engine.compute([], [nb_site])
        assert len(result.to_prune) == 1
        entity_type, key, status = result.to_prune[0]
        assert entity_type == "site"
        assert key == "site:DC1"

    def test_has_changes_true(self) -> None:
        from netbox_vsphere_sync.application.diff_engine import DiffResult

        result = DiffResult()
        assert result.has_changes is False
        result.to_create.append(Site(name="DC1"))
        assert result.has_changes is True
