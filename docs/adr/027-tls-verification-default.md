# ADR-027: TLS Verification by Default

**Status:** Accepted
**Date:** 2026-06-15

## Context

The tool connects to three external systems over HTTPS: vCenter, NetBox, and Vault. Disabling TLS verification makes these connections vulnerable to man-in-the-middle attacks and exposes credentials on the wire.

However, development and test environments often use self-signed certificates. Requiring valid TLS certificates in every environment would block local development.

## Decision

**TLS verification is enabled by default** for all three endpoints:

| Endpoint | TLS Verification | Opt-Out Flag |
|---|---|---|
| vCenter | Enabled | `--vcenter-insecure` or `vcenter.verify_ssl: false` |
| NetBox | Enabled | `--netbox-insecure` or `netbox.verify_ssl: false` |
| Vault | Enabled | `vault.verify_ssl: false` |

- A warning is logged when TLS verification is disabled.
- Disabling TLS is always explicit — no automatic detection.
- CLI flags override YAML config for ad-hoc troubleshooting.

## Consequences

**Positive:**
- Secure default for production use.
- Explicit opt-out for development environments.
- Warning log helps operators audit insecure configurations.

**Negative:**
- Self-signed certificates in dev/staging require per-endpoint opt-out.
- No support for custom CA bundles (future enhancement possible).

## Related

- `docs/SRS.md` — NFR-05 (TLS enabled by default).
- `docs/architecture.md` — Security Design: TLS.
- `docs/standards.md` — Security requirements.
