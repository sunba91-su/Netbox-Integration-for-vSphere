# ADR-013: Domain Events for Observability

**Status:** Accepted
**Date:** 2026-06-15

## Context

The sync engine performs multiple operations (collect, diff, create, update, skip, error). Each operation has associated metadata (entity type, natural key, duration, error details). This data needs to be captured for:
- Console output (Rich tables).
- Structured logs (structlog JSON).
- Reports (human-readable summary).
- Metrics (counts of created/updated/errored entities).

Embedding logging calls directly in domain or application logic couples those layers to the logging framework.

## Decision

The application layer emits **immutable domain events** during sync:

```python
@dataclass(frozen=True)
class EntityCreated:
    entity_type: str
    natural_key: str
    netbox_id: int

@dataclass(frozen=True)
class EntityUpdated:
    entity_type: str
    natural_key: str
    netbox_id: int
    changes: dict

@dataclass(frozen=True)
class EntitySkipped:
    entity_type: str
    natural_key: str
    reason: str

@dataclass(frozen=True)
class SyncError:
    entity_type: str
    natural_key: str
    exception: str
```

An `EventLog` collects events in memory during a run. After the run, the observability layer consumes the event log to produce output (console, JSON, report).

## Consequences

**Positive:**
- Clean separation of sync logic from output formatting.
- Events are testable data objects.
- Easy to add new output formats (e.g. JSON file, metrics push) without modifying sync logic.

**Negative:**
- Memory consumption proportional to event volume.
- Events are lost if the process crashes before output generation.
- Event schema must be versioned for forward compatibility.

## Related

- `docs/domains.md` — Events in domain layer.
- `docs/architecture.md` — Event Log component.
- `docs/standards.md` — Testing: application layer events.
