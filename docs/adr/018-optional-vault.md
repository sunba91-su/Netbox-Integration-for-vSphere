# ADR-018: Optional Vault Integration

**Status:** Accepted
**Date:** 2026-06-15

## Context

Production deployments require secure secrets management. Environment variables leak into process dumps and shell history. Config files containing credentials should not be committed to version control.

HashiCorp Vault is the industry standard for secrets management. However, not all deployments have access to Vault — small teams, dev environments, and test pipelines may rely on environment variables alone.

## Decision

Vault integration is **optional** (behind a Vault config section):

```yaml
vault:
  enabled: true
  url: https://vault.example.com:8200
  mount_point: secret
  auth_method: token  # token | approle | kubernetes
  path_prefix: nvs/sync
```

- Vault uses KV v2 secrets engine.
- Supported auth methods: token, AppRole, Kubernetes.
- Token auto-renewal at 90% of TTL (60-minute default).
- If Vault is unreachable or disabled, credentials fall back to env vars / config file.
- Credentials retrieved from Vault are never logged, cached to disk, or exposed in error messages.

## Consequences

**Positive:**
- Production-ready secrets management.
- Multiple auth methods for different deployment environments.
- Graceful fallback when Vault is unavailable.

**Negative:**
- Vault dependency (network, authentication) adds a failure point.
- Token renewal logic adds complexity.
- Kubernetes auth requires service account binding configuration.

## Related

- `docs/vision.md` — Vault Integration section.
- `docs/architecture.md` — Security Design: Vault.
- `docs/SRS.md` — FR-19 (config validation), NFR-09 (secrets management).
