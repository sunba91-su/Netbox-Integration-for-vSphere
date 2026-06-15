from __future__ import annotations

from rich.console import Console as RichConsole
from rich.table import Table
from rich.text import Text

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

console = RichConsole()


class ConsoleReporter:
    def __init__(self, event_log: EventLog) -> None:
        self._event_log = event_log

    def render(self) -> None:
        events = self._event_log.events

        for event in events:
            if isinstance(event, SyncStarted):
                self._render_header(event)
            elif isinstance(event, EntityCreated):
                self._render_created(event)
            elif isinstance(event, EntityUpdated):
                self._render_updated(event)
            elif isinstance(event, EntitySkipped):
                self._render_skipped(event)
            elif isinstance(event, EntityPruned):
                self._render_pruned(event)
            elif isinstance(event, SyncError):
                self._render_error(event)
            elif isinstance(event, SyncCompleted):
                self._render_summary(event)

    def _render_header(self, event: SyncStarted) -> None:
        mode = "DRY RUN" if event.dry_run else "LIVE"
        prune = " + PRUNE" if event.prune else ""
        console.print(f"\n[bold cyan]NetBox vSphere Sync[/bold cyan] ({mode}{prune})")
        console.print("=" * 50)

    def _render_created(self, event: EntityCreated) -> None:
        text = Text()
        text.append("  + ", style="green")
        text.append(f"{event.entity_type}: {event.natural_key}")
        console.print(text)

    def _render_updated(self, event: EntityUpdated) -> None:
        text = Text()
        text.append("  ~ ", style="yellow")
        text.append(f"{event.entity_type}: {event.natural_key}")
        if event.changes:
            changes_str = ", ".join(event.changes.keys())
            text.append(f" [{changes_str}]", style="dim")
        console.print(text)

    def _render_skipped(self, event: EntitySkipped) -> None:
        text = Text()
        text.append("  - ", style="grey50")
        text.append(f"{event.entity_type}: {event.natural_key}")
        text.append(f" ({event.reason})", style="dim")
        console.print(text)

    def _render_pruned(self, event: EntityPruned) -> None:
        text = Text()
        text.append("  x ", style="red")
        text.append(f"{event.entity_type}: {event.natural_key}")
        text.append(f" -> {event.new_status}", style="dim")
        console.print(text)

    def _render_error(self, event: SyncError) -> None:
        text = Text()
        text.append("  ! ", style="red")
        if event.entity_type:
            text.append(f"[{event.entity_type}] ")
        text.append(f"{event.error_message}", style="bold red")

        if event.exception_type:
            text.append(f" ({event.exception_type})", style="dim")
        console.print(text)

    def _render_summary(self, event: SyncCompleted) -> None:
        table = Table(title="Sync Summary")

        table.add_column("Metric", style="cyan")
        table.add_column("Count", justify="right")

        table.add_row("Duration", f"{event.duration_seconds:.1f}s")
        table.add_row("Created", str(event.created_count))
        table.add_row("Updated", str(event.updated_count))
        table.add_row("Skipped", str(event.skipped_count))
        table.add_row("Pruned", str(event.pruned_count))
        table.add_row("Errors", str(event.error_count))

        console.print()
        console.print(table)
        console.print()
