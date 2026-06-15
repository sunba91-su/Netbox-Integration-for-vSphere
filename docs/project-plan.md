# Project Plan: Python Best Practices + Docker + CI/CD

## Project Epics & Tasks: Python Best Practices + Docker + CI/CD

---

## Epic 1: Project Structure & Packaging

> Establish clean module boundaries, explicit public interfaces, and proper version management.

---

### Task 1.1 — Add package version and public API exports

**Description:**
Add `__version__ = "0.1.0"` and `__all__` to the root package `__init__.py`. This becomes the single source of truth for the package version, referenced dynamically by `pyproject.toml`.

**Dependencies:** None

**Estimated Complexity:** Low

**Definition of Done:**
- [ ] `src/netbox_vsphere_sync/__init__.py` contains `__version__ = "0.1.0"` and `__all__ = ["__version__"]`
- [ ] `pyproject.toml` uses `dynamic = ["version"]` with `[tool.setuptools.dynamic] version = {attr = "netbox_vsphere_sync.__version__"}`
- [ ] `python -c "import netbox_vsphere_sync; print(netbox_vsphere_sync.__version__)"` prints `0.1.0`

---

### Task 1.2 — Add `__all__` exports to all subpackage `__init__.py` files

**Description:**
Define explicit public APIs for every subpackage using `__all__`. This follows the python-project-structure skill pattern and makes the package's public interface discoverable.

**Dependencies:** None

**Estimated Complexity:** Medium

**Definition of Done:**
- [ ] `domain/__init__.py` exports: entities, value objects, events, ports, exceptions, constants
- [ ] `application/__init__.py` exports: `SyncEngine`, `DiffEngine`, `DependencyResolver`, `Bootstrapper`, `EventLog`
- [ ] `infrastructure/netbox/__init__.py` exports: `NetBoxClient`, `NetBoxACL`, all repositories
- [ ] `infrastructure/vsphere/__init__.py` exports: `VSphereClient`, `VSphereCollector`, `VSphereACL`
- [ ] `infrastructure/vault/__init__.py` exports: `VaultClient`, `VaultACL`
- [ ] `infrastructure/config/__init__.py` exports: `ConfigLoader`, `SecretResolver`, `PidLockManager`
- [ ] `cli/__init__.py` exports: `main`
- [ ] `report/__init__.py` exports: `ReportGenerator`, `ConsoleRenderer`
- [ ] `make typecheck` passes with no new errors

---

### Task 1.3 — Add PEP 561 `py.typed` marker

**Description:**
Create an empty `py.typed` marker file so type checkers (pyright, mypy) recognize this package as typed per PEP 561.

**Dependencies:** None

**Estimated Complexity:** Low

**Definition of Done:**
- [ ] File `src/netbox_vsphere_sync/py.typed` exists (empty)
- [ ] `pyproject.toml` includes `package-data` to include `py.typed` in the distribution

---

### Task 1.4 — Add pytest configuration to `pyproject.toml` ✅ (partial)

**Description:**
Add `[tool.pytest.ini_options]` section with markers (`unit`, `integration`, `slow`, `vcr`) and default `addopts`. This consolidates test configuration into one file.

**Dependencies:** None

**Estimated Complexity:** Low

**Status:** Partially complete — `unit`, `integration`, `slow` markers added. `vcr` marker pending (see Task 1.5).

**Definition of Done:**
- [x] `pyproject.toml` contains `[tool.pytest.ini_options]` with markers and `addopts`
- [ ] `pytest --markers` shows `unit`, `integration`, `slow`, `vcr`
- [x] `make test` passes without regression

---

## Epic 2: Logging & Observability

> Integrate structlog for structured, configurable logging with sensitive data filtering.

---

### Task 2.1 — Create logging configuration module

**Description:**
Create `report/logging_config.py` with a `configure_logging()` function that sets up structlog with console (dev) and JSON (prod) renderers, timestamp formatting, and sensitive key filtering (`password`, `token`, `secret` → `****`). Log level configurable via `NVS_LOG_LEVEL` env var.

**Dependencies:** None

**Estimated Complexity:** Medium

**Definition of Done:**
- [ ] `report/logging_config.py` exists with `configure_logging(log_level, log_format)` function
- [ ] Sensitive key processor masks `password`, `token`, `secret`, `secret_id` fields
- [ ] Console renderer produces human-readable output
- [ ] JSON renderer produces valid JSON
- [ ] Unit test verifies sensitive key filtering works

