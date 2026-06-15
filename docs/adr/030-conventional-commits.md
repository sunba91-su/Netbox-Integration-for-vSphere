# ADR-030: Conventional Commits

**Status:** Accepted
**Date:** 2026-06-15

## Context

Commit messages should be informative and structured. Without conventions, commit messages range from unhelpful ("fix stuff", "changes") to verbose novels that bury the key change.

Structured commit messages enable:
- Automated changelog generation.
- Semantic versioning inference.
- Release note creation.
- Git history filtering (e.g., "show me all docs changes").

## Decision

All commits follow the **Conventional Commits** format:

```
type(scope): short description (max 72 chars)

[optional body — explain what and why, not how]

[optional footer — BREAKING CHANGE, Closes #issue]
```

**Types:** feat, fix, docs, refactor, test, chore, style, ci, build.

**Scopes:** domain, infra, cli, report, vsphere, netbox, vault, config, docs.

**Examples:**
```
feat(domain): add VLAN aggregate with natural key matching
fix(infra): handle pynetbox pagination timeout
docs: move vision and domains to docs/
chore: add pre-commit hooks for ruff and pyright
```

- Subject line: imperative present tense, no period, max 72 chars.
- Body: explain *what* and *why*, not *how*.

## Consequences

**Positive:**
- Machine-parseable commit history.
- Consistent and informative message format.
- Enables tooling (changelog generation, semver inference).

**Negative:**
- Learning curve for team members unfamiliar with the format.
- Requires `--amend` or squash if a commit message doesn't conform.
- Subject line length limit (72 chars) can be tight for complex changes.

## Related

- `docs/standards.md` — Commit convention.
- `AGENTS.md` — Commit policy.
- `.pre-commit-config.yaml` — commitizen or commitlint (future).
