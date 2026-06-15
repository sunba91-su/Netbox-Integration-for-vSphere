# ADR-006: Dry-Run Philosophy

**Status:** Accepted
**Date:** 2026-06-15

## Context

Operators need to preview what changes a sync run will make before applying them to a production NetBox instance. Without a dry-run feature, the only way to test is against a staging NetBox — which is often unavailable or out of sync.

## Decision

Every sync invocation supports `--dry-run` mode:

1. Collect from vSphere (same as live run).
2. Fetch current state from NetBox (same as live run).
3. Compute the diff (same algorithm as live run).
4. Report the diff to the user.
5. **Write nothing to NetBox.**

The diff report shows:
- Entities to be created (POST).
- Entities to be updated (PATCH).
- Entities to be pruned (with `--prune`).

## Consequences

**Positive:**
- Safe preview for production changes.
- Builds operator confidence in the tool.
- Shareable change sets for team review.

**Negative:**
- Two code paths for every mutation (dry-run vs live), increasing testing surface.
- Dry-run diff is a snapshot; real state may differ when live run executes.

## Related

- `docs/SRS.md` — FR-08 (dry-run mode).
- `docs/architecture.md` — Diff Engine component.
- `docs/standards.md` — Testing: diff engine unit tests.
