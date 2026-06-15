# ADR-023: pytest + vcrpy Testing

**Status:** Accepted
**Date:** 2026-06-15

## Context

The tool interacts with three external APIs (vSphere, NetBox, Vault) that are not always available in test environments. Integration tests need deterministic, reproducible HTTP responses.

Options:
1. Live API testing — requires infrastructure, slow, non-deterministic.
2. Mocking (unittest.mock) — easy but couples tests to implementation details.
3. Record/replay (vcrpy) — records real HTTP interactions, replays from cassette files.

vcrpy records requests and responses as YAML cassette files. Replayed responses are byte-identical to the original, giving deterministic, realistic integration tests without live APIs.

## Decision

**pytest** as the test runner with **vcrpy** for HTTP record/replay:

- **Domain tests:** Pure unit tests — no vcrpy, no mocking of external APIs. Test business logic directly.
- **Application tests:** Mock ports (Protocol implementations) — no vcrpy. Test orchestration logic.
- **Infrastructure tests:** vcrpy for recorded NetBox/Vault interactions. PyVmomi tests use `unittest.mock` (no vcrpy for SOAP).
- **CLI tests:** Click CliRunner with mocked infrastructure layer.

Test strategy by layer:
| Layer | Approach | Target Coverage |
|---|---|---|
| Domain | Pure unit tests | >= 95% |
| Application | Mock ports | >= 90% |
| Infrastructure | vcrpy / mock | >= 70% |
| CLI | CliRunner + mock | >= 80% |

## Consequences

**Positive:**
- Deterministic integration tests — no reliance on live APIs.
- Cassettes serve as documentation of API interactions.
- Fast test execution (no network latency).
- Per-layer strategy targets the right testing approach for each concern.

**Negative:**
- Cassettes are sensitive to API version changes (must re-record).
- Cassettes may contain sensitive data (must be scrubbed before committing).
- PyVmomi (SOAP) cannot use vcrpy — requires manual mocking.

## Related

- `docs/standards.md` — Testing strategy.
- `docs/domains.md` — Testing approach per bounded context.
- `SRS.md` — NFR-12 (testability).
