# ADR-021: Pyright Strict Mode

**Status:** Accepted
**Date:** 2026-06-15

## Context

Python's dynamic typing catches type errors only at runtime. For a project with non-trivial business logic, untyped code accumulates bugs that manifest in production (e.g., passing a string where an integer is expected, returning `None` when a non-optional return type is assumed).

Pyright supports three strictness levels: off, basic, and strict. Strict mode enables all optional checks, including:
- No implicit `Any` (every parameter and return must be typed).
- No untyped function definitions.
- No unknown types in imports.
- No potential `None` violations without explicit handling.

## Decision

**Pyright strict mode** is mandatory for all production code.

- All functions must have fully typed signatures (parameters and return types).
- `Any` is permitted only with an explicit inline comment justifying the exception.
- `# type: ignore` requires an accompanying comment explaining why.
- Pyright is run in CI and as a pre-commit hook.
- `pyrightconfig.json` configures strict mode globally with per-directory exceptions for tests (tests/ gets basic mode to reduce noise).

## Consequences

**Positive:**
- Catches type errors before runtime.
- Self-documenting code through type signatures.
- IDE autocompletion and refactoring support.

**Negative:**
- Increases development time (especially for infrastructure code with complex third-party types).
- Third-party stubs may be incomplete (PyVmomi requires manual type annotations).
- `tests/` requires reduced strictness to avoid fighting with pytest fixtures.

## Related

- `docs/standards.md` — Coding standards: Pyright strict.
- `pyrightconfig.json` — Tool configuration.
- `.pre-commit-config.yaml` — Pre-commit hook.
