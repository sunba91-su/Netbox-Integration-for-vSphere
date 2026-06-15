# ADR-034: Dependency Injection via CLI Wiring

**Status:** Accepted
**Date:** 2026-06-15

## Context

The application and domain layers should not instantiate their dependencies (ACLs, repositories, clients). Doing so would:
- Tightly couple layers to concrete implementations.
- Make testing harder (cannot substitute mocks).
- Violate the Dependency Rule (domain depending on infrastructure).

A composition root wires all dependencies together at application startup. The question is where to locate it.

## Decision

The **CLI layer is the composition root**. Click commands instantiate and wire all dependencies:

```python
@click.command()
@click.option("--config", required=True)
def sync(config: str) -> None:
    # 1. Load configuration
    config_obj = ConfigLoader(config).load()

    # 2. Create infrastructure
    vcenter_client = VCenterClient(config_obj.vcenter)
    netbox_client = NetBoxClient(config_obj.netbox)
    vault_client = VaultClient(config_obj.vault) if config_obj.vault.enabled else None

    # 3. Create ACLs (infrastructure → domain translation)
    vsphere_acl = VSphereACL()
    netbox_acl = NetBoxACL()

    # 4. Create repositories
    site_repo = NetBoxSiteRepository(netbox_client, netbox_acl)
    device_repo = NetBoxDeviceRepository(netbox_client, netbox_acl)

    # 5. Create collectors
    collector = VSphereCollector(vcenter_client, vsphere_acl)

    # 6. Create sync engine
    engine = SyncEngine(
        collector=collector,
        repos={...},
        config=config_obj.sync,
    )

    # 7. Run
    engine.run()
```

No DI framework (no inject, no dependency-injector). Plain manual wiring keeps dependencies explicit and debuggable.

## Consequences

**Positive:**
- Clean layer separation — no infrastructure imports in domain/application.
- All wiring in one place — easy to understand.
- No DI framework dependency.
- Easy to inject mocks for testing (just instantiate with mock repos).

**Negative:**
- Manual wiring is verbose for many dependencies.
- Adding a new repository requires updating the composition root.
- Deep dependency chains are harder to construct manually.

## Related

- `docs/architecture.md` — Component Diagram: CLI as composition root.
- `docs/standards.md` — Layer dependency rules.
- `docs/domains.md` — Repository port definitions.
