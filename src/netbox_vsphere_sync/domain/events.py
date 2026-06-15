from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(frozen=True, kw_only=True)
class DomainEvent:
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, kw_only=True)
class EntityCreated(DomainEvent):
    entity_type: str
    natural_key: str
    netbox_id: int | None = None


@dataclass(frozen=True, kw_only=True)
class EntityUpdated(DomainEvent):
    entity_type: str
    natural_key: str
    netbox_id: int
    changes: dict[str, str | object] | None = None


@dataclass(frozen=True, kw_only=True)
class EntitySkipped(DomainEvent):
    entity_type: str
    natural_key: str
    reason: str


@dataclass(frozen=True, kw_only=True)
class EntityPruned(DomainEvent):
    entity_type: str
    natural_key: str
    new_status: str


@dataclass(frozen=True, kw_only=True)
class SyncStarted(DomainEvent):
    config_path: str
    dry_run: bool
    prune: bool


@dataclass(frozen=True, kw_only=True)
class SyncCompleted(DomainEvent):
    duration_seconds: float
    created_count: int = 0
    updated_count: int = 0
    skipped_count: int = 0
    pruned_count: int = 0
    error_count: int = 0


@dataclass(frozen=True, kw_only=True)
class SyncError(DomainEvent):
    entity_type: str | None = None
    natural_key: str | None = None
    error_message: str = ""
    exception_type: str = ""


@dataclass(frozen=True, kw_only=True)
class BootstrapCreated(DomainEvent):
    object_type: str
    name: str


@dataclass(frozen=True, kw_only=True)
class BootstrapSkipped(DomainEvent):
    object_type: str
    name: str
    reason: str
