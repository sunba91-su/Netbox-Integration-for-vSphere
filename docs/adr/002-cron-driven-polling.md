# ADR-002: Cron-Driven Periodic Polling

**Status:** Accepted
**Date:** 2026-06-15

## Context

Two common patterns exist for keeping external systems synchronised: event-driven (push) and polling (pull).

vSphere lacks a simple, universal CDC (Change Data Capture) stream. vSphere events exist but are:
- Ephemeral (not persisted indefinitely).
- Categorised differently across vSphere versions.
- Not reliably ordered across a cluster.
- Hard to replay after a consumer outage.

Property Collector polling (the alternative) is expensive and version-sensitive.

## Decision

The tool uses **periodic polling** triggered by an external scheduler (cron, systemd timer, K8s CronJob).

- The tool itself has no scheduler — it runs once per invocation.
- The user configures the polling interval via the scheduler (e.g. `*/30 * * * *`).
- Every run performs a full reconciliation against the live vSphere inventory.

## Consequences

**Positive:**
- Infrastructure-agnostic (works with any scheduler).
- Simple tool design — no process persistence, no state.
- Full reconciliation each run (self-healing on restarts).

**Negative:**
- Latency of up to one full poll interval between vSphere change and NetBox update.
- vSphere API load per invocation (scales with inventory size).
- Not suitable for sub-minute synchronisation requirements.

## Related

- `docs/vision.md` — Technology stack: PyVmomi and cron-driven philosophy.
- `docs/SRS.md` — NFR-04 (pull-based sync).
- `docs/architecture.md` — Deployment Design: VM+cron, Docker, K8s CronJob.
