# Project Plan: Python Best Practices + Docker + CI/CD

## Project Epics & Tasks: Python Best Practices + Docker + CI/CD

---

## Epic 1: Project Structure & Packaging

> Establish clean module boundaries, explicit public interfaces, and proper version management.

---

### Task 1.1 — Add package version and public API exports ✅

**Description:**
Add `__version__ = "0.1.0"` and `__all__` to the root package `__init__.py`. This becomes the single source of truth for the package version, referenced dynamically by `pyproject.toml`.

**Dependencies:** None

**Estimated Complexity:** Low

**Definition of Done:**
- [x] `src/netbox_vsphere_sync/__init__.py` contains `__version__ = "0.1.0"` and `__all__ = ["__version__"]`
- [x] `pyproject.toml` uses `dynamic = ["version"]` with `[tool.setuptools.dynamic] version = {attr = "netbox_vsphere_sync.__version__"}`
- [x] `python -c "import netbox_vsphere_sync; print(netbox_vsphere_sync.__version__)"` prints `0.1.0`

---

### Task 1.2 — Add `__all__` exports to all subpackage `__init__.py` files ✅

**Description:**
Define explicit public APIs for every subpackage using `__all__`. This follows the python-project-structure skill pattern and makes the package's public interface discoverable.

**Dependencies:** None

**Estimated Complexity:** Medium

**Definition of Done:**
- [x] `domain/__init__.py` exports: entities, value objects, events, ports, exceptions, constants
- [x] `application/__init__.py` exports: `SyncEngine`, `DiffEngine`, `DependencyResolver`, `Bootstrapper`, `EventLog`
- [x] `infrastructure/netbox/__init__.py` exports: `NetBoxClient`, `NetBoxACL`, all repositories
- [x] `infrastructure/vsphere/__init__.py` exports: `VSphereClient`, `VSphereCollector`, `VSphereACL`
- [x] `infrastructure/vault/__init__.py` exports: `VaultClient`, `VaultACL`
- [x] `infrastructure/config/__init__.py` exports: `ConfigLoader`, `SecretResolver`, `PidLockManager`
- [x] `cli/__init__.py` exports: `main`
- [x] `report/__init__.py` exports: `ReportGenerator`, `ConsoleReporter`
- [x] `make typecheck` passes with no new errors

---

### Task 1.3 — Add PEP 561 `py.typed` marker ✅

**Description:**
Create an empty `py.typed` marker file so type checkers (pyright, mypy) recognize this package as typed per PEP 561.

**Dependencies:** None

**Estimated Complexity:** Low

**Definition of Done:**
- [x] File `src/netbox_vsphere_sync/py.typed` exists (empty)
- [x] `pyproject.toml` includes `package-data` to include `py.typed` in the distribution

---

### Task 1.4 — Add pytest configuration to `pyproject.toml` ✅

**Description:**
Add `[tool.pytest.ini_options]` section with markers (`unit`, `integration`, `slow`, `vcr`) and default `addopts`. This consolidates test configuration into one file.

**Dependencies:** None

**Estimated Complexity:** Low

**Definition of Done:**
- [x] `pyproject.toml` contains `[tool.pytest.ini_options]` with markers and `addopts`
- [x] `pytest --markers` shows `unit`, `integration`, `slow`, `vcr`
- [x] `make test` passes without regression

---

### Task 1.5 — Add `py.typed` marker and `vcr` pytest marker ✅

**Description:**
Create an empty `py.typed` marker file (PEP 561) so type checkers recognize this package as typed. Also add the missing `vcr` pytest marker to complete the test marker set defined in standards.md §6.6.

**Dependencies:** Task 1.4

**Estimated Complexity:** Low

**Definition of Done:**
- [x] File `src/netbox_vsphere_sync/py.typed` exists (empty)
- [x] `pyproject.toml` includes `[tool.setuptools.package-data]` to include `py.typed`
- [x] `pyproject.toml` pytest markers include `vcr: Tests using recorded HTTP cassettes`
- [x] `pytest --markers` shows all 4 markers: `unit`, `integration`, `slow`, `vcr`
- [x] `make check` passes

---

### Task 1.6 — Add LICENSE file ✅

**Description:**
Create the Apache 2.0 LICENSE file at the repository root. This is referenced in standards.md §1.1 and pyproject.toml but doesn't exist yet.

**Dependencies:** None

**Estimated Complexity:** Low

**Definition of Done:**
- [x] `LICENSE` file exists at repository root
- [x] File contains Apache License 2.0 full text
- [x] `pyproject.toml` license field matches LICENSE file

---

## Epic 2: Logging & Observability

