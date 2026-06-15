# ADR-038: Layered Test Strategy

**Status:** Accepted
**Date:** 2026-06-15

## Context

Testing a multi-layered application with external API dependencies requires different approaches for different layers. A single testing strategy (e.g., "always mock everything" or "always test live") produces poor results:
- Mocking everything exercises no real integration.
- Testing everything live is slow, non-deterministic, and requires infrastructure.

Each layer has different testing needs:
- **Domain:** Pure business logic — should be fast, exhaustive, and mock-free.
- **Application:** Orchestration logic — needs controlled port responses.
- **Infrastructure:** API interaction — needs realistic HTTP responses.
- **CLI:** Command parsing and output — needs isolated runner.

## Decision

**Per-layer test strategy** with different tools and coverage targets:

| Layer | Approach | Tool | Target Coverage |
|---|---|---|---|
| Domain | Pure unit tests — no mocking | pytest | >= 95% |
| Application | Mock ports (Protocol implementations) | pytest + unittest.mock | >= 90% |
| Infrastructure | vcrpy for HTTP (NetBox, Vault), manual mock for SOAP (PyVmomi) | pytest + vcrpy | >= 70% |
| CLI | Click CliRunner with mocked infra | pytest + CliRunner | >= 80% |
| Integration | End-to-end with recorded NetBox cassettes | pytest + vcrpy | Key flows only |

Test file naming: `test_{module}_{scenario}.py` (e.g., `test_device_repository_find_by_key.py`).

Tests mirror the `src/` directory structure under `tests/`.

## Consequences

**Positive:**
- Right tool for each layer — fast domain tests (95%+ coverage), realistic infra tests.
- vcrpy cassettes provide deterministic HTTP replay.
- Clear coverage targets per layer prevent "coverage fraud" (100% code coverage but poor assertion coverage).

**Negative:**
- Multiple testing patterns increase cognitive load.
- vcrpy cassettes must be scrubbed of secrets before committing.
- PyVmomi (SOAP) has no vcrpy support — must use manual mocking.

## Related

- `docs/standards.md` — Testing strategy.
- `docs/domains.md` — Test approach per bounded context.
- `docs/SRS.md` — NFR-12 (testability), NFR-15 (coverage targets).
