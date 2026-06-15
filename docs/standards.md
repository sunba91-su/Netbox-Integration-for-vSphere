# Project Standards: netbox-vsphere-sync

> Coding, workflow, and governance standards for the project.

---

## Table of Contents

1. [Folder Structure](#1-folder-structure)
2. [Coding Standards](#2-coding-standards)
3. [Git Strategy](#3-git-strategy)
4. [Branch Naming](#4-branch-naming)
5. [Commit Convention](#5-commit-convention)
6. [Testing Strategy](#6-testing-strategy)
7. [Security Requirements](#7-security-requirements)
8. [Linting & Formatting](#8-linting--formatting)
9. [Documentation Standards](#9-documentation-standards)
10. [Build Commands](#10-build-commands)

---

## 1. Folder Structure

### 1.1 Top-Level

```
netbox-vsphere-sync/
├── pyproject.toml              # Dependencies, metadata, entry points (PEP 621)
├── Makefile                    # Common command recipes
├── README.md                   # Quickstart and usage
├── LICENSE                     # Apache 2.0
├── .gitignore
├── ruff.toml                   # Linter + formatter configuration
├── pyrightconfig.json          # Strict type-checker configuration
├── .pre-commit-config.yaml     # Pre-commit hooks
├── .github/workflows/          # CI pipeline (GitHub Actions)
├── docs/                       # System documentation
│   ├── vision.md               # Architecture vision and strategy
│   ├── domains.md              # DDD domain model, bounded contexts
│   ├── architecture.md         # System, component, API, deployment design
│   ├── SRS.md                  # Software requirements specification
│   └── standards.md            # This file — project standards
├── src/                        # Source code
│   └── netbox_vsphere_sync/
│       ├── __init__.py
│       ├── domain/             # Core domain (pure Python, no infra imports)
│       ├── application/        # Use cases (sync engine, diff engine)
│       ├── infrastructure/     # Adapters (NetBox, vSphere, Vault, config)
│       ├── cli/                # Click commands
│       └── report/             # Observability (reports, logging)
└── tests/                      # Mirrors src/ structure
    ├── __init__.py
    ├── conftest.py
    ├── domain/
    ├── application/
    ├── infrastructure/
    └── cli/
```

### 1.2 Source Package Structure

```
src/netbox_vsphere_sync/
├── __init__.py                 # Version, __all__, null export
├── domain/
│   ├── __init__.py
│   ├── model/                  # Entities, value objects
│   │   ├── __init__.py
│   │   ├── natural_key.py
│   │   ├── site.py
│   │   ├── cluster.py
│   │   ├── host.py
│   │   ├── network.py
│   │   ├── inventory.py
│   │   ├── vsphere/            # vSphere-side domain objects
│   │   │   ├── __init__.py
│   │   │   ├── datacenter.py
│   │   │   ├── cluster.py
│   │   │   ├── host.py
│   │   │   ├── portgroup.py
│   │   │   ├── vmknic.py
│   │   │   ├── datastore.py
│   │   │   └── hardware.py
│   │   └── config/             # Pydantic config models
│   │       ├── __init__.py
│   │       ├── vsphere.py
│   │       ├── netbox.py
│   │       ├── vault.py
│   │       ├── sync.py
│   │       └── vlan.py
│   ├── events.py               # Domain event hierarchy
│   ├── ports.py                # Repository protocols (typing.Protocol)
│   ├── exceptions.py           # Domain exception hierarchy
│   └── constants.py            # Constants (dependency order, defaults)
├── application/
│   ├── __init__.py
│   ├── sync_engine.py          # Pipeline orchestrator
│   ├── diff_engine.py          # Create/update/unchanged computation
│   ├── dependency_resolver.py  # Topological sort engine
│   ├── bootstrapper.py         # Prerequisite metadata creator
│   └── event_log.py            # Domain event collector
├── infrastructure/
│   ├── __init__.py
│   ├── netbox/
│   │   ├── __init__.py
│   │   ├── acl.py              # Anti-corruption layer (domain ↔ API)
│   │   ├── client.py           # pynetbox wrapper
│   │   └── repositories/       # Per-entity repository implementations
│   │       ├── __init__.py
│   │       ├── site.py
│   │       ├── cluster.py
│   │       ├── device.py
│   │       ├── vlan.py
│   │       ├── interface.py
│   │       ├── ip_address.py
│   │       └── inventory_item.py
│   ├── vsphere/
│   │   ├── __init__.py
│   │   ├── acl.py              # Anti-corruption layer (PyVmomi ↔ domain)
│   │   └── collector.py        # Paginated property collector
│   ├── vault/
│   │   ├── __init__.py
│   │   ├── acl.py              # Anti-corruption layer (hvac ↔ secrets)
│   │   └── client.py           # hvac wrapper
│   └── config/
│       ├── __init__.py
│       ├── loader.py           # YAML + env + CLI → AppConfig
│       └── secret_resolver.py  # Vault → env var merge
├── cli/
│   ├── __init__.py
│   ├── __main__.py             # python -m entry point
│   ├── app.py                  # Click group with global options
│   └── commands/
│       ├── __init__.py
│       ├── sync.py
│       ├── check.py
│       ├── bootstrap.py
│       └── config.py
└── report/
    ├── __init__.py
    ├── generator.py            # SyncReport from SyncRun
    └── console.py              # Rich console rendering
```

### 1.3 Test Structure

```
tests/
├── __init__.py
├── conftest.py                 # Session-scoped fixtures, plugin registration
├── domain/
│   ├── __init__.py
│   ├── test_events.py
│   ├── test_natural_key.py
│   └── model/
│       ├── __init__.py
│       ├── test_site.py
│       ├── test_cluster.py
│       ├── test_host.py
│       ├── test_network.py
│       └── test_inventory.py
├── application/
│   ├── __init__.py
│   ├── test_sync_engine.py
│   ├── test_diff_engine.py
│   └── test_dependency_resolver.py
├── infrastructure/
│   ├── __init__.py
│   ├── netbox/
│   │   ├── __init__.py
│   │   └── test_repositories.py
│   └── vsphere/
│       ├── __init__.py
│       └── test_collector.py
└── cli/
    ├── __init__.py
    └── test_commands.py
```

### 1.4 Layer Import Rules

| Layer | Imports From | Does NOT Import |
|---|---|---|
| CLI | Application, Domain, Infrastructure | — |
| Application | Domain, Ports (Protocol only) | CLI, Infrastructure |
| Domain | Nothing (pure Python stdlib) | CLI, Application, Infrastructure |
| Infrastructure | Domain, Ports | CLI, Application |
| Report | Domain, Application | — |

---

## 2. Coding Standards

### 2.1 Python Version

- **Target:** Python 3.11+
- Features allowed: `match`/`case`, `X | Y` union syntax, `type` aliases, `@dataclass`, `typing.Protocol`
- Features prohibited: `typing.List`/`Dict`/`Optional` (use `list`/`dict`/`X | None`)

### 2.2 Type Annotations

```python
"""All functions must have type annotations on parameters and return types."""
```

- Pyright in **strict** mode
- No `Any` without an inline `# type: ignore[no-any-explicit]` comment AND justification
- Use `type` for aliases:
  ```python
  type ConnectionState = Literal["connected", "disconnected", "notResponding", "maintenance"]
  ```
- Use `Self` return type for factory classmethods:
  ```python
  @classmethod
  def from_name(cls, name: str) -> Self: ...
  ```
- Use `override` decorator for protocol implementations:
  ```python
  from typing import override

  class NetBoxSiteRepository(SiteRepository):
      @override
      def find_all(self, **filters) -> list[Site]: ...
  ```

### 2.3 Data Class Conventions

| Pattern | Code | Notes |
|---|---|---|
| Value Object | `@dataclass(frozen=True)` | Immutable, equality by value, hashable |
| Entity | `@dataclass` | Mutable, equality by identity/natural key |
| Domain Event | `@dataclass(frozen=True)` | Immutable, timestamped at creation |
| Config | `pydantic.BaseModel` | Validation, env var support, serialization |

### 2.4 Repository Ports

```python
"""All repository ports use typing.Protocol (structural subtyping)."""

from typing import Protocol, Optional

class SiteRepository(Protocol):
    def find_all(self) -> list[Site]: ...
    def find_by_name(self, name: str) -> Optional[Site]: ...
    def upsert(self, site: Site) -> Site: ...
```

### 2.5 Docstrings

- **Google style** for public APIs
- One-line docstrings for trivial getters/setters
- Omit docstrings for `__init__`, `__post_init__`, test functions (use readable names instead)
- Required sections for complex functions: `Args:`, `Returns:`, `Raises:`

```python
def compute_device_diff(
    desired: list[HostInfo],
    existing: list[Device],
) -> list[tuple[str, Optional[Device], Optional[HostInfo]]]:
    """Compare vSphere hosts against NetBox devices.

    Args:
        desired: Live hosts from vSphere PropertyCollector.
        existing: Current devices from NetBox REST API.

    Returns:
        List of (action, netbox_device, vsphere_host) tuples where
        action is "create", "update", or "skip".

    Raises:
        DiffError: If a natural key collision is detected.
    """
```

### 2.6 Naming Conventions

| Element | Convention | Example |
|---|---|---|
| Packages | `snake_case` | `netbox_vsphere_sync` |
| Modules | `snake_case` | `sync_engine.py` |
| Classes | `PascalCase` | `SyncEngine`, `VSphereACL` |
| Functions | `snake_case` | `compute_diff` |
| Variables | `snake_case` | `host_count` |
| Constants | `UPPER_SNAKE_CASE` | `DEPENDENCY_ORDER` |
| Private (`_`) | Single leading underscore | `_should_update` |
| Type aliases | `PascalCase` | `type ConnectionState = ...` |
| Protocols | `PascalCase` (no `I` or `ABC` prefix) | `SiteRepository` |

### 2.7 Error Handling

```python
"""All domain exceptions inherit from SyncError."""

class SyncError(Exception):
    """Base exception for all sync errors."""

class VSphereConnectionError(SyncError):
    """vCenter is unreachable or authentication failed."""

class NetBoxAPIError(SyncError):
    """NetBox API returned an error or is unreachable."""

class VaultAuthError(SyncError):
    """Vault authentication failed or secret path missing."""

class ConfigurationError(SyncError):
    """Config validation failed or secret resolution failed."""

class DiffError(SyncError):
    """Unexpected condition during diff computation."""
```

- Never catch bare `except:`
- Log the error, then raise domain exception
- Infrastructure layer wraps external exceptions:

```python
try:
    result = self._api.dcim.devices.get(name=host_name)
except pynetbox.RequestError as e:
    raise NetBoxAPIError(f"Failed to fetch device {host_name}: {e}") from e
```

### 2.8 Logging

```python
"""structlog for structured JSON logging."""

import structlog

logger = structlog.get_logger(__name__)
logger.info("sync.start", run_id=run_id, mode=mode)
logger.error("sync.failed", run_id=run_id, error=str(e))
```

- **NEVER log credentials.** Passwords, tokens, secret IDs must be filtered.
- Use structlog's `structlog.dev.ConsoleRenderer` for dev, `structlog.processors.JSONRenderer` for production
- Structured fields: `run_id`, `entity_type`, `entity_name`, `action`, `duration`

### 2.9 Comments

- No comments that explain WHAT (the code should be self-documenting)
- Comments are for WHY — rationale, trade-offs, business rules
- No dead code (commented-out code). Delete it.

```python
# Bad — explains what:
# Increment the counter by 1
count += 1

# Good — explains why:
# Use PATCH not PUT because NetBox returns 412 on PUT for stale objects
```

---

## 3. Git Strategy

### 3.1 Model

Trunk-based development with short-lived feature branches.

```
main ─────●─────────●───────────────●─────────▶
          │         │               │
          ├─ feat/x ┘               │
          │         └─ fix/y ───────┘
                    └─ chore/z ─────┘
```

### 3.2 Rules

| Rule | Detail |
|---|---|
| `main` is always deployable | No direct pushes — all changes via PR |
| Feature branches | Short-lived (< 3 days preferred) |
| Rebase before merge | Keep a linear, readable history |
| Merge strategy | **Squash merge** (one commit per PR into main) |
| No `develop` branch | Trunk-based; main is the single integration branch |
| PR required | Every change reviewed before merge |

### 3.3 Workflow

```
1. Branch from main:    git checkout -b feat/vlan-sync
2. Work + commit:       git commit -m "feat(vlan): add port group sync"
3. Rebase on main:      git fetch origin && git rebase origin/main
4. Push:                git push -u origin feat/vlan-sync
5. Create PR:           gh pr create --fill
6. Merge (squash):      gh pr merge --squash
7. Delete branch:       git branch -D feat/vlan-sync
```

---

## 4. Branch Naming

### 4.1 Convention

```
<type>/<short-description>

Examples:
  feat/vlan-sync
  fix/pagination-timeout
  docs/architecture
  chore/pre-commit-hooks
  ci/github-actions
  refactor/sync-engine
  test/integration-tests
```

### 4.2 Types

| Type | When to Use |
|---|---|
| `feat/` | New feature or capability |
| `fix/` | Bug fix |
| `docs/` | Documentation only |
| `chore/` | Maintenance (deps, CI, config, tooling) |
| `ci/` | CI/CD pipeline changes |
| `refactor/` | Code change that neither fixes nor adds |
| `test/` | Adding or updating tests |

- Use kebab-case for descriptions: `feat/vlan-sync`, not `feat/vlan_sync` or `feat/VLAN_SYNC`
- Keep descriptions short (< 40 chars recommended)

---

## 5. Commit Convention

### 5.1 Format

```
type(scope): short description (max 72 chars)

[optional body — explain WHAT and WHY, not HOW]

[optional footer — BREAKING CHANGE, Closes #issue]
```

### 5.2 Types

| Type | When to Use |
|---|---|
| `feat` | New feature or capability |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `test` | Adding or updating tests |
| `chore` | Maintenance (deps, CI, config, tooling) |
| `style` | Formatting, whitespace (no logic change) |
| `ci` | CI/CD pipeline changes |
| `build` | Build system or dependency changes |

### 5.3 Scopes

`domain`, `infra`, `cli`, `report`, `vsphere`, `netbox`, `vault`, `config`, `docs`

### 5.4 Rules

- Subject line: max 72 characters, lowercase, no trailing period
- **Imperative mood:** "add", "fix", "remove" — not "added", "fixed", "removed"
- Body wraps at 72 characters
- Body explains WHAT changed and WHY, not HOW
- Footer for breaking changes: `BREAKING CHANGE: ...`
- Footer for issue references: `Closes #123`

### 5.5 Examples

```
feat(domain): add VLAN aggregate with natural key matching

Clusters and VLANs are both namespaced by site. The natural key
now includes site_name to prevent collisions across datacenters.

Closes #42
```

```
fix(infra): handle pynetbox pagination timeout

pynetbox's default timeout (60s) is insufficient for large
inventory reads. Increased to 120s and added retry logic.

Closes #55
```

```
chore: add pre-commit hooks for ruff and pyright

Enforce linting and type checking before every commit to
reduce CI failures and improve code quality.
```

---

## 6. Testing Strategy

### 6.1 Framework & Tools

| Tool | Purpose |
|---|---|
| `pytest` | Test runner, fixtures, parameterization |
| `pytest-cov` | Coverage reporting (target: >= 80%) |
| `vcrpy` | Record/replay HTTP for deterministic NetBox tests |
| `pytest-mock` | Monkeypatch/mock integration |
| `click.testing.CliRunner` | CLI acceptance tests |

### 6.2 Test Structure

```
tests/
├── conftest.py          # Session fixtures, vcr config, plugin registration
├── pytest.ini           # Or in pyproject.toml: markers, addopts
├── domain/              # Mirror of src/netbox_vsphere_sync/domain/
├── application/         # Mirror of src/netbox_vsphere_sync/application/
├── infrastructure/      # Mirror of src/netbox_vsphere_sync/infrastructure/
└── cli/                 # Mirror of src/netbox_vsphere_sync/cli/
```

### 6.3 Testing by Layer

| Layer | Test Type | Mocking | Focus |
|---|---|---|---|
| **Domain** | Unit tests | No mocks needed | Value object invariants, entity equality, natural key matching, event creation |
| **Application** | Unit tests | Mock repository ports (Protocol stubs) | Sync ordering, diff correctness, bootstrapper logic, event emission |
| **Infrastructure** | Integration tests | vcrpy for NetBox, pytest fixtures for vSphere, hvac mock | ACL translation, pagination, error wrapping, retry logic |
| **CLI** | Acceptance tests | Full mock stack via CliRunner | Flag parsing, command wiring, exit codes, output format |

### 6.4 Test File & Function Naming

```
File:  test_<module_name>.py
       test_site.py, test_sync_engine.py, test_collector.py

Function: test_<function_name>_<scenario>_<expected_outcome>
          test_create_duplicate_key_raises_error
          test_find_all_with_pagination_returns_all
          test_bootstrap_creates_missing_metadata
```

### 6.5 Fixture Guidelines

- Session-scoped: expensive shared resources (vcr cassette directories)
- Module-scoped: per-test-class setup (mock clients)
- Function-scoped: temporary data (entity instances, diff results)
- Conftest: shared fixtures (mock Site, mock Device, etc.)

```python
# tests/conftest.py
import pytest

@pytest.fixture(scope="session")
def vcr_config():
    return {"filter_headers": [("authorization", "****")]}

@pytest.fixture
def mock_site() -> Site:
    return Site(name="DC1", slug=Slug.from_name("DC1"))

@pytest.fixture
def mock_host() -> HostInfo:
    return HostInfo(
        name="esxi-01a.example.com",
        datacenter_name="DC1",
        cluster_name="ClusterA",
        version=ESXiVersion(version="8.0.3", build="123456"),
        connection_status=ConnectionStatus(state="connected"),
        power_state=PowerState(state="poweredOn"),
        cpu=CpuInfo(cores=32, threads=64, model="Xeon Gold 6438M+", vendor="Intel"),
        memory=MemoryBytes(274877906944),
        mor=ManagedObjectRef(type="HostSystem", value="host-123"),
    )
```

### 6.6 Markers

```python
# pyproject.toml
[tool.pytest.ini_options]
markers = [
    "unit: Pure unit tests (no external dependencies).",
    "integration: Tests requiring external API mocking.",
    "slow: Tests that take > 1 second.",
    "vcr: Tests using recorded HTTP cassettes.",
]
```

```python
@pytest.mark.unit
def test_slug_from_name_converts_correctly(): ...

@pytest.mark.integration
def test_netbox_site_repository(): ...

@pytest.mark.vcr("sites")
def test_netbox_fetch_all_sites(): ...
```

### 6.7 Coverage Targets

| Metric | Target |
|---|---|
| Line coverage | >= 80% |
| Branch coverage | >= 70% |
| Domain layer | >= 95% |
| Application layer | >= 90% |
| Infrastructure layer | >= 70% |
| CLI layer | >= 80% |

### 6.8 Run Commands

```bash
make test          # Full test suite with coverage
make test-unit     # pytest -m unit
make test-integration  # pytest -m integration
pytest --cov-report=html  # HTML coverage report
pytest -k "vlan"   # Run only VLAN-related tests
```

---

## 7. Security Requirements

### 7.1 Credential Handling

```
Resolution order (highest to lowest):

  1. CLI flags           --vcenter-pass '...'
  2. Environment vars     NVS_VCENTER_PASS
  3. Vault secrets        kv-v2/vcenter/creds → VCENTER_PASS
  4. YAML config file     vcenter.password
  5. Defaults             None (fails with actionable error)
```

| Rule | Implementation |
|---|---|
| Never hardcode | No secrets in source code. Config uses `${VAR}` interpolation for env vars. |
| Never log | structlog processor masks keys: `password`, `token`, `secret`. Log shows `****`. |
| Never write to disk | Credentials exist only in process memory. No credential files written. |
| Config files | May reference env vars (`${VCENTER_USER}`) but never contain plaintext secrets. |

### 7.2 TLS Configuration

| Endpoint | Default | Override |
|---|---|---|
| vCenter | `verify_ssl: true` | `--no-verify-vcenter` flag or `vcenter.verify_ssl: false` |
| NetBox | `verify_ssl: true` | `--no-verify-netbox` flag or `netbox.verify_ssl: false` |
| Vault | `ssl_verify: true` | `vault.ssl_verify: false` |

### 7.3 Vault Token Management

- TTL: 60 minutes (configurable via Vault policy)
- Auto-renew: at 90% of TTL (triggers `renew_token()` before each secret read)
- Fallback: if Vault is unreachable, fall back to env vars with WARNING log
- Supported auth methods: `token`, `approle`, `kubernetes`

### 7.4 Lock File

```
Location:  /tmp/nvs-sync.lock
Content:   PID (integer)

Acquisition:
  1. If lock exists and PID is alive → exit with warning (code 0)
  2. If lock exists and PID is stale → overwrite, proceed
  3. If no lock → create with current PID

Release:
  - atexit handler (normal exit)
  - signal handler (SIGTERM, SIGINT)
  - Stale PID detection on next run
```

### 7.5 NetBox Permissions

The NetBox API token requires:

| Endpoint | Permissions |
|---|---|
| `/api/dcim/sites/` | `view_site`, `add_site`, `change_site` |
| `/api/dcim/devices/` | `view_device`, `add_device`, `change_device` |
| `/api/dcim/interfaces/` | `view_interface`, `add_interface`, `change_interface` |
| `/api/dcim/inventory-items/` | `view_inventoryitem`, `add_inventoryitem`, `change_inventoryitem` |
| `/api/dcim/manufacturers/` | `view_manufacturer`, `add_manufacturer` |
| `/api/dcim/device-roles/` | `view_devicerole`, `add_devicerole` |
| `/api/virtualization/clusters/` | `view_cluster`, `add_cluster`, `change_cluster` |
| `/api/ipam/vlans/` | `view_vlan`, `add_vlan` |
| `/api/ipam/ip-addresses/` | `view_ipaddress`, `add_ipaddress` |
| `/api/extras/custom-fields/` | `view_customfield`, `add_customfield` |

### 7.6 Security Acceptance Criteria

| ID | Criterion |
|---|---|
| AC-017 | Credentials never appear in log output |
| AC-018 | TLS verification enabled by default |
| AC-019 | Vault token auto-renews before expiry |
| AC-020 | No secrets in source code or config files |

---

## 8. Linting & Formatting

### 8.1 Ruff Configuration

```toml
# ruff.toml
target-version = "py311"
line-length = 88

[lint]
select = [
    "E",     # pycodestyle errors
    "W",     # pycodestyle warnings
    "F",     # pyflakes
    "I",     # isort
    "N",     # pep8-naming
    "UP",    # pyupgrade (target py311)
    "RUF",   # ruff-specific
    "B",     # flake8-bugbear
]

[lint.per-file-ignores]
"tests/*" = ["N802"]  # allow test_ prefixed function names

[format]
quote-style = "double"
indent-style = "space"
line-ending = "lf"
```

### 8.2 Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.9.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
  - repo: local
    hooks:
      - id: pyright
        name: pyright
        entry: pyright
        language: system
        types: [python]
```

### 8.3 Enforcement

| Command | Scope | Run At | Fail On |
|---|---|---|---|
| `ruff check` | All `.py` files | Pre-commit + CI | Any lint error |
| `ruff format --check` | All `.py` files | Pre-commit + CI | Formatting diff |
| `pyright --strict` | `src/` only | Pre-commit + CI | Type error |
| `make check` | Full pipeline | Before merge | Any failure |

---

## 9. Documentation Standards

### 9.1 Document Map

| Document | Purpose | Audience | Format |
|---|---|---|---|
| `docs/vision.md` | Architecture vision, data model, strategic decisions | All stakeholders | Markdown |
| `docs/domains.md` | DDD bounded contexts, aggregates, events, ports | Developers | Markdown |
| `docs/architecture.md` | System context, components, API, security, deployment | Operators, developers | Markdown |
| `docs/SRS.md` | Functional and non-functional requirements | PM, QA, developers | Markdown |
| `docs/standards.md` | This file — coding, git, testing, security standards | All contributors | Markdown |
| `README.md` | Quickstart, install, basic usage | End users | Markdown |

### 9.2 Document Rules

- All docs in `docs/` directory with `.md` extension
- Use GitHub-Flavored Markdown
- Use tables for structured data, code blocks for examples
- Keep diagrams in ASCII art (no embedded images/charts)
- Link between related documents (e.g., architecture.md links to vision.md)
- Update documentation when code changes

---

## 10. Build Commands

### 10.1 Makefile

| Command | Action |
|---|---|
| `make install` | Install package + dev dependencies (`pip install -e ".[dev]"`) |
| `make lint` | Run ruff linter (`ruff check src/ tests/`) |
| `make format` | Run ruff formatter (`ruff format src/ tests/`) |
| `make typecheck` | Run pyright (`pyright --strict src/`) |
| `make test` | Run pytest with coverage (`pytest --cov=netbox_vsphere_sync`) |
| `make test-unit` | Run unit tests only (`pytest -m unit`) |
| `make test-integration` | Run integration tests only (`pytest -m integration`) |
| `make check` | Run lint + typecheck + test (the full gate) |
| `make build` | Build distribution packages (`python -m build`) |
| `make clean` | Remove build artifacts (`rm -rf dist/ build/ .pytest_cache/`) |
| `make run` | Run the sync CLI (`netbox-vsphere-sync sync --dry-run`) |
| `make pre-commit` | Install pre-commit hooks (`pre-commit install`) |

---

> **End of Standards.** All contributors must follow these standards.
> Violations found during code review must be corrected before merge.
