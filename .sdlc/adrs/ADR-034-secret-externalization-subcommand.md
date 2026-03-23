# ADR-034: Externalize-Secrets as a Local CLI Subcommand

## Status

Accepted

## Date

2026-03-23

## Context

REQ-005 calls for an `externalize-secrets` subcommand that reads an Ansible YAML file,
detects hardcoded credentials, and produces two output files:

1. `<name>.externalized.yml` — the original playbook with secret vars removed and a
   `vars_files:` entry pointing at the secrets file.
2. `secrets.yml` (or a user-specified path) — the extracted credential variables.

The question is where this logic should live: server-side in the Primary engine (called
via gRPC like `scan` and `format`), or client-side in the CLI itself.

### Forces in tension

- **ADR-001** says all inter-service communication uses gRPC.
- **ADR-024** documents that the CLI is currently a "thin client" that delegates
  engine work to the Primary over gRPC.
- The `externalize-secrets` operation is purely a **local file transformation**:
  it reads one file, writes two files, and the only non-trivial logic is (a) running
  gitleaks and (b) editing YAML structure with ruamel.yaml — both of which are already
  available in the CLI process.
- Routing this through the Primary would require new proto messages, a new RPC, a new
  server-side handler, and a file-upload/download round trip — for a transformation
  that has no need of the engine's scan pipeline, venv management, or validator
  orchestration.
- The `gitleaks` binary is a runtime dependency already used by the gitleaks validator
  container; the CLI can invoke it directly in the same way
  `apme_engine.validators.gitleaks.scanner.run_gitleaks` does.
- `ruamel.yaml` is already a declared project dependency (`pyproject.toml`).

## Decision

**Implement `externalize-secrets` as a local-only CLI subcommand with no gRPC dependency.**

The subcommand invokes `run_gitleaks` from the existing scanner module directly (running
the `gitleaks` binary locally) and processes YAML using `ruamel.yaml`. It writes output
files locally. No Primary connection is required.

## Alternatives Considered

### Alternative 1: Route through Primary via a new gRPC RPC

**Description**: Add an `ExternalizeSecrets` RPC to the Primary proto. The CLI uploads
the file, the server runs gitleaks + YAML processing, and returns the two output file
contents.

**Pros**:
- Consistent with ADR-001 (gRPC for all engine work)
- Server-side execution works in the web gateway context

**Cons**:
- Significant proto churn: new request/response messages, new RPC, regenerate stubs
- The file transformation itself is trivial — no engine capabilities are needed
- Adds latency and network round-trip for a purely local operation
- Web gateway context is handled separately (REQ-003/ADR-029); CLI use case is local

**Why not chosen**: The operational overhead is disproportionate to the complexity
of the transformation. The CLI already has direct access to all necessary libraries.

### Alternative 2: Implement server-side, reuse via the `fix` session workflow

**Description**: Treat secret externalization as a Tier-1 auto-fix remediator inside
the `fix` subcommand.

**Pros**:
- Reuses the existing fix pipeline scaffolding

**Cons**:
- The fix pipeline is convergence-loop oriented (scan → patch → re-scan)
- Secret externalization is a one-shot, non-idempotent transformation (removing vars)
- The output is two files, not a patch on one file — doesn't fit the patch model
- Would require significant changes to the fix pipeline's result model

**Why not chosen**: Structural mismatch between the fix pipeline's patch model and the
two-file output this feature requires.

## Consequences

### Positive

- Zero proto changes; no service rebuild required
- Works without a running daemon/pod (developer-friendly)
- Reuses `run_gitleaks` and `ruamel.yaml` — no new dependencies
- Consistent with how the formatter can run locally per ADR-024's observation that the
  CLI naturally accumulates local capabilities

### Negative

- Cannot be invoked from the web gateway or operator UI without a separate implementation
- Diverges slightly from the ADR-001 "gRPC for all engine work" principle; justified
  by the purely local nature of the operation

### Neutral

- If a web/gateway path is needed in the future (REQ-003 / ADR-029), it can add a
  dedicated endpoint that calls the same underlying Python logic

## Implementation Notes

- Reuse `apme_engine.validators.gitleaks.scanner.run_gitleaks(tmpdir)` — copy the source
  file to a temp directory, scan it, then map findings back by line number.
- Use `ruamel.yaml` round-trip mode (`YAML(typ="rt")`) to preserve comments and
  formatting in the externalized output file.
- Map gitleaks findings to YAML variable names via line-number overlap:
  for each key in `vars:`, check whether any gitleaks finding's `[StartLine, EndLine]`
  intersects the key's line range `[key_line, next_key_line - 1]`.
- Insert `vars_files:` immediately before `vars:` using `CommentedMap.insert()`.
- The `--secrets-file` option (default: `secrets.yml`) names the file placed under the
  same directory as the source file unless an absolute path is given.
- The original source file is never modified.

## Related Decisions

- ADR-010: Gitleaks as gRPC Validator — reuses `run_gitleaks` module
- ADR-024: Thin CLI with Local Daemon Mode — contextualizes local-CLI operations
- ADR-028: Session-Based Fix Workflow — explains why this is NOT part of the fix pipeline

---

## Revision History

| Date | Author | Change |
|------|--------|--------|
| 2026-03-23 | Bradley A. Thornton | Initial proposal and acceptance |
