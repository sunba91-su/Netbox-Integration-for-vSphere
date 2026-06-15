# ADR-017: Credential Resolution Precedence

**Status:** Accepted
**Date:** 2026-06-15

## Context

The tool requires credentials for three external systems: vCenter, NetBox, and (optionally) Vault. These credentials can come from multiple sources: CLI flags, environment variables, Vault secrets, YAML config files, or defaults.

Without a clear precedence rule, credential resolution is ambiguous and error-prone. Operators may unintentionally override a production credential with a default value.

## Decision

Credential resolution follows a strict **precedence hierarchy** (highest to lowest):

1. **CLI flags** (`--vcenter-username`, `--netbox-token`, etc.)
2. **Environment variables** (`NVS_VCENTER_USERNAME`, `NVS_NETBOX_TOKEN`, etc.)
3. **Vault secrets** (retrieved via hvac, resolved before config file)
4. **YAML config file** (`vcenter.username`, `netbox.token`, etc.)
5. **Defaults** (defined in Pydantic config models — only for non-sensitive values)

If a required credential has no resolved value after evaluating all sources, the tool exits with an actionable error message indicating which credential is missing and which sources were checked.

## Consequences

**Positive:**
- Clear, predictable resolution order.
- CLI flags override everything for ad-hoc testing.
- Environment variables work well for containerised deployments.
- Vault integration for production secrets management.

**Negative:**
- Complex resolution logic with 5 sources.
- Debugging credential issues may require tracing through all resolution steps.
- Vault resolution adds latency before config validation.

## Related

- `docs/architecture.md` — Security Design: credential resolution.
- `docs/SRS.md` — FR-19 (config validation and precedence), NFR-09 (no hardcoded secrets).
- `docs/standards.md` — Security requirements.
