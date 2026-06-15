# ADR-007: Auto-Bootstrap NetBox Metadata

**Status:** Accepted
**Date:** 2026-06-15

## Context

NetBox requires several metadata objects to exist before devices, clusters, and interfaces can be created:

- **Manufacturer:** "VMware Inc" for ESXi hosts.
- **Device Role:** "ESXi Server" with appropriate colour/slug.
- **Cluster Type:** "vSphere Cluster" for vSphere clusters.
- **Custom Fields:** vSphere-specific fields (MOR, BIOS UUID, ESXi version, power state, etc.).

Requiring users to create these manually before first sync is error-prone and creates a poor onboarding experience.

## Decision

The tool **bootstraps required NetBox metadata automatically** on first run (or any run where it is missing):

- Checks for existence by natural key.
- Creates Manufacturer, Role, ClusterType if absent.
- Creates/validates Custom Fields by name and type.
- The `bootstrap` config section allows disabling specific auto-creation.
- Bootstrap runs as the first step before any entity sync.

## Consequences

**Positive:**
- Zero manual NetBox setup required.
- Idempotent — safe to re-run.
- Custom fields are versioned with the tool (schema-in-code).

**Negative:**
- The tool requires NetBox write permissions for metadata (not just data).
- May surprise NetBox administrators who expect full manual control.
- Custom field creation cannot be undone by the tool (NetBox has no CF delete API for populated fields).

## Related

- `docs/SRS.md` — FR-03 (auto-discovery and creation of manufacturer, roles, types), FR-04 (custom field creation).
- `docs/architecture.md` — Custom Fields Inventory table, Bootstrap component.
- `docs/vision.md` — Implementation Plan: Phase 1 Bootstrap.
