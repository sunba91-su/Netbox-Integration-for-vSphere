# ADR-024: CLI-Only Interface

**Status:** Accepted
**Date:** 2026-06-15

## Context

Some infrastructure synchronisation tools provide a web UI for configuration, monitoring, and manual sync triggering. A web UI introduces significant complexity:
- Web server process management.
- Authentication and authorisation.
- Frontend development (HTML, CSS, JS).
- CSRF, XSS, session management.
- Ongoing maintenance burden.

The tool is designed for cron-based automation — the primary user is a cron daemon, not a human watching a dashboard.

## Decision

The tool exposes a **CLI-only interface** using Click:

```bash
nvs-sync --config /etc/nvs/config.yaml
nvs-sync --config /etc/nvs/config.yaml --dry-run
nvs-sync --config /etc/nvs/config.yaml --prune
nvs-sync --help
```

No web UI, no dashboard, no persistent daemon mode. Results are consumed through:
1. Exit codes (0 = success, 1 = partial failure, 2 = fatal error).
2. Structured stdout logs (aggregator-friendly).
3. Rich console output (interactive use).

## Consequences

**Positive:**
- Simple, scriptable, cron-friendly.
- No web server, no frontend, no auth system.
- Easy to containerise (stateless CLI).

**Negative:**
- No real-time monitoring dashboard.
- Human operators must use CLI or wrap it in their own tools.
- Change preview requires running with `--dry-run`.

## Related

- `docs/architecture.md` — CLI Design: Click commands.
- `docs/SRS.md` — FR-02 (CLI interface).
- `docs/standards.md` — CLI conventions.
