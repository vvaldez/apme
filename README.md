# Ansible Forward (APME Engine)

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

> **WARNING: Proof-of-Concept / Rapid Prototype**
>
> This project is in an early, experimental state. APIs, CLI flags, gRPC
> contracts, configuration formats, and internal architecture are all
> **unstable and subject to breaking changes without notice**. There are no
> stability guarantees, no migration paths between versions, and no
> backward-compatibility commitments at this time.
>
> Do not depend on any interface or behavior remaining the same between
> commits. If you are evaluating this project, expect things to move fast
> and break often.

Ansible Policy & Modernization Engine — a multi-validator static analysis platform for Ansible content. It parses playbooks, roles, collections, and task files into a structured hierarchy, then fans validation out in parallel across four independent backends (OPA/Rego, native Python, Ansible-runtime, and Gitleaks) to produce a single, unified list of violations.

## Architecture at a glance

```
┌─────────┐      gRPC       ┌────────────┐      gRPC (parallel)      ┌────────────┐
│   CLI   │ ──────────────► │  Primary   │ ──────────────────────►   │   Native   │ :50055
│ (on-the │  ScanRequest    │ (orchestr) │   ValidateRequest         │  (Python)  │
│  -fly)  │  chunked fs     │            │ ┌─────────────────────►   ├────────────┤
└─────────┘                 │   Engine   │ │                         │    OPA     │ :50054
     ▲                      │  ┌──────┐  │ │  ┌──────────────────►   │  (Rego)    │
     │   ScanResponse       │  │parse │  │ │  │                      ├────────────┤
     │   violations         │  │annot.│  │ │  │  ┌───────────────►   │  Ansible   │ :50053
     └──────────────────────│  │hier. │  ├─┘  │  │                   │ (runtime)  │
                            │  └──────┘  ├────┘  │                   ├────────────┤
                            └────────────┘───────┘                   │  Gitleaks  │ :50056
                                 │                                   │ (secrets)  │
                            ┌────┴────┐                              └────────────┘
                            │ Galaxy  │ :8765
                            │ Proxy   │ (PEP 503)
                            └─────────┘
```

Six app containers, one pod. All inter-service communication is gRPC. The Galaxy Proxy serves Ansible collections as Python wheels (PEP 503). The CLI is run on-the-fly with the project directory mounted. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full design.

## Key features

- **Single parse, multiple validators** — the engine parses Ansible content once and produces a hierarchy payload + scandata; validators consume it independently.
- **Parallel fan-out** — Primary calls Native, OPA, Ansible, and Gitleaks validators concurrently via `asyncio.gather()`; total latency = max(validators), not sum.
- **Unified gRPC contract** — every validator implements the same `Validator` service (`validate.proto`); adding a new validator means implementing one RPC.
- **100+ rules** across four backends: OPA Rego (L002–L025, R118), native Python (L026–L056, R101–R501), Ansible runtime (L057–L059, M001–M004), Gitleaks (SEC:* — 800+ secret patterns).
- **Secret scanning** — Gitleaks binary wrapped in gRPC; scans all project files for hardcoded credentials, API keys, private keys. Vault-encrypted files and Jinja2 expressions are automatically filtered.
- **Secret externalization** — `externalize-secrets` subcommand extracts hardcoded credentials from `vars:` blocks into a separate vars file, inserts `vars_files:` into the playbook, and never modifies the source. Vault-ready output with a `--dry-run` mode for safe auditing.
- **Multi ansible-core version support** — the Primary orchestrator builds session-scoped venvs per ansible-core version (UV-cached); argspec and deprecation checks run against the requested version. Venvs are shared read-only with validators via a `/sessions` volume.
- **Structured diagnostics** — every validator reports per-rule timing data via the gRPC contract; use `-v` for summaries or `-vv` for full per-rule breakdowns.
- **Galaxy Proxy** — converts Ansible Galaxy collection tarballs into pip-installable Python wheels (PEP 503/427); collections are `uv pip install`'d into session venvs, leveraging standard Python caching and dependency resolution.
- **YAML formatter** — normalize indentation, key ordering, Jinja spacing, and tab removal with comment preservation. Idempotent by design; runs as a pre-pass before semantic fixes.
- **Colocated tests** — every rule has a `*_test.py` (native), `*_test.rego` (OPA), or `.md` doc with violation/pass examples usable as integration tests.

## Quick start

### Local development (no containers)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -e ".[dev]"

# Run a scan
apme-scan scan /path/to/playbook-or-project

# JSON output
apme-scan scan --json .

# Diagnostics: summary + top 10 slowest rules
apme-scan scan -v .

