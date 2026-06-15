# ADR-025: Single vCenter Per Run

**Status:** Accepted
**Date:** 2026-06-15

## Context

Larger organisations may run multiple vCenter instances — one per datacenter, geography, or administrative boundary. The tool could support multiple vCenters in a single run (aggregating all inventory) or require one invocation per vCenter.

Multi-vCenter aggregation adds complexity:
- Conflict resolution for overlapping names across vCenters.
- Transactional semantics across independent vCenter connections.
- Error isolation (one vCenter failure affecting other syncs).
- Multiple vCenter credentials in a single config.

## Decision

**Each run connects to exactly one vCenter.** Multiple vCenters are handled by running the tool multiple times with different configs:

```bash
nvs-sync --config /etc/nvs/vcenter-dc1.yaml
nvs-sync --config /etc/nvs/vcenter-dc2.yaml
```

- One config file = one vCenter.
- Multiple configs can be scheduled independently or via a wrapper script.
- Each run produces independent results (logs, reports, exit codes).

## Consequences

**Positive:**
- Simple — no aggregation logic.
- Independent failure domains (one vCenter down doesn't block another).
- Connection and credential management is straightforward.

**Negative:**
- Multiple config files to manage.
- Cross-vCenter entities (e.g., VMware vCenter linking, stretched clusters) cannot be correlated.
- Requires cron or wrapper orchestration for multi-vCenter environments.

## Related

- `docs/vision.md` — Single vCenter scope.
- `docs/SRS.md` — NFR-16 (single vCenter support).
- `docs/architecture.md` — Deployment Design: multiple configs.
