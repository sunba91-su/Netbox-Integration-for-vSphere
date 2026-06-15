from __future__ import annotations

from netbox_vsphere_sync.application.event_log import EventLog
from netbox_vsphere_sync.domain.events import (
    EntityCreated,
    EntityPruned,
    EntitySkipped,
    EntityUpdated,
    SyncCompleted,
    SyncError,
    SyncStarted,
)


class ReportGenerator:
    def __init__(self, event_log: EventLog) -> None:
        self._event_log = event_log

    def generate_text(self) -> str:
        lines: list[str] = []
        events = self._event_log.events

        for event in events:
            if isinstance(event, SyncStarted):
                lines.append(f"Sync: dry_run={event.dry_run}")
            elif isinstance(event, EntityCreated):
                lines.append(f"  + {event.entity_type}: {event.natural_key}")
            elif isinstance(event, EntityUpdated):
                changes = f" [{', '.join(event.changes.keys())}]" if event.changes else ""
                lines.append(f"  ~ {event.entity_type}: {event.natural_key}{changes}")
            elif isinstance(event, EntitySkipped):
                lines.append(f"  - {event.entity_type}: {event.natural_key} ({event.reason})")
            elif isinstance(event, EntityPruned):
                lines.append(f"  x {event.entity_type}: {event.natural_key} -> {event.new_status}")
            elif isinstance(event, SyncError):
                lines.append(f"  ! {event.error_message or event.entity_type}")
            elif isinstance(event, SyncCompleted):
                lines.append(
                    f"\nSummary: {event.duration_seconds:.1f}s | "
                    f"+{event.created_count} ~{event.updated_count} "
                    f"-{event.skipped_count} x{event.pruned_count} "
                    f"!{event.error_count}"
                )

        return "\n".join(lines)
