# AGENTS.md — Netbox-Integration-for-vSphere

## State

Greenfield repository. No source code, no build system, no dependency manifests, no CI.

## Scope

Netbox ↔ vSphere integration. The eventual toolchain is not yet established, but Python (PyVmomi, pynetbox) is the most likely choice given the ecosystem.

## Guidance

- **No commands yet.** Build, test, lint, format, and typecheck recipes do not exist. Do not guess.
- **No existing conventions.** Establish them deliberately as the first code lands.
- **Start simple.** Choose Python with `pyproject.toml`, add a `Makefile` or `Taskfile.yml` for common commands, and pin a CI workflow early.
- **Expected eventual stack (not guaranteed):** Python, pytest, flake8/ruff, mypy/pyright, pre-commit.

Remove this file once an actual toolchain is in place and a proper `AGENTS.md` can be written against real code.
