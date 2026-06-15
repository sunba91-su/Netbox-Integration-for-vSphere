# ADR-032: Pre-Commit Quality Gates

**Status:** Accepted
**Date:** 2026-06-15

## Context

CI-based quality checks catch issues after the commit is already made. At that point, fixing requires an additional commit, amending the history, or living with the CI failure. Catching issues earlier — before the commit — reduces CI frustration and keeps the commit history clean.

Pre-commit hooks run automatically on `git commit`. If any hook fails, the commit is aborted. This "shift left" approach moves quality enforcement earlier in the development cycle.

## Decision

**Pre-commit hooks** (via `pre-commit` framework) enforce quality before every commit:

| Hook | Run | Purpose |
|---|---|---|
| `ruff check --fix` | On staged files | Auto-fix lint/import issues |
| `ruff format` | On staged files | Enforce code formatting |
| `pyright` | On staged files | Type checking (strict mode) |
| `trailing-whitespace` | On staged files | Remove trailing whitespace |
| `end-of-file-fixer` | On staged files | Ensure newline at EOF |
| `check-yaml` | On YAML files | Validate YAML syntax |
| `check-toml` | On TOML files | Validate TOML syntax |

Configuration in `.pre-commit-config.yaml` with pinned hook versions.

- Install with `pre-commit install`.
- Run on all files with `pre-commit run --all-files`.
- Can be bypassed with `git commit --no-verify` (discouraged).

## Consequences

**Positive:**
- Catches issues before they reach CI.
- Consistent code style across contributors.
- Faster feedback loop than CI.

**Negative:**
- Slower commit workflow (hooks take time to run).
- Too many hooks can be annoying (kept to 7 essential hooks).
- Pre-commit framework adds a Python dependency (dev only).

## Related

- `docs/standards.md` — Pre-commit hooks.
- `.pre-commit-config.yaml` — Tool configuration.
- `Makefile` — `make install` installs pre-commit hooks.
