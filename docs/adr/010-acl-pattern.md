# ADR-010: Anti-Corruption Layer Pattern

**Status:** Accepted
**Date:** 2026-06-15

## Context

The core domain must not depend on the APIs of external systems:
- PyVmomi returns `vim.*` managed objects with complex nested types.
- pynetbox returns `pynetbox.core.response.Record` and `list` objects.
- hvac returns raw JSON dictionaries.

Directly using these types in domain logic creates tight coupling. A change in PyVmomi API (e.g. vSphere 9.0) could ripple through the entire codebase.

## Decision

Each external system is fronted by an **Anti-Corruption Layer (ACL)** :

- **vSphere ACL:** Translates `vim.*` objects into domain `vsphere.*` entities.
- **NetBox ACL:** Translates pynetbox responses into domain `netbox.*` entities.
- **Vault ACL:** Translates hvac responses into typed config objects.

The ACL is a one-way translation layer, not a full facade. It does not surface external API methods to domain code.

## Consequences

**Positive:**
- API upgrades are isolated to the ACL.
- Domain code uses pure domain objects — no PyVmomi/pynetbox imports.
- ACLs can be unit-tested with recorded fixtures.

**Negative:**
- Translation overhead for every API call.
- ACLs must be kept in sync with domain model changes.
- Two code paths for each external interaction (raw API + ACL wrapper).

## Related

- `docs/domains.md` — ACL definitions for each bounded context.
- `docs/architecture.md` — Component Diagram: ACL isolation.
- `docs/standards.md` — Coding standards: Protocol ports.
