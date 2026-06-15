# AGENTS.md — Netbox-Integration-for-vSphere

## Project Overview

Python CLI tool for one-way, cron-driven synchronisation from VMware vSphere
into NetBox (4.5+). vSphere is the authoritative source for compute, storage,
and network topology.

---

## Tech Stack

| Component | Technology | Purpose |
|---|---|---|
| Language | Python 3.11+ | Runtime |
| vSphere SDK | PyVmomi | Read vCenter inventory |
| NetBox Client | pynetbox >=7.0 | Read/write NetBox API |
| Vault Client | hvac >=2.0 | Secrets management (optional) |
| CLI Framework | Click | Command-line interface |
| Config Validation | Pydantic v2 | YAML + env + vault config |
| Logging | Rich + structlog | Console + structured output |
| Testing | pytest + vcrpy | Unit + recorded integration tests |
| Linting | Ruff | Style, imports, conventions |
| Type Checking | Pyright (strict) | Static type safety |
| Packaging | pyproject.toml (PEP 621) | Build and distribution |
| Automation | Makefile | Common command recipes |
| Pre-commit | pre-commit | Pre-commit lint + typecheck |

---

## Project Structure

```
netbox-vsphere-sync/
├── pyproject.toml              # Dependencies, metadata, entry points (PEP 621)
├── Makefile                    # Common command recipes
├── README.md                   # Quickstart and usage
├── .gitignore
├── ruff.toml                   # Linter + formatter configuration
├── pyrightconfig.json          # Strict type-checker configuration
├── .pre-commit-config.yaml     # Pre-commit hooks
├── Dockerfile                  # Multi-stage production image (planned)
├── .dockerignore               # Docker build context exclusions (planned)
├── docker-compose.yml          # Local development/testing (planned)
│
├── docs/                       # System documentation
│   ├── vision.md               # Architecture vision and strategy
│   ├── domains.md              # DDD domain model and bounded contexts
│   ├── architecture.md         # System context, components, deployment
│   ├── SRS.md                  # Software requirements specification
│   ├── standards.md            # Coding, git, testing, security standards
│   └── project-plan.md         # Epics and tasks for development
│
├── src/
│   └── netbox_vsphere_sync/    # Main package
│       ├── __init__.py
│       ├── domain/             # Core domain: entities, VOs, events, ports
│       │   ├── model/          # Entities, value objects
│       │   │   ├── vsphere/    # vSphere-side domain objects
│       │   │   └── config/     # Pydantic config models
│       │   ├── events.py       # Domain event hierarchy
│       │   ├── ports.py        # Repository protocols (typing.Protocol)
│       │   ├── exceptions.py   # Domain exception hierarchy
│       │   └── constants.py    # Constants (dependency order, defaults)
│       ├── application/        # Use cases: sync engine, diff engine
│       │   ├── sync_engine.py
│       │   ├── diff_engine.py
│       │   ├── dependency_resolver.py
│       │   ├── bootstrapper.py
│       │   └── event_log.py
│       ├── infrastructure/     # Adapters: NetBox ACL, vSphere ACL, Vault
│       │   ├── config/
│       │   │   ├── loader.py
│       │   │   ├── lock_manager.py
│       │   │   └── secret_resolver.py
│       │   ├── netbox/
│       │   │   ├── acl.py
│       │   │   ├── client.py
│       │   │   └── repositories/
│       │   ├── vsphere/
│       │   │   ├── acl.py
│       │   │   ├── client.py
│       │   │   └── collector.py
│       │   └── vault/
│       │       ├── acl.py
│       │       └── client.py
│       ├── cli/                # Click commands
│       │   ├── __main__.py
│       │   ├── app.py
│       │   └── commands/
│       │       └── sync.py     # Only implemented command
│       └── report/             # Observability: reports, logging
│           ├── console.py
│           └── generator.py
│
└── tests/                      # Mirrors src/ structure
    ├── conftest.py
    ├── domain/
    │   └── model/
    ├── application/
    ├── infrastructure/
    │   ├── netbox/
    │   └── vsphere/
    └── cli/
```

---

## Build Commands

| Command | Action |
|---|---|
| `make install` | Install package + dev dependencies |
| `make lint` | Run ruff linter + formatter check |
| `make typecheck` | Run pyright type checker |
| `make test` | Run pytest with coverage |
| `make check` | Run lint + typecheck + test |
| `make run` | Run the sync CLI |
| `make clean` | Remove build artifacts |

---

## Commit Policy

### Format

```
type(scope): short description (max 72 chars)

[optional body — explain what and why, not how]

[optional footer — BREAKING CHANGE, Closes #issue]
```

### Types

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

### Scopes

`domain`, `infra`, `cli`, `report`, `vsphere`, `netbox`, `vault`, `config`, `docs`

### Examples

```
feat(domain): add VLAN aggregate with natural key matching
fix(infra): handle pynetbox pagination timeout
docs: move vision and domains to docs/
chore: add pre-commit hooks for ruff and pyright
```

---

## Branch Strategy

Trunk-based development with short-lived feature branches.

```
main ─────●─────────●───────────────●─────────▶
          │         │               │
          ├─ feat/x ┘               │
          │         └─ fix/y ───────┘
                    └─ chore/z ─────┘
```

### Rules

| Rule | Detail |
|---|---|
| `main` is always deployable | No direct pushes — all changes via PR |
| Feature branches | Short-lived (< 3 days preferred) |
| Branch naming | `feat/xxx`, `fix/xxx`, `docs/xxx`, `chore/xxx` |
| PR required | Every change reviewed before merge |
| Merge strategy | Squash merge (keep main history clean) |
| No develop branch | Trunk-based; main is the single integration branch |
| Rebase before merge | Keep a linear, readable history |

---

## Documentation

| Document | Purpose |
|---|---|
| `docs/vision.md` | Architecture vision, data model, strategic decisions |
| `docs/domains.md` | DDD bounded contexts, aggregates, events, ports |
| `docs/architecture.md` | System context, components, API, security, deployment |
| `docs/SRS.md` | Functional and non-functional requirements, acceptance criteria |
| `docs/standards.md` | Coding, git, testing, security standards |
| `docs/project-plan.md` | Epics and tasks for development |

---

## Workflow for Agents

1. Read `docs/vision.md` first to understand the full architecture.
2. Read `docs/domains.md` to understand the domain model and bounded contexts.
3. Read `docs/architecture.md` for component, API, and deployment design.
4. Read `docs/SRS.md` for functional and non-functional requirements.
5. Read `docs/standards.md` for coding, git, and testing standards.
6. Follow the project structure — code goes in the correct layer (domain,
   application, infrastructure, cli, report).
7. Use Conventional Commits for every commit.
8. Create a feature branch (`feat/xxx`) before making changes.
9. Run `make check` before committing (lint + typecheck + test).
10. Keep PRs small and focused on a single concern.