---

### Task 2.2 — Integrate structlog into core modules

**Description:**
Add structured logging to key modules: `sync_engine.py`, `diff_engine.py`, `bootstrapper.py`, `config/loader.py`, `vsphere/client.py`, `netbox/client.py`, `vault/client.py`. Use `structlog.get_logger(__name__)` pattern. Log sync start/end, entity counts, diff summary, and errors with context.

**Dependencies:** Task 2.1

**Estimated Complexity:** Medium

**Definition of Done:**
- [ ] All listed modules import and use `structlog.get_logger(__name__)`
- [ ] `sync_engine.py` logs: sync start (with dry_run/prune flags), entity counts per type, sync completion (with duration and counts)
- [ ] `netbox/client.py` logs: connection attempt, success/failure
- [ ] `vsphere/client.py` logs: connection attempt, success/failure
- [ ] No credentials appear in any log output
- [ ] `make typecheck` passes
- [ ] `make lint` passes

---

### Task 2.3 — Add `--verbose` and `--log-format` CLI options

**Description:**
Add `--verbose` flag (sets log level to DEBUG) and `--log-format` option (`console` or `json`) to the CLI. Wire these to `configure_logging()`.

**Dependencies:** Task 2.1, Task 2.2

**Estimated Complexity:** Low

**Definition of Done:**
- [ ] `nvs-sync sync --help` shows `--verbose` and `--log-format` options
- [ ] `--verbose` sets log level to DEBUG
- [ ] `--log-format json` produces JSON output
- [ ] `--log-format console` (default) produces human-readable output
- [ ] `NVS_LOG_LEVEL` env var works as fallback
- [ ] `make test` passes

---

## Epic 3: NetBox Integration Best Practices

> Align the NetBox integration with official best practices for performance, reliability, and authentication.

---

### Task 3.1 — Enhance `NetBoxClient` with pagination, brief mode, and timeouts

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
- [ ] `NetBoxClient.__init__` accepts `timeout`, `brief_mode`, `exclude_config_context` params
- [ ] `list_all()` method passes `brief=True` when enabled
- [ ] Device/cluster list calls exclude `config_context` by default
- [ ] Retry logic handles transient errors (max 3 retries, exponential backoff)
- [ ] Existing unit tests still pass
- [ ] `make typecheck` passes

---

### Task 3.2 — Add NetBox configuration options

**Description:**
Extend `NetBoxConfig` Pydantic model with new fields: `brief_mode`, `exclude_config_context`, `request_timeout`, `max_retries`. These have sensible defaults and are configurable via YAML.

**Dependencies:** None

**Estimated Complexity:** Low

**Definition of Done:**
- [ ] `NetBoxConfig` has new fields with defaults: `brief_mode=True`, `exclude_config_context=True`, `request_timeout=120`, `max_retries=3`
- [ ] Existing config loading still works (backwards compatible)
- [ ] YAML config can override these values
- [ ] `make test` passes

---

### Task 3.3 — Update repositories to use new client features

**Description:**
Update all repository implementations in `infrastructure/netbox/repositories/` to pass `brief=True` and `exclude_config_context=True` (where applicable) through the client.

**Dependencies:** Task 3.1, Task 3.2

**Estimated Complexity:** Medium

**Definition of Done:**
- [ ] All repositories pass appropriate flags to `client.list_all()`
- [ ] `device_repository.py` excludes `config_context`
- [ ] `cluster_repository.py` excludes `config_context`
- [ ] Brief mode enabled for all list operations
- [ ] `make test` passes
- [ ] `make typecheck` passes

---

## Epic 4: Docker Containerization

> Create a production-optimized Docker image with multi-stage build and security hardening.

---

### Task 4.1 — Create `.dockerignore`

**Description:**
Create `.dockerignore` to exclude unnecessary files from the Docker build context: `.git`, `tests/`, `docs/`, `__pycache__`, `.ruff_cache`, `.pytest_cache`, `*.egg-info`, `.vscode`, `.idea`.

**Dependencies:** None

**Estimated Complexity:** Low

**Definition of Done:**
- [ ] `.dockerignore` exists with comprehensive exclusion list
- [ ] `docker build .` context size is minimal (verify with `docker build --no-cache .`)

