# ADR-020: Rich + structlog Dual Logging

**Status:** Accepted
**Date:** 2026-06-15

## Context

The tool has two distinct output audiences:
1. **Human operators** running the tool interactively — need formatted tables, spinners, colour-coded diffs.
2. **Log aggregators** (Splunk, Loki, ELK) consuming JSON logs — need structured, machine-parseable records.

A single logging library typically serves only one audience well. Using two complementary libraries provides the best experience for both.

## Decision

Use **structlog** for structured JSON logging and **Rich** for interactive console output:

**structlog** (always on):
- JSON-formatted logs to stdout.
- Key-value pairs (event, entity_type, natural_key, duration_ms, error).
- Timestamps in ISO-8601.
- Log level: INFO for normal runs, DEBUG for troubleshooting.

**Rich** (TTY-only):
- Progress spinners during sync phases.
- Tables for diff reports (entity type, action, natural key).
- Colour-coded status (green=created, yellow=updated, red=error, grey=skipped).
- Summary table at end of run.

The `EventLog` (see ADR-013) feeds both output systems: structlog receives each event as a structured log line; Rich receives the aggregated event list for console rendering.

## Consequences

**Positive:**
- Best experience for both human and machine consumers.
- structlog output is aggregator-ready (no parsing required).
- Rich output makes interactive troubleshooting productive.

**Negative:**
- Two logging configurations to maintain.
- Rich output is rate-limited (spinner animations add latency).
- Terminal output must detect TTY vs pipe for automatic Rich fallback.

## Related

- `docs/architecture.md` — Observability: logging strategy.
- `docs/standards.md` — Coding standards: structlog conventions.
- `docs/SRS.md` — NFR-10 (structured logging), NFR-11 (human-readable reports).
