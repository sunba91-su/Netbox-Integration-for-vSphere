# ADR-019: Pydantic v2 for Configuration

**Status:** Accepted
**Date:** 2026-06-15

## Context

The tool accepts configuration from multiple sources: YAML files, environment variables, CLI flags, and Vault secrets. The configuration schema is complex (vCenter connection, NetBox connection, sync behaviour, bootstrap options, VLAN allocation, IP role mapping).

A validation framework is needed to:
- Validate types and constraints at load time.
- Provide clear error messages for invalid config.
- Generate documentation / schema automatically.
- Support env var overrides.

## Decision

**Pydantic v2** is used for all configuration models:

```python
class VCenterConfig(BaseModel):
    host: str = Field(..., description="vCenter hostname or IP")
    username: str = Field("", validation_alias="NVS_VCENTER_USERNAME")
    password: SecretStr = Field("", validation_alias="NVS_VCENTER_PASSWORD")
    verify_ssl: bool = True

    @model_validator(mode="after")
    def check_credentials(self) -> "VCenterConfig":
        if not self.username or not self.password.get_secret_value():
            raise ValueError("vCenter credentials required")
        return self
```

- Config hierarchy: `AppConfig` wraps `VCenterConfig`, `NetBoxConfig`, `VaultConfig`, `SyncConfig`, `BootstrapConfig`.
- `Field(validation_alias=...)` enables env var injection.
- `SecretStr` ensures credentials are never accidentally logged.
- `model_validator` enables cross-field validation.
- Config is loaded from YAML, overlaid with env vars, then overlaid with CLI flags.

## Consequences

**Positive:**
- Type-safe configuration with validation.
- Secret handling (no accidental exposure).
- Auto-generated JSON Schema for documentation.
- Env var support built into Pydantic.

**Negative:**
- Pydantic v2 has breaking changes from v1 (requires `model_validator` instead of `@validator`).
- Recursive config models can be complex to write.
- Serialisation/deserialisation round-trips may lose environment variable aliases.

## Related

- `docs/SRS.md` — Config Schema appendix, FR-19.
- `docs/architecture.md` — Config Loader component.
- `docs/standards.md` — Pydantic configuration standards.
