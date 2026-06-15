# ADR-035: Five Bounded Contexts

**Status:** Accepted
**Date:** 2026-06-15

## Context

The system has several distinct responsibilities that should be separated to enable independent evolution, testing, and reasoning:

1. Reading vSphere inventory (PyVmomi, property collector, vSphere data model).
2. Writing to NetBox (pynetbox, upsert semantics, NetBox data model).
3. Orchestrating the sync (dependency ordering, diff computation, event emission).
4. Managing configuration and secrets (YAML, env, Vault, Pydantic validation).
5. Observability (logging, reporting, metrics).

Mixing these responsibilities creates modules that are hard to change, test, or reason about.

## Decision

The system is organised into **five bounded contexts**:

| Context | Responsible For | Location |
|---|---|---|
| **vSphere Inventory** | vSphere connection, property collection, MOR → domain translation | `infrastructure/vsphere/` |
| **NetBox CMDB** | NetBox connection, repository implementations, domain → NetBox translation | `infrastructure/netbox/` |
| **Sync Orchestration** | Sync engine, diff engine, bootstrapper, dependency resolver | `application/` |
| **Config & Secrets** | YAML loading, env var resolution, Vault integration, Pydantic validation | `infrastructure/config/`, `infrastructure/vault/` |
| **Observability** | Event log, Rich console, structlog configuration | `report/` |

The **domain layer** (`domain/`) is shared across contexts — it contains the pure business model that all contexts reference.

## Consequences

**Positive:**
- Clear responsibility boundaries — each context has a single purpose.
- Independent evolution — changing vSphere collector doesn't affect NetBox repository.
- Easier testing — each context can be tested in isolation.

**Negative:**
- Five contexts + domain = six module groups to navigate.
- Context boundaries require translation logic (ACLs).
- Some code spans contexts (e.g., a custom field definition is both NetBox CMDB and Config).

## Related

- `docs/domains.md` — Bounded Context definitions.
- `docs/architecture.md` — System Context diagram.
- `docs/standards.md` — Project structure.
