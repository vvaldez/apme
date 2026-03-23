# REQ-005: Secret Externalization Subcommand

## Metadata

- **Phase**: PHASE-003 - Enterprise Dashboard
- **Status**: Approved
- **Created**: 2026-03-23

## Overview

An `externalize-secrets` CLI subcommand that detects hardcoded secrets in Ansible YAML
files (using gitleaks) and extracts them into a separate vars file without modifying the
original. The command produces two output files: an externalized playbook that references
the secrets file via `vars_files`, and a secrets file containing the extracted credentials.

## User Stories

**As a Security Engineer**, I want to externalize hardcoded secrets from Ansible playbooks
so that credentials are stored separately from playbook logic and can be vault-encrypted
or managed by a secrets manager.

**As a Platform Engineer**, I want a non-destructive extraction workflow so that I can
review the outputs before replacing the original files.

**As a CI/CD Operator**, I want a `--dry-run` mode so that I can audit secrets without
writing any files.

## Acceptance Criteria

### Scenario: Single file with secrets

- **GIVEN**: An Ansible playbook with hardcoded credentials in the `vars:` block
- **WHEN**: `apme-scan externalize-secrets playbook.yml` is run
- **THEN**:
  - `playbook.externalized.yml` is written with all detected secret vars removed
  - `vars_files: [secrets.yml]` is inserted into each affected play
  - `secrets.yml` is written containing the extracted key-value pairs
  - The original `playbook.yml` is not modified

### Scenario: Dry-run shows what would change

- **GIVEN**: A playbook with secrets
- **WHEN**: `apme-scan externalize-secrets --dry-run playbook.yml` is run
- **THEN**: No files are written; stdout reports which secrets would be extracted

### Scenario: Custom secrets file path

- **GIVEN**: A playbook with secrets
- **WHEN**: `apme-scan externalize-secrets --secrets-file vault/credentials.yml playbook.yml`
- **THEN**: The secrets are written to `vault/credentials.yml` and `vars_files` references that path

### Scenario: No secrets detected

- **GIVEN**: A clean playbook with no hardcoded credentials
- **WHEN**: `apme-scan externalize-secrets playbook.yml` is run
- **THEN**: No files are written; user is informed that no secrets were found

### Scenario: Mixed vars block

- **GIVEN**: A play whose `vars:` block contains both secret and non-secret variables
- **WHEN**: `apme-scan externalize-secrets playbook.yml` is run
- **THEN**: Only the secret variables are moved to `secrets.yml`; non-secret vars remain inline

### Scenario: Gitleaks not installed

- **GIVEN**: The `gitleaks` binary is not present
- **WHEN**: `apme-scan externalize-secrets playbook.yml` is run
- **THEN**: An actionable error message is printed; exit code 1

## Inputs / Outputs

### Inputs

| Name | Type | Description | Required |
|------|------|-------------|----------|
| `target` | Path | YAML file to process | Yes |
| `--secrets-file` | str | Filename/path for extracted secrets (default: `secrets.yml`) | No |
| `--dry-run` | flag | Show what would change without writing files | No |

### Outputs

| Name | Type | Description |
|------|------|-------------|
| `<name>.externalized.yml` | File | Source playbook with secret vars removed and `vars_files` added |
| `secrets.yml` (or `--secrets-file`) | File | Extracted secret key-value pairs, vault-ready |

## Behavior

### Happy Path

1. CLI runs gitleaks on the target file (in a temp directory) to detect secrets.
2. Gitleaks findings are mapped back to YAML variable names using line numbers.
3. For each affected play: secret vars are removed from `vars:`; `vars_files:` is inserted
   referencing the secrets output file.
4. If the `vars:` block becomes empty after extraction, it is removed.
5. The externalized YAML and the secrets file are written.
6. A summary is printed: number of secrets extracted, file paths created.

### Edge Cases

| Case | Handling |
|------|----------|
| `vars_files` already present in play | Append the secrets file reference; do not duplicate |
| All vars are secrets → `vars:` becomes empty | Remove the empty `vars:` block entirely |
| Multi-line secret value (e.g., PEM key) | Detected via gitleaks line-range overlap with YAML key range |
| Jinja2 references in vars | Filtered by the existing gitleaks wrapper (not extracted) |
| Vault-encrypted files | Filtered by the existing gitleaks wrapper (skipped silently) |
| `secrets.yml` already exists | Overwrite with a warning on stderr |

### Error Conditions

| Error | Cause | Response |
|-------|-------|----------|
| Target not found | Path does not exist | Stderr message, exit 1 |
| Not a playbook | File is not a YAML list of plays | Stderr warning, skip file |
| gitleaks not installed | Binary missing from PATH | Stderr message "gitleaks binary not found — install gitleaks to use this command", exit 1 |

## Dependencies

- REQ-003: Security & Compliance (gitleaks integration foundation)
- ADR-010: Gitleaks as gRPC Validator (reuses `run_gitleaks` scanner module)
- ADR-034: Externalize-Secrets as a Local CLI Subcommand
- `ruamel.yaml` (already a project dependency)
- `gitleaks` binary (runtime dependency, same as the gitleaks validator)
