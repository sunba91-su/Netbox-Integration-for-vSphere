# NetBox vSphere Sync

One-way synchronisation from VMware vSphere into NetBox.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)
[![Ruff](https://img.shields.io/badge/linter-ruff-red.svg)](https://docs.astral.sh/ruff/)
[![Pyright](https://img.shields.io/badge/type%20checker-pyright-blue.svg)]https://github.com/microsoft/pyright)

## Overview

`nvs-sync` is a CLI tool that performs one-way, cron-driven synchronisation from VMware vSphere into NetBox. It reads vCenter inventory (sites, clusters, hosts, VMs, networks, storage) and creates/updates the corresponding objects in NetBox.

**Key characteristics:**

- **One-way sync** — vSphere is the authoritative source; NetBox is the target
- **Idempotent** — running the same sync twice produces no changes
- **No implicit deletions** — orphaned objects are reported, not removed (unless `--prune` is used)
- **Dependency-aware** — objects are created in topological order (site → cluster → device → interface → IP)

## Quick Start

### Prerequisites

- Python 3.11 or later
- Access to a vSphere vCenter instance (read-only is sufficient)
- NetBox 4.5+ with API token
- (Optional) HashiCorp Vault for secrets management

### Installation

```bash
# Clone the repository
git clone https://github.com/sunba91/Netbox-Integration-for-vSphere.git
cd Netbox-Integration-for-vSphere

# Install in development mode
make install-dev
```

### Create a Configuration File

```yaml
# config.yaml
vcenter:
  host: vc01.example.com
  username: "${VCENTER_USER}"
  password: "${VCENTER_PASS}"
  verify_ssl: true

netbox:
  url: https://netbox.example.com
  token: "${NVS_NETBOX_TOKEN}"
  verify_ssl: true
  timeout: 30

sync:
  dry_run: false
  prune: false
  batch_size: 100

bootstrap:
  custom_fields:
    - name: nvs_managed
      type: boolean
      default: true
```

### Run a Sync

```bash
# With config file
nvs-sync --config config.yaml

# Dry-run mode (preview only)
nvs-sync --config config.yaml --dry-run

# With environment variables for credentials
export NVS_VCENTER_USERNAME="administrator@vsphere.local"
export NVS_VCENTER_PASSWORD="your-password"
export NVS_NETBOX_TOKEN="your-netbox-api-token"

nvs-sync --config config.yaml
```

## Configuration

Configuration is loaded from multiple sources with the following precedence:

1. **CLI flags** (highest priority)
2. **Environment variables**
3. **HashiCorp Vault** (if enabled)
4. **YAML config file** (lowest priority)

### Configuration File

| Section | Description | Required |
|---|---|---|
| `vcenter` | vCenter connection settings | Yes |
| `netbox` | NetBox connection settings | Yes |
| `sync` | Synchronisation behaviour | No |
| `bootstrap` | Prerequisite object creation | No |
| `vault` | Vault integration settings | No |

### Environment Variables

| Variable | Description |
|---|---|
| `NVS_CONFIG` | Path to YAML config file |
| `NVS_VCENTER_USERNAME` | vCenter username |
| `NVS_VCENTER_PASSWORD` | vCenter password |
| `NVS_NETBOX_TOKEN` | NetBox API token |

### Vault Integration

Enable Vault to resolve secrets from HashiCorp Vault:

```yaml
vault:
  enabled: true
  addr: https://vault.example.com:8200
  ssl_verify: true
  auth:
    method: approle
    role_id: "${VAULT_ROLE_ID}"
    secret_id: "${VAULT_SECRET_ID}"
  secrets:
    vcenter:
      path: kv-v2/vcenter/creds
      mount_point: kv-v2
      keys:
        username: VCENTER_USER
        password: VCENTER_PASS
    netbox:
      path: kv-v2/netbox/api-token
      mount_point: kv-v2
      keys:
        token: NVS_NETBOX_TOKEN
```

## CLI Usage

```
Usage: nvs-sync [OPTIONS] COMMAND [ARGS]...

Options:
  -c, --config FILE            Path to YAML config file  [env: NVS_CONFIG]
  --dry-run                    Preview changes without writing
  --prune                      Deactivate orphaned objects
  --vcenter-username TEXT      vCenter username  [env: NVS_VCENTER_USERNAME]
  --vcenter-password TEXT      vCenter password  [env: NVS_VCENTER_PASSWORD]
  --netbox-token TEXT          NetBox API token  [env: NVS_NETBOX_TOKEN]
  --vcenter-insecure           Disable vCenter TLS verification
  --netbox-insecure            Disable NetBox TLS verification
  --help                       Show this message and exit

Commands:
  sync       Run a full synchronisation
```

### Exit Codes

| Code | Meaning |
|---|---|
| `0` | Sync completed successfully |
| `1` | Sync completed with partial errors |
| `2` | Fatal error (connection, config, or runtime) |

## Development

### Setup

```bash
make install-dev
```

This installs the package in editable mode with all dev dependencies and sets up pre-commit hooks.

### Common Commands

| Command | Action |
|---|---|
| `make lint` | Run ruff linter + formatter check |
| `make format` | Auto-fix lint issues + format code |
| `make typecheck` | Run pyright type checker |
| `make test` | Run pytest with verbose output |
| `make test-cov` | Run tests with coverage (80% minimum) |
| `make check` | Run lint + typecheck + test |
| `make run` | Run the sync CLI |
| `make clean` | Remove build artifacts |

### Project Structure

```
src/netbox_vsphere_sync/
├── domain/             # Core domain: entities, value objects, events, ports
├── application/        # Use cases: sync engine, diff engine, bootstrapper
├── infrastructure/     # Adapters: NetBox, vSphere, Vault, config
├── cli/                # Click commands
└── report/             # Observability: reports, logging
```

### Testing

```bash
# Run all tests
make test

# Run with coverage
make test-cov

# Run specific test file
python -m pytest tests/application/test_diff_engine.py -v

# Run tests by marker
python -m pytest -m unit
python -m pytest -m integration
```

## Architecture

The tool follows a clean architecture with clear layer separation:

- **Domain** — Pure business logic, entities, and port definitions (no external dependencies)
- **Application** — Use cases that orchestrate domain logic and infrastructure adapters
- **Infrastructure** — External integrations (NetBox API, vSphere SDK, Vault, config loading)
- **CLI** — User interface layer (Click commands)
- **Report** — Output formatting (Rich console tables, structured logging)

### Sync Flow

1. **Collect** — VSphereCollector reads vCenter inventory
2. **Bootstrap** — Create prerequisite NetBox objects (sites, custom fields, tags)
3. **Resolve** — DependencyResolver orders entities by topological sort
4. **Diff** — DiffEngine compares vSphere source vs NetBox target
5. **Apply** — SyncEngine creates/updates NetBox objects via repositories
6. **Report** — ConsoleReporter renders Rich tables with results

## Roadmap

- [ ] Additional CLI commands (`check`, `bootstrap`, `config`)
- [ ] Docker containerisation
- [ ] CI/CD pipeline (GitHub Actions)
- [ ] Prometheus metrics export
- [ ] Webhook notifications on sync failure

## License

Apache License 2.0 — see [LICENSE](LICENSE) for details.
