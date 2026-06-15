# ADR-036: Deployment-Agnostic Design

**Status:** Accepted
**Date:** 2026-06-15

## Context

Different teams have different deployment requirements:
- **Traditional ops:** VM with systemd timer and config file.
- **Container-first teams:** Docker container with env var config.
- **Kubernetes-native teams:** CronJob with Vault CSI or AppRole.
- **Small teams:** Simple cron job on the NetBox server.

The tool should not prescribe a single deployment topology. It must work equally well in all of these environments.

## Decision

The core tool is **deployment-agnostic** — it has no deployment-specific code:

- **No daemon mode** — runs synchronously and exits.
- **No PID file management** beyond concurrency lock (ADR-026).
- **No log rotation** — relies on external log management.
- **No container health checks** — exit codes provide status.
- **All configuration** through CLI flags, env vars, config files, and Vault.

Supported deployment topologies (documented in architecture.md):

| Topology | Config | Schedule | Secrets |
|---|---|---|---|
| VM + systemd timer | YAML file | systemd timer | Vault agent / env file |
| Docker + cron | Env vars + (optional YAML) | Host cron | Docker secrets / env |
| K8s CronJob | ConfigMap + env | CronJob spec | Vault CSI / K8s secrets |
| K8s + Vault | ConfigMap + Vault annotations | CronJob spec | Vault Agent injector |

## Consequences

**Positive:**
- Maximum flexibility — works in any environment.
- No deployment-specific bugs in core code.
- Documentation can cover multiple topologies.

**Negative:**
- No built-in health checks (must rely on exit codes and monitoring).
- No built-in log rotation (relies on external tools).
- Users must assemble their own deployment configuration.

## Related

- `docs/architecture.md` — Deployment Design: 4 topologies.
- `docs/SRS.md` — NFR-07 (deployment flexibility).