> Integrate structlog for structured, configurable logging with sensitive data filtering.

---

### Task 2.1 — Create logging configuration module ✅

**Description:**
Create `report/logging_config.py` with a `configure_logging()` function that sets up structlog with console (dev) and JSON (prod) renderers, timestamp formatting, and sensitive key filtering (`password`, `token`, `secret` → `****`). Log level configurable via `NVS_LOG_LEVEL` env var.

**Dependencies:** None

**Estimated Complexity:** Medium

**Definition of Done:**
- [x] `report/logging_config.py` exists with `configure_logging(log_level, log_format)` function
- [x] Sensitive key processor masks `password`, `token`, `secret`, `secret_id` fields
- [x] Console renderer produces human-readable output
- [x] JSON renderer produces valid JSON
- [x] Unit test verifies sensitive key filtering works

---

### Task 2.2 — Integrate structlog into core modules ✅

**Description:**
Add structured logging to key modules: `sync_engine.py`, `diff_engine.py`, `bootstrapper.py`, `config/loader.py`, `vsphere/client.py`, `netbox/client.py`, `vault/client.py`. Use `structlog.get_logger(__name__)` pattern. Log sync start/end, entity counts, diff summary, and errors with context.

**Dependencies:** Task 2.1

**Estimated Complexity:** Medium

**Definition of Done:**
- [x] All listed modules import and use `structlog.get_logger(__name__)`
- [x] `sync_engine.py` logs: sync start (with dry_run/prune flags), entity counts per type, sync completion (with duration and counts)
- [x] `netbox/client.py` logs: connection attempt, success/failure
- [x] `vsphere/client.py` logs: connection attempt, success/failure
- [x] No credentials appear in any log output
- [x] `make typecheck` passes
- [x] `make lint` passes

---

### Task 2.3 — Add `--verbose` and `--log-format` CLI options ✅

**Description:**
Add `--verbose` flag (sets log level to DEBUG) and `--log-format` option (`console` or `json`) to the CLI. Wire these to `configure_logging()`.

**Dependencies:** Task 2.1, Task 2.2

**Estimated Complexity:** Low

**Definition of Done:**
- [x] `nvs-sync sync --help` shows `--verbose` and `--log-format` options
- [x] `--verbose` sets log level to DEBUG
- [x] `--log-format json` produces JSON output
- [x] `--log-format console` (default) produces human-readable output
- [x] `NVS_LOG_LEVEL` env var works as fallback
- [x] `make test` passes

---

## Epic 3: NetBox Integration Best Practices

> Align the NetBox integration with official best practices for performance, reliability, and authentication.

---

### Task 3.1 — Enhance `NetBoxClient` with pagination, brief mode, and timeouts ✅

**Description:**
Update `NetBoxClient` to:
- Enable threading for concurrent requests: `pynetbox.api(..., threading=True)`
- Add configurable request timeout (default 120s)
- Add `brief=True` parameter support for list operations
- Add `exclude_config_context` parameter support for device/cluster queries
- Add retry wrapper with exponential backoff for transient `ConnectionError`/`ReadTimeout`

**Dependencies:** None

**Estimated Complexity:** Medium

**Definition of Done:**
- [x] `NetBoxClient.__init__` accepts `timeout`, `brief_mode`, `exclude_config_context` params
- [x] `list_all()` method passes `brief=True` when enabled
- [x] Device/cluster list calls exclude `config_context` by default
- [x] Retry logic handles transient errors (max 3 retries, exponential backoff)
- [x] Existing unit tests still pass
- [x] `make typecheck` passes

---

### Task 3.2 — Add NetBox configuration options ✅

**Description:**
Extend `NetBoxConfig` Pydantic model with new fields: `brief_mode`, `exclude_config_context`, `request_timeout`, `max_retries`. These have sensible defaults and are configurable via YAML.

**Dependencies:** None

**Estimated Complexity:** Low

**Definition of Done:**
- [x] `NetBoxConfig` has new fields with defaults: `brief_mode=True`, `exclude_config_context=True`, `request_timeout=120`, `max_retries=3`
- [x] Existing config loading still works (backwards compatible)
- [x] YAML config can override these values
- [x] `make test` passes

---

### Task 3.3 — Update repositories to use new client features ✅

**Description:**
Update all repository implementations in `infrastructure/netbox/repositories/` to pass `brief=True` and `exclude_config_context=True` (where applicable) through the client.

**Dependencies:** Task 3.1, Task 3.2

**Estimated Complexity:** Medium

**Definition of Done:**
- [x] All repositories pass appropriate flags to `client.list_all()`
- [x] `device_repository.py` excludes `config_context`
- [x] `cluster_repository.py` excludes `config_context`
- [x] Brief mode enabled for all list operations
- [x] `make test` passes
- [x] `make typecheck` passes

