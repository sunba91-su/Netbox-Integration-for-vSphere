# ADR-016: Configurable VLAN ID Allocation

**Status:** Accepted
**Date:** 2026-06-15

## Context

vSphere port groups may or may not carry VLAN tags. Some port groups use explicit VLAN IDs, others use "VLAN Trunking" (0/4095), and some are assigned by the vCenter using ephemeral port bindings (no tag).

NetBox requires a VLAN ID (1-4095) for each VLAN object. The tool must decide what to do for port groups without a usable tag.

## Decision

VLAN allocation uses a **configurable three-strategy model** defined per sync scope:

```yaml
vlan_allocation:
  strategy: from_portgroup  # from_portgroup | reserved_range | auto_allocate
  # For reserved_range strategy:
  range_start: 3000
  range_end: 3999
```

| Strategy | Behaviour |
|---|---|
| `from_portgroup` | Use the VLAN tag from the port group. Skip if tag is 0 or empty. |
| `reserved_range` | Allocate a VLAN ID from a configured reserved range. Requires stable allocation tracking. |
| `auto_allocate` | Skip VLAN creation for port groups without tags. Only create from tagged port groups. |

When using `reserved_range`, allocation stability is maintained by deterministic mapping based on the port group's natural key (e.g., hash to a slot in the reserved range).

## Consequences

**Positive:**
- Flexible — works with VLAN-tagged, trunked, and untagged port groups.
- `reserved_range` provides stable VLAN IDs for untagged networks.
- Configuration is explicit — no guesswork.

**Negative:**
- `reserved_range` requires collision detection and allocation tracking.
- Three strategies mean more test cases.
- Strategy choice is global per config, not per port group.

## Related

- `docs/vision.md` — VLAN ID strategy.
- `docs/SRS.md` — FR-18 (VLAN ID allocation).
- `docs/architecture.md` — API Design: VLAN creation.
