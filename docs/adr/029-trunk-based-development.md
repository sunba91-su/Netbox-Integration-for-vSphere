# ADR-029: Trunk-Based Development

**Status:** Accepted
**Date:** 2026-06-15

## Context

Long-lived feature branches create integration debt — the longer a branch diverges from main, the more painful the merge. Complex multi-party merges can introduce subtle bugs.

Common alternatives:
- **Git Flow:** Long-lived develop/release branches. Heavy ceremony for a small project.
- **Trunk-based:** Short-lived branches (< 3 days), frequent merges to main.
- **Main-only:** No branches, commit directly to main. Risky for team work.

## Decision

**Trunk-based development** with short-lived feature branches:

```
main ─────●─────────●───────────────●─────────▶
          │         │               │
          ├─ feat/x ┘               │
          │         └─ fix/y ───────┘
                    └─ chore/z ─────┘
```

Rules:
- `main` is always deployable — no direct pushes.
- Feature branches live < 3 days (preferred).
- Branch naming: `feat/xxx`, `fix/xxx`, `docs/xxx`, `chore/xxx`, `test/xxx`, `refactor/xxx`.
- PR required for every change.
- Squash merge to keep `main` history linear.
- Rebase onto `main` before opening the PR.
- No `develop` branch.

## Consequences

**Positive:**
- Clean, linear git history on `main`.
- Fast integration — merge conflicts are minimised.
- Easy to reason about what's in a release.

**Negative:**
- Requires discipline to keep branches short-lived.
- Incomplete features must be hidden behind feature flags or not merged.
- Squash merging loses individual commit granularity on `main`.

## Related

- `docs/standards.md` — Git strategy, branch naming.
- `AGENTS.md` — Branch strategy.
