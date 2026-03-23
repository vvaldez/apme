# TASK-001: Implement `externalize-secrets` CLI Subcommand

## Metadata

- **REQ**: REQ-005
- **Status**: Complete
- **Assigned**: 2026-03-23

## Objective

Implement the `externalize-secrets` subcommand for the APME CLI. The subcommand detects
hardcoded secrets in Ansible YAML files using the existing gitleaks scanner, extracts
them to a separate `secrets.yml`, and writes an externalized copy of the source playbook
with `vars_files:` references — without touching the original file.

## Implementation Steps

- [x] Create `src/apme_engine/cli/externalize.py` with:
  - `run_externalize(args)` — main subcommand entry point
  - `externalize_file(source, secrets_path, dry_run)` — core logic
  - `_find_secret_keys(vars_map, secret_ranges)` — map gitleaks ranges to YAML keys
  - `_insert_vars_files(play, ref)` — position `vars_files:` before `vars:`
  - `_build_secrets_yaml(secrets, source_name)` — render secrets file text
- [x] Register `externalize-secrets` subcommand in `src/apme_engine/cli/parser.py`
- [x] Wire up dispatch in `src/apme_engine/cli/__init__.py`
- [x] Write unit tests in `tests/test_externalize.py`
- [x] Create ADR-034 documenting the local-CLI design decision

## Verification

- `apme-scan externalize-secrets examples/secrets_example.yml` produces:
  - `examples/secrets_example.externalized.yml` (no secret values, has `vars_files:`)
  - `examples/secrets.yml` (contains extracted secret key-value pairs)
  - Original `examples/secrets_example.yml` unchanged
- `apme-scan externalize-secrets --dry-run examples/secrets_example.yml` writes no files
- `pytest tests/test_externalize.py` passes
- `ruff check src/apme_engine/cli/externalize.py tests/test_externalize.py` clean
