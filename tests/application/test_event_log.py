from netbox_vsphere_sync.application.event_log import EventLog
from netbox_vsphere_sync.domain.events import (
    EntityCreated,
    EntitySkipped,
    EntityUpdated,
    SyncError,
    SyncStarted,
)


class TestEventLog:
    def setup_method(self) -> None:
        self.log = EventLog()

    def test_record_and_count(self) -> None:
        self.log.record(SyncStarted(config_path="", dry_run=True, prune=False))
        self.log.record(EntityCreated(entity_type="site", natural_key="site:DC1"))
        assert len(self.log.events) == 2

    def test_created_count(self) -> None:
        self.log.record(EntityCreated(entity_type="site", natural_key="site:DC1"))
        self.log.record(EntityCreated(entity_type="device", natural_key="device:DC1:esxi-01"))
        assert self.log.created_count == 2

    def test_updated_count(self) -> None:
        self.log.record(EntityUpdated(entity_type="site", natural_key="site:DC1", netbox_id=1))
        assert self.log.updated_count == 1

    def test_skipped_count(self) -> None:
        self.log.record(
            EntitySkipped(
                entity_type="site",
                natural_key="site:DC1",
                reason="No changes",
            )
        )
        assert self.log.skipped_count == 1

    def test_error_count(self) -> None:
        self.log.record(
            SyncError(
                error_message="Connection failed",
                exception_type="ConnectionError",
            )
        )
        assert self.log.error_count == 1

    def test_clear(self) -> None:
        self.log.record(EntityCreated(entity_type="site", natural_key="site:DC1"))
        self.log.clear()
        assert len(self.log.events) == 0
