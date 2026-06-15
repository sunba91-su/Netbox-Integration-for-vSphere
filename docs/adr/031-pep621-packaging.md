# ADR-031: PEP 621 pyproject.toml Packaging

**Status:** Accepted
**Date:** 2026-06-15

## Context

Python packaging has evolved significantly. The traditional approach uses `setup.py` (executable configuration) or `setup.cfg` (declarative but limited). PEP 621 standardises project metadata in `pyproject.toml`, providing a single source of truth for build system configuration, dependencies, and metadata.

The project needs:
- Package metadata (name, version, description, author, license).
- Dependencies and optional dependency groups.
- Entry points (CLI command).
- Build system configuration.

## Decision

Use **`pyproject.toml` (PEP 621)** as the single configuration file:

```toml
[project]
name = "netbox-vsphere-sync"
version = "0.1.0"
description = "One-way synchronisation from VMware vSphere into NetBox"
requires-python = ">=3.11"
dependencies = [
    "pyvmomi>=8.0",
    "pynetbox>=7.0",
    "hvac>=2.0",
    "click>=8.1",
    "pydantic>=2.0",
    "structlog>=24.0",
    "rich>=13.0",
]

[project.scripts]
nvs-sync = "netbox_vsphere_sync.cli.app:main"

[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.backends._legacy:_Backend"
```

No `setup.py` or `setup.cfg` — `pyproject.toml` is the sole build configuration file.

## Consequences

**Positive:**
- Modern standard — single file for all metadata.
- PEP 621 is tool-agnostic (works with setuptools, hatch, pdm, etc.).
- CLI entry points clearly defined.

**Negative:**
- Some older tools (e.g., `pip` < 21.3) may not support all PEP 621 features.
- Version must be hardcoded in `pyproject.toml` or dynamically resolved.
- Optional dependency groups (`[project.optional-dependencies]`) are less mature than `extras_require`.

## Related

- `docs/standards.md` — Package structure.
- `pyproject.toml` — Tool configuration.
- `Makefile` — Build commands.