# Diagnostics: full per-rule breakdown
apme-scan scan -vv .

# Format YAML files (show diff)
apme-scan format /path/to/project

# Format and apply changes in place
apme-scan format --apply /path/to/project

# CI check mode (exit 1 if changes needed)
apme-scan format --check /path/to/project

# Full fix pipeline: format → idempotency check → re-scan → modernize
apme-scan fix --apply /path/to/project

# AI-assisted fixes (requires Abbenay daemon)
apme-scan fix --ai --apply /path/to/project

# AI with auto-approve (no interactive review)
apme-scan fix --ai --auto-approve --apply /path/to/project

# Extract hardcoded secrets to a separate vars file (non-destructive)
apme-scan externalize-secrets playbook.yml

# Dry-run: audit without writing any files
apme-scan externalize-secrets --dry-run playbook.yml

# Custom secrets file path
apme-scan externalize-secrets --secrets-file vault/credentials.yml playbook.yml
```

### Container deployment (Podman)

```bash
# Build all images
./containers/podman/build.sh

# Start the pod (Primary + Native + OPA + Ansible + Gitleaks + Galaxy Proxy)
./containers/podman/up.sh

# Scan a project (CLI container, on-the-fly)
cd /path/to/your/project
/path/to/apme/containers/podman/run-cli.sh

# With options
containers/podman/run-cli.sh scan --json .
```

### Health check

```bash
apme-scan health-check
```

## AI escalation

APME can escalate Tier 2 violations (no deterministic transform) to an AI provider for proposed fixes. This requires the [Abbenay](https://github.com/redhat-developer/abbenay) daemon.

### Prerequisites

```bash
pip install apme-engine[ai]

# Consumer auth token (required for inline policy)
export APME_ABBENAY_TOKEN="your-token"
```

### Binary daemon

```bash
# Start Abbenay daemon (auto-discovers socket at $XDG_RUNTIME_DIR/abbenay/)
abbenay daemon start
# Or from a Sea binary:
./abbenay-daemon-linux-x64 start

# Set consumer auth token for inline policy (required)
export APME_ABBENAY_TOKEN="your-token"

# Fix with AI
apme-scan fix --ai --apply /path/to/project
```

### Container daemon

See the [Abbenay container documentation](https://github.com/redhat-developer/abbenay/blob/main/docs/CONTAINER.md) for full container setup instructions.

```bash
# Pull the pre-built multi-arch image (amd64 + arm64)
podman pull ghcr.io/redhat-developer/abbenay:latest

# Standalone: Abbenay defaults to gRPC on :50051.
# When running inside the APME pod, use -p 50057:50051 to avoid
# colliding with APME Primary (also :50051).
podman run -d --name abbenay \
  -v ./config.yaml:/home/abbenay/.config/abbenay/config.yaml:ro \
  -e OPENROUTER_API_KEY="$OPENROUTER_API_KEY" \
  -p 8787:8787 -p 50057:50051 \
  ghcr.io/redhat-developer/abbenay:latest

# Point APME at the Abbenay container via gRPC TCP
APME_ABBENAY_ADDR=localhost:50057 apme-scan fix --ai --apply .
```

### CLI flags

| Flag | Description |
|------|-------------|
| `--ai` | Enable AI escalation (opt-in) |
| `--auto-approve` | Approve all AI proposals without prompting (CI mode) |
| `--max-passes N` | Max convergence passes (default: 5) |
| `--apply` | Write changes in place |
| `--check` | Exit 1 if changes would be made (CI mode) |
| `--json` | Output structured data payloads as JSON |
| `--session ID` | Explicit session ID for venv reuse (default: auto-derived from project root) |

### Remediation flow

1. **Tier 1 (deterministic)**: convergence loop applies transforms until stable
2. **Tier 2 (AI)**: remaining violations are sent to the AI provider one at a time; each proposal is re-validated, cleaned with Tier 1 transforms, and retried with feedback if needed
3. **Interactive review**: accepted proposals are applied (or shown as diffs without `--apply`)
4. **Tier 3 (manual)**: violations that neither transforms nor AI can fix are reported for human review

## Secret externalization

The `externalize-secrets` subcommand detects hardcoded credentials in Ansible YAML
files (using Gitleaks) and separates them into a standalone vars file — without
touching the original. This is the first step toward vault-encrypting or secrets-manager-backed
credentials.

### How it works

1. Gitleaks scans the source file for hardcoded credentials (AWS keys, GitHub PATs,
   passwords, private keys, and 800+ other patterns).
2. Each detected variable is identified by mapping gitleaks line numbers back to the
   YAML `vars:` block, including multi-line values like PEM keys.
3. Two output files are written — the original is never modified:

| File | Contents |
|------|----------|
| `<name>.externalized.yml` | Playbook with secret vars removed; `vars_files:` inserted |
| `secrets.yml` (or `--secrets-file`) | Extracted key-value pairs, vault-ready |

### Example

Given `playbook.yml` with hardcoded credentials in `vars:`:

```yaml
- name: Deploy app
  hosts: all
  vars:
    aws_access_key_id: "AKIA1234567890ABCDEF"
    db_password: "SuperSecret123!"
    app_name: "my-app"          # not a secret — stays inline
  tasks: ...
