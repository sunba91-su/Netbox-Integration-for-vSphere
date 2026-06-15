# ADR-009: DDD Layered Architecture

**Status:** Accepted
**Date:** 2026-06-15

## Context

The sync logic contains non-trivial business rules:
- Natural key matching.
- Dependency ordering.
- IP address role assignment.
- VLAN allocation strategy.
- Per-host storage linking.

These rules must be testable without external dependencies (vCenter, NetBox, Vault). Without a clean architecture, business logic becomes tightly coupled to API clients, making it hard to unit-test, evolve, or reason about.

## Decision

The codebase follows a **DDD-inspired layered architecture** with four layers:

```
CLI → Application → Domain → Infrastructure
```

| Layer | Responsibility | Dependencies |
|---|---|---|
| CLI | Click commands, argument parsing, output formatting | Application |
| Application | Orchestration: sync engine, diff engine, bootstrapper | Domain |
| Domain | Business rules, entities, value objects, ports | None (pure Python) |
| Infrastructure | API adapters (PyVmomi, pynetbox, hvac), config loading | Domain |

The **Dependency Rule**: each layer depends only on the layer below.

## Consequences

**Positive:**
- Business logic is pure Python — easy to test, no mocking required.
- API changes (e.g. NetBox REST API version upgrade) are isolated to infrastructure.
- Clear boundaries make the codebase navigable for new contributors.

**Negative:**
- More files and modules than a flat architecture.
- Requires discipline — must avoid leaking infrastructure concerns upward.
- Learning curve for developers unfamiliar with DDD.

## Related

- `docs/domains.md` — Full domain model description.
- `docs/architecture.md` — Component Diagram: DDD layers.
- `docs/standards.md` — Project structure, coding standards.