---

### Task 3.4 — Add integration test setup with vcrpy ✅

**Description:**
Set up the integration test infrastructure using vcrpy for recording and replaying HTTP interactions with NetBox. Create shared fixtures, cassettes directory, and document how to record new cassettes. This enables deterministic integration tests without a live NetBox instance.

**Dependencies:** Task 1.5

**Estimated Complexity:** Medium

**Definition of Done:**
- [x] `tests/integration/` directory created with `conftest.py`
- [x] `tests/integration/cassettes/` directory for recorded HTTP interactions
- [x] Shared fixtures: `netbox_client`, `vcr_cassette_dir`, `record_mode`
- [x] `conftest.py` configures vcrpy with auth header filtering
- [x] Documentation in conftest.py on how to record new cassettes
- [x] `pytest -m integration` runs without errors (even with empty cassettes)
- [x] `make typecheck` passes

---

## Epic 4: Docker Containerization

> Create a production-optimized Docker image with multi-stage build and security hardening.

---

### Task 4.1 — Create `.dockerignore` ✅

**Description:**
Create `.dockerignore` to exclude unnecessary files from the Docker build context: `.git`, `tests/`, `docs/`, `__pycache__`, `.ruff_cache`, `.pytest_cache`, `*.egg-info`, `.vscode`, `.idea`.

**Dependencies:** None

**Estimated Complexity:** Low

**Definition of Done:**
- [x] `.dockerignore` exists with comprehensive exclusion list
- [x] `docker build .` context size is minimal (verify with `docker build --no-cache .`)

---

### Task 4.2 — Create multi-stage `Dockerfile` ✅

**Description:**
Create a multi-stage Dockerfile:
- **Stage 1 (`deps`)**: `python:3.11-slim`, copy `pyproject.toml`, install only runtime dependencies
- **Stage 2 (`runtime`)**: `python:3.11-slim`, copy installed packages from `deps`, copy `src/`, create non-root user `nvs` (UID 1000), set `ENTRYPOINT ["nvs-sync"]`

Security: non-root user, minimal base, no dev dependencies, no build tools in final image.

**Dependencies:** Task 4.1

**Estimated Complexity:** Medium

**Definition of Done:**
- [x] `Dockerfile` exists with multi-stage build
- [x] `docker build -t nvs-sync:latest .` succeeds
- [x] `docker run --rm nvs-sync:latest --help` shows CLI help
- [x] Container runs as non-root user (`nvs`, UID 1000)
- [x] Image size is < 200MB (verify with `docker images nvs-sync`)
- [x] No dev dependencies in final image

---

### Task 4.3 — Create `docker-compose.yml` ✅

**Description:**
Create `docker-compose.yml` with an `nvs-sync` service that mounts config directory and accepts environment variables for credentials.

**Dependencies:** Task 4.2

**Estimated Complexity:** Low

**Definition of Done:**
- [x] `docker-compose.yml` defines `nvs-sync` service
- [x] Config directory mounted at `/etc/netbox-vsphere-sync`
- [x] Environment variables: `NVS_VCENTER_USERNAME`, `NVS_VCENTER_PASSWORD`, `NVS_NETBOX_TOKEN`
- [x] `docker compose config` validates successfully

---

### Task 4.4 — Add Docker Makefile targets ✅

**Description:**
Add `docker-build` and `docker-run` targets to the Makefile.

**Dependencies:** Task 4.2, Task 4.3

**Estimated Complexity:** Low

**Definition of Done:**
- [x] `make docker-build` builds the Docker image
- [x] `make docker-run` runs the container with config volume
- [x] `make check` still passes

---

### Task 4.5 — Add remaining Makefile targets ✅

**Description:**
Add `test-unit`, `test-integration`, `build`, and `pre-commit` targets to the Makefile. These are listed in standards.md §10.1 as planned targets.

**Dependencies:** Task 1.4, Task 3.4

**Estimated Complexity:** Low

**Definition of Done:**
- [x] `make test-unit` runs `pytest -m unit`
- [x] `make test-integration` runs `pytest -m integration`
- [x] `make build` runs `python -m build`
- [x] `make pre-commit` runs `pre-commit install`
- [x] `.PHONY` list updated with new targets
- [x] `make check` still passes

---

## Epic 5: CI/CD Pipeline

> Automate linting, type checking, testing, building, and Docker verification on every push and PR.

---

### Task 5.1 — Create GitHub Actions CI workflow ✅

