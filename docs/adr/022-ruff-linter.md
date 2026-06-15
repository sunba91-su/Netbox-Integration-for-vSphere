# ADR-022: Ruff as Unified Linter

**Status:** Accepted
**Date:** 2026-06-15

## Context

Python linting and formatting traditionally requires multiple tools: flake8 (lint), isort (imports), pyupgrade (modern syntax), black (formatting). Each tool has its own config, its own speed characteristics, and its own set of edge cases.

Ruff is a Rust-based linter and formatter that replaces all of the above in a single binary with a single config file. It is orders of magnitude faster and supports plugins for additional rules.

## Decision

**Ruff** is the sole linting and formatting tool:

- `ruff check` replaces flake8, isort, pyupgrade, and all other linters.
- `ruff format` replaces black.
- Single `ruff.toml` configuration file.
- Rule set: `E/W/F/I/N/UP/RUF/B` (errors, warnings, pyflakes, isort, numpy, pyupgrade, ruff-specific, bugbear).
- `ruff check --fix` runs as a pre-commit hook (auto-fix safe issues).
- `ruff format` runs as a pre-commit hook (formatting only).
- CI fails if any ruff checks fail.

## Consequences

**Positive:**
- Single tool, single config, fast execution.
- Catches common bugs (bugbear rules), import issues, and style problems.
- Formatting guarantees consistent code style without bikeshedding.

**Negative:**
- Ruff's `--fix` can sometimes change semantics (must review before committing).
- Ruff is not yet as configurable as flake8 for very specific plugin needs.
- The ecosystem is newer — some flake8 plugins have no Ruff equivalent.

## Related

- `docs/standards.md` — Coding standards: Ruff rules.
- `ruff.toml` — Tool configuration.
- `.pre-commit-config.yaml` — Pre-commit hook.
- `Makefile` — `make lint`, `make format`.
