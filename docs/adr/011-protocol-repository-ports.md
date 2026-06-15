# ADR-011: Repository Ports via Protocol

**Status:** Accepted
**Date:** 2026-06-15

## Context

Domain business logic (sync engine, diff engine) needs to interact with external systems (NetBox, vSphere) but should not depend on concrete infrastructure implementations. Traditional approaches include abstract base classes (ABCs), interfaces, and duck typing.

ABCs require explicit inheritance and create a tight coupling between the port definition and its implementations. Python's `typing.Protocol` provides structural subtyping — an implementation satisfies the interface purely by having the right method signatures.

## Decision

Repository interfaces are defined as **`typing.Protocol`** in the domain layer's `ports.py`:

```python
class DeviceRepository(Protocol):
    def find_by_natural_key(self, site: str, name: str) -> Device | None: ...
    def create(self, device: Device) -> Device: ...
    def update(self, device: Device) -> Device: ...
```

Concrete implementations live in the infrastructure layer and satisfy the Protocol structurally.

- No `I` prefix convention (e.g. `IDeviceRepository`).
- No abstract base classes.
- Protocol methods are minimal — only what the domain needs.

## Consequences

**Positive:**
- Structural subtyping — no explicit `implements` declaration needed.
- Easy to mock for unit tests (simple `Mock` with the right method signature).
- Ports are thin and focused on domain needs.

**Negative:**
- Protocol violations are only caught at runtime (no compile-time check).
- Type-checkers (Pyright) can verify Protocol conformance but configuration is required.
- Protocols cannot enforce async versus sync method signatures at import time.

## Related

- `docs/domains.md` — Port definitions for each repository.
- `docs/standards.md` — Coding standards: Protocol ports, naming conventions.
- `docs/architecture.md` — Component Diagram: domain ports.