**Description:**
Create `.github/workflows/ci.yml` with jobs:
1. **lint**: `ruff check` + `ruff format --check`
2. **typecheck**: `pyright src/ tests/`
3. **test**: `pytest --cov` with Python 3.11, 3.12, 3.13 matrix
4. **build**: `python -m build` (verify package builds)
5. **docker**: Build Docker image (verify it works)

Triggers: push to `main`, pull requests to `main`.

**Dependencies:** All previous epics (code must be working)

**Estimated Complexity:** High

**Definition of Done:**
- [x] `.github/workflows/ci.yml` exists
- [x] CI runs on push to `main` and PRs
- [x] lint job passes (ruff check + format)
- [x] typecheck job passes (pyright)
- [x] test job passes on Python 3.11, 3.12, 3.13
- [x] build job produces valid package
- [x] docker job builds successfully

---

### Task 5.2 — Create release pipeline ✅

**Description:**
Create `.github/workflows/release.yml` triggered on tag push (`v*`). This pipeline builds the Python package, publishes to PyPI, builds and pushes the Docker image, and creates a GitHub Release with artifacts.

**Dependencies:** Task 5.1, Task 4.2

**Estimated Complexity:** Medium

**Definition of Done:**
- [x] `.github/workflows/release.yml` exists
- [x] Triggers on tag push (`v*`)
- [x] Build job produces Python package (`python -m build`)
- [x] Publish job uploads to PyPI (`twine upload`)
- [x] Docker job builds and pushes image to registry
- [x] Release job creates GitHub Release with package artifacts
- [x] Secrets: `PYPI_TOKEN`, `DOCKERHUB_TOKEN` documented

---

## Epic 6: Documentation

> Write comprehensive README covering installation, usage, configuration, development, and architecture.

---

### Task 6.1 — Rewrite `README.md` ✅

**Description:**
Replace the current minimal README with comprehensive documentation:
- Project badges (Python version, license, CI status)
- Overview / What it does
- Quick Start (pip install + Docker)
- Configuration (YAML, env vars, Vault)
- CLI Usage (commands, flags, examples)
- Development (setup, testing, pre-commit)
- Architecture (brief + link to `docs/`)
- NetBox Permissions (required API tokens)
- License

**Dependencies:** All previous epics (must be complete to document accurately)

**Estimated Complexity:** Medium

**Definition of Done:**
- [x] README has all sections listed above
- [x] Installation instructions work (pip and Docker)
- [x] Configuration examples are valid YAML
- [x] CLI usage examples are accurate
- [x] Development setup instructions work from clean clone
- [x] Links to docs/ are valid

---

### Task 6.2 — Fix documentation inconsistencies ✅

**Description:**
Fix outdated references in architecture.md and SRS.md that don't match the actual implementation.

**Dependencies:** None

**Estimated Complexity:** Low

**Status:** Complete — CLI flags, env vars, Dockerfile, planned command markers, and Makefile targets updated.

**Definition of Done:**
- [x] `architecture.md` §4.4 shows `nvs-sync` CLI with correct flags
- [x] `architecture.md` §6.2 shows multi-stage Dockerfile
- [x] `architecture.md` §2.2 marks unimplemented commands as planned
- [x] `SRS.md` §5.4 shows correct CLI interface
- [x] `SRS.md` FR-014, FR-015 marked as [PLANNED]
- [x] All cross-document links are valid

---

## Dependency Graph

```
Epic 1 (Structure) ─────────────────────┐
  1.1, 1.2, 1.3                          │
  1.4 ──▶ 1.5                            │
                                         │
Epic 2 (Logging) ───────────────────────┤
  2.1 → 2.2 → 2.3                       │
                                         ├──▶ Epic 5 (CI) ──▶ Epic 6 (Docs)
Epic 3 (NetBox Best Practices) ──────────┤
  3.1 ──┐                                │
  3.2 ──┤                                │
  3.3 ──┘ (3.1 + 3.2)                    │
  3.4 (needs 1.5)                        │
                                         │
Epic 4 (Docker) ─────────────────────────┘
  4.1 → 4.2 → 4.3 → 4.4
  4.5 (needs 1.4, 3.4)
  5.2 (needs 5.1, 4.2)
```

---

## Summary

| Epic | Tasks | Estimated Effort |
|------|-------|-----------------|
| 1. Project Structure & Packaging | 6 | ~2 hours |
| 2. Logging & Observability | 3 | ~2 hours |
| 3. NetBox Integration Best Practices | 4 | ~3 hours |
| 4. Docker Containerization | 5 | ~2 hours |
| 5. CI/CD Pipeline | 2 | ~2.5 hours |
| 6. Documentation | 2 | ~1.5 hours |
| **Total** | **22** | **~13 hours** |