```

Running `apme-scan externalize-secrets playbook.yml` produces:

**`playbook.externalized.yml`**
```yaml
- name: Deploy app
  hosts: all
  vars_files:
    - secrets.yml
  vars:
    app_name: "my-app"
  tasks: ...
```

**`secrets.yml`**
```yaml
# Externalized secrets — store securely, do not commit to version control
# Generated from: playbook.yml
# Consider encrypting this file with: ansible-vault encrypt secrets.yml
aws_access_key_id: "AKIA1234567890ABCDEF"
db_password: "SuperSecret123!"
```

### Usage

```bash
# Extract secrets from a single playbook
apme-scan externalize-secrets playbook.yml

# Audit without writing (dry-run)
apme-scan externalize-secrets --dry-run playbook.yml

# Custom secrets file name/path
apme-scan externalize-secrets --secrets-file vault/credentials.yml playbook.yml

# Process all YAML files in a directory
apme-scan externalize-secrets ./roles/my_role/
```

### Options

| Option | Description |
|--------|-------------|
| `target` | Path to a YAML file or directory (default: `.`) |
| `--secrets-file FILE` | Filename for extracted secrets (default: `secrets.yml`) |
| `--dry-run` | Report what would be extracted without writing any files |

### Next steps after externalization

```bash
# Encrypt the generated secrets file with Ansible Vault
ansible-vault encrypt secrets.yml

# Or store individual values in a secrets manager and reference via lookup:
# db_password: "{{ lookup('aws_ssm', '/myapp/db_password') }}"
```

### Prerequisites

The `gitleaks` binary must be installed and on `PATH`. See the
[Gitleaks installation guide](https://github.com/gitleaks/gitleaks#installing).

## Scaling

Scale pods, not services within a pod. Each pod is a self-contained stack that can process a scan request end-to-end. For more throughput, run multiple pods behind a load balancer. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md#scaling).

## Tests

```bash
pip install -e ".[dev]"

# Unit + colocated rule tests
pytest

# With coverage
pytest --cov=src/apme_engine --cov-report=term-missing --cov-fail-under=36

# End-to-end integration (requires Podman + built images)
pytest -m integration tests/integration/test_e2e.py
```

## Project layout

```
proto/apme/v1/          gRPC service definitions (.proto)
src/apme/v1/            generated Python gRPC stubs
src/apme_engine/
  ├── engine/           ARI-based scanner (parse, annotate, hierarchy)
  │   └── annotators/   per-module risk annotators
  ├── validators/
  │   ├── base.py       Validator protocol + ScanContext
  │   ├── native/       Python rules (L026–L056, R101–R501)
  │   ├── opa/          Rego bundle (L002–L025, R118)
  │   ├── ansible/      Ansible-runtime rules (L057–L059, M001–M004)
  │   └── gitleaks/     Gitleaks wrapper (SEC:* — secret detection)
  ├── daemon/           gRPC server implementations
  ├── venv_manager/     Session-scoped venv lifecycle (VenvSessionManager)
  ├── remediation/      Tier 1 transforms + AI escalation
  ├── formatter.py      YAML formatter (phase 1 remediation)
  ├── cli/              CLI entry point (scan, format, fix, health-check)
  └── runner.py         scan orchestration
