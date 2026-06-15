# ADR-015: IP Address Role Decision Matrix

**Status:** Accepted
**Date:** 2026-06-15

## Context

NetBox IPAddress records have a `role` field indicating the address's purpose (loopback, secondary, anycast, VIP, VRRP, HSRP, GLBP, carp). vSphere exposes network interfaces through two mechanisms:

1. **Service tags** on VMkernel network interfaces (management, vmotion, vsan, faultToleranceLogging, vSphereReplication, vSphereReplicationNfc, nfs, etc.).
2. **Port group names** on standard and distributed switches.

Service tags are more precise but not always populated (especially for standard port groups or older vSphere versions).

## Decision

IP address role is assigned using a **two-tier decision matrix**:

| Tier | Source | Priority |
|---|---|---|
| 1 | vSphere service tag | Highest (exact match) |
| 2 | Port group prefix rule | Fallback |

**Tier 1 — Service Tag Mapping:**
| vSphere Service Tag | NetBox Role |
|---|---|
| vmotion | anycast |
| vsan | anycast |
| faultToleranceLogging | anycast |
| vSphereReplication | anycast |
| vSphereReplicationNfc | anycast |
| nfs | anycast |
| management | (null — default) |

**Tier 2 — Port Group Prefix Rules** (configurable in YAML):
```yaml
ipaddress_role_mapping:
  - pattern: "^vMotion"
    role: anycast
  - pattern: "^VSAN"
    role: anycast
  - pattern: "^Management"
    role: null
```

If no rule matches, role is omitted (null).

## Consequences

**Positive:**
- Deterministic role assignment for every IP.
- Service tags provide accurate roles where available.
- Port group prefix rules provide a configurable fallback.

**Negative:**
- Two-tier logic adds complexity to the role resolution.
- Port group naming conventions vary across organisations (prefix rules must be customised).
- Service tag priority may not be desired in all cases.

## Related

- `docs/vision.md` — IPAddress Role Decision Matrix.
- `docs/SRS.md` — FR-16 (IP address role mapping).
- `docs/architecture.md` — API Design: IP address resolution.
