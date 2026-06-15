# ADR-033: Frozen Dataclasses for Value Objects

**Status:** Accepted
**Date:** 2026-06-15

## Context

Domain entities and value objects have different mutability requirements:
- **Entities** have identity (e.g., a Device with a natural key) and some mutable fields (e.g., power state).
- **Value objects** are defined entirely by their attributes and should be immutable (e.g., a vSphere MOR, an IP address with prefix length).

Immutability provides:
- Safe sharing across threads/processes.
- Hashability (value objects can be dict keys or set members).
- Prevention of accidental mutation bugs.
- Value equality (two objects with same fields are equal).

## Decision

- **Value objects** use `@dataclass(frozen=True)` — immutable, hashable, value equality.
- **Entities** use `@dataclass` (not frozen) — identity-based equality, mutable fields.

```python
@dataclass(frozen=True)
class VSphereMOR:
    """vSphere Managed Object Reference — value object."""
    value: str  # e.g., "host-123"
    type: str   # e.g., "HostSystem"

@dataclass
class Device:
    """ESXi host — entity with identity and mutable state."""
    name: str
    site: str
    mor: VSphereMOR
    bios_uuid: str
    power_state: str
    cluster_mor: VSphereMOR | None = None
```

- No `namedtuple` or `TypedDict`.
- No custom `__hash__` or `__eq__` overrides unless necessary.

## Consequences

**Positive:**
- Value objects are safe to use as dict keys and set members.
- Immutability prevents accidental mutation bugs.
- Clear semantic distinction between entities and value objects.

**Negative:**
- Frozen dataclasses cannot have default factories that depend on other fields.
- Updating a value object requires creating a new instance (`dataclasses.replace`).
- Mutable default values (e.g., empty list) require `field(default_factory=list)`.

## Related

- `docs/domains.md` — Entities and Value Objects definitions.
- `docs/standards.md` — Coding standards: dataclass conventions.
- `docs/architecture.md` — Domain Model.