src/apme_gateway/       API gateway (FastAPI, REST/WebSocket, SQLite)
src/galaxy_proxy/       Galaxy → PEP 503 wheel proxy
frontend/               React operator UI (Vite + TypeScript)
containers/             Containerfiles + Podman pod config
docs/                   architecture, design, rule mapping
tests/                  unit, integration, rule doc coverage
```

## Documentation

| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | Container topology, gRPC contracts, data flow, scaling model |
| [DATA_FLOW.md](docs/DATA_FLOW.md) | Request lifecycle, engine pipeline, serialization formats |
| [DEPLOYMENT.md](docs/DEPLOYMENT.md) | Podman pod setup, configuration, troubleshooting |
| [DEVELOPMENT.md](docs/DEVELOPMENT.md) | Adding rules, proto generation, testing, code organization |
| [DESIGN_VALIDATORS.md](docs/DESIGN_VALIDATORS.md) | Validator abstraction rationale and design decisions |
| [LINT_RULE_MAPPING.md](docs/LINT_RULE_MAPPING.md) | Complete rule ID cross-reference (L/M/R/P) |
| [ANSIBLELINT_COVERAGE.md](docs/ANSIBLELINT_COVERAGE.md) | Coverage vs ansible-lint, gap analysis |
| [RULE_DOC_FORMAT.md](docs/RULE_DOC_FORMAT.md) | Rule `.md` format for docs + integration tests |
| [ANSIBLE_CORE_MIGRATION.md](docs/ANSIBLE_CORE_MIGRATION.md) | ansible-core 2.19/2.20 breaking changes and rule mapping |
| [PODMAN_OPA_ISSUES.md](docs/PODMAN_OPA_ISSUES.md) | Podman rootless troubleshooting |
| [DESIGN_REMEDIATION.md](docs/DESIGN_REMEDIATION.md) | Remediation engine: transform registry, AI escalation, convergence loop |
| [DESIGN_AI_ESCALATION.md](docs/DESIGN_AI_ESCALATION.md) | AI integration: Abbenay provider, hybrid validation loop, prompt engineering |
| [RESEARCH_REVIEW.md](docs/RESEARCH_REVIEW.md) | Analysis of early research concepts and roadmap pull-ins |
| [DESIGN_DASHBOARD.md](docs/DESIGN_DASHBOARD.md) | Dashboard & presentation layer: API gateway, REST/WebSocket, persistence, auth, frontend |
| [ADRs](.sdlc/adrs/) | Architecture Decision Records — key design decisions with context, alternatives, and rationale |

## Roadmap

### Phase 1 — YAML Formatter (done)

`format` subcommand with `--diff`/`--apply`/`--check` modes, idempotency guarantees, gRPC `Format` RPC.

### Phase 2 — Modernization Engine

- `fix` subcommand: format → idempotency gate → re-scan → semantic transforms.
- **`is_finding_resolvable()` partition**: each rule declares a `fixable` attribute; the fix pipeline splits findings into auto-fixable vs manual/AI.
- **Multi-pass convergence loop**: scan → fix → rescan → repeat until stable or oscillation detected (max N passes).
- **`module_metadata.json`**: machine-readable module lifecycle data (introduced, deprecated, removed, parameter renames) generated from `ansible-doc` across core versions. M-series rules become data-driven lookups instead of per-rule hardcoded logic.

### Phase 2a — New Rules

- **Secret scanning** (done) — Gitleaks validator: 800+ patterns for credentials, API keys, private keys via dedicated container + gRPC wrapper. Vault and Jinja filtering built in.
- **Secret externalization** (done) — `externalize-secrets` subcommand: non-destructive extraction of hardcoded credentials into a separate vars file with `vars_files:` stitching. See [ADR-034](.sdlc/adrs/ADR-034-secret-externalization-subcommand.md).
- **EE compatibility rules** (R505–R507): undeclared collections, system path assumptions, undeclared Python deps. Requires static `ee_baseline.json` from `ee-supported-rhel9` inspection.
- **Version auto-detection**: infer source Ansible version from playbook signals (short-form module names → ≤2.9, `include:` → ≤2.7, `tower_*` → ≤2.13). Auto-scope M-rules without an explicit `--ansible-core-version` flag.

### Phase 3 — AI Integration (in progress)

- **Abbenay daemon** as the AI backend via gRPC: `pip install apme-engine[ai]`.
- **AIProvider Protocol** (`ADR-024`): pluggable abstraction for LLM providers; `AbbenayProvider` is the default.
- **Hybrid validation loop**: AI proposals are re-scanned through APME validators, cleaned up with Tier 1 transforms, and retried with feedback if issues persist (max 2 attempts).
- **Interactive review** (`--ai` flag): per-fix diff review (y/n/skip) like `git add -p`, or `--ci` for automatic application.
- **Structured best practices**: curated Ansible guidelines injected into prompts for higher-quality fixes.
- **Preflight checks**: auto-discover Abbenay daemon socket, health check before AI calls.
- See [DESIGN_AI_ESCALATION.md](docs/DESIGN_AI_ESCALATION.md) for the full design.

### Phase 4 — Web UI (in progress)

Operator UI for scan + fix sessions, health monitoring, and findings management. API gateway (FastAPI), REST/WebSocket API, persistence (SQLite), and React frontend. See [DESIGN_DASHBOARD.md](docs/DESIGN_DASHBOARD.md) for the full design.

## License

Apache-2.0
