from netbox_vsphere_sync.domain.events import DomainEvent


class EventLog:
    def __init__(self) -> None:
        self._events: list[DomainEvent] = []

    def record(self, event: DomainEvent) -> None:
        self._events.append(event)

    @property
    def events(self) -> list[DomainEvent]:
        return list(self._events)

    def clear(self) -> None:
        self._events.clear()

    @property
    def created_count(self) -> int:
        from netbox_vsphere_sync.domain.events import EntityCreated

        return sum(1 for e in self._events if isinstance(e, EntityCreated))

    @property
    def updated_count(self) -> int:
        from netbox_vsphere_sync.domain.events import EntityUpdated

        return sum(1 for e in self._events if isinstance(e, EntityUpdated))

    @property
    def skipped_count(self) -> int:
        from netbox_vsphere_sync.domain.events import EntitySkipped

        return sum(1 for e in self._events if isinstance(e, EntitySkipped))

    @property
    def pruned_count(self) -> int:
        from netbox_vsphere_sync.domain.events import EntityPruned

        return sum(1 for e in self._events if isinstance(e, EntityPruned))

    @property
    def error_count(self) -> int:
        from netbox_vsphere_sync.domain.events import SyncError

        return sum(1 for e in self._events if isinstance(e, SyncError))