---

### Task 4.2 — Create multi-stage `Dockerfile`

**Description:**
Create a multi-stage Dockerfile:
- **Stage 1 (`deps`)**: `python:3.11-slim`, copy `pyproject.toml`, install only runtime dependencies
- **Stage 2 (`runtime`)**: `python:3.11-slim`, copy installed packages from `deps`, copy `src/`, create non-root user `nvs` (UID 1000), set `ENTRYPOINT ["nvs-sync"]`

Security: non-root user, minimal base, no dev dependencies, no build tools in final image.

**Dependencies:** Task 4.1

**Estimated Complexity:** Medium

**Definition of Done:**
- [ ] `Dockerfile` exists with multi-stage build
- [ ] `docker build -t nvs-sync:latest .` succeeds
- [ ] `docker run --rm nvs-sync:latest --help` shows CLI help
- [ ] Container runs as non-root user (`nvs`, UID 1000)
- [ ] Image size is < 200MB (verify with `docker images nvs-sync`)
- [ ] No dev dependencies in final image

---

### Task 4.3 — Create `docker-compose.yml`

**Description:**
Create `docker-compose.yml` with an `nvs-sync` service that mounts config directory and accepts environment variables for credentials.

**Dependencies:** Task 4.2

**Estimated Complexity:** Low

**Definition of Done:**
- [ ] `docker-compose.yml` defines `nvs-sync` service
- [ ] Config directory mounted at `/etc/netbox-vsphere-sync`
- [ ] Environment variables: `NVS_VCENTER_HOST`, `NVS_VCENTER_USER`, `NVS_VCENTER_PASS`, `NVS_NETBOX_URL`, `NVS_NETBOX_TOKEN`
- [ ] `docker compose config` validates successfully

---

### Task 4.4 — Add Docker Makefile targets

**Description:**
Add `docker-build` and `docker-run` targets to the Makefile.

**Dependencies:** Task 4.2, Task 4.3

**Estimated Complexity:** Low

**Definition of Done:**
- [ ] `make docker-build` builds the Docker image
- [ ] `make docker-run` runs the container with config volume
- [ ] `make check` still passes

---

## Epic 5: CI/CD Pipeline

> Automate linting, type checking, testing, building, and Docker verification on every push and PR.

---

### Task 5.1 — Create GitHub Actions CI workflow

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
- [ ] `.github/workflows/ci.yml` exists
- [ ] CI runs on push to `main` and PRs
- [ ] lint job passes (ruff check + format)
- [ ] typecheck job passes (pyright)
- [ ] test job passes on Python 3.11, 3.12, 3.13
- [ ] build job produces valid package
- [ ] docker job builds successfully

---

## Epic 6: Documentation

> Write comprehensive README covering installation, usage, configuration, development, and architecture.

---

### Task 6.1 — Rewrite `README.md`

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
- [ ] README has all sections listed above
- [ ] Installation instructions work (pip and Docker)
- [ ] Configuration examples are valid YAML
- [ ] CLI usage examples are accurate
- [ ] Development setup instructions work from clean clone
- [ ] Links to docs/ are valid

---

## Dependency Graph

```
Epic 1 (Structure) ─────────────────────┐
                                         │
Epic 2 (Logging) ───────────────────────┤
  2.1 → 2.2 → 2.3                       │
                                         ├──▶ Epic 5 (CI) ──▶ Epic 6 (Docs)
Epic 3 (NetBox Best Practices) ──────────┤
  3.1 ──┐                                │
  3.2 ──┤                                │
  3.3 ──┘ (3.1 + 3.2)                    │
                                         │
Epic 4 (Docker) ─────────────────────────┘
  4.1 → 4.2 → 4.3 → 4.4
```

---

## Summary

| Epic | Tasks | Estimated Effort |
|------|-------|-----------------|
| 1. Project Structure & Packaging | 4 | ~1 hour |
| 2. Logging & Observability | 3 | ~2 hours |
| 3. NetBox Integration Best Practices | 3 | ~2 hours |
| 4. Docker Containerization | 4 | ~1.5 hours |
| 5. CI/CD Pipeline | 1 | ~1.5 hours |
| 6. Documentation | 1 | ~1 hour |
| **Total** | **16** | **~9 hours** |
