# APME Standard Operating Procedures

Consolidated best practices for the Ansible Policy & Modernization Engine.

This document synthesizes guidance from `CLAUDE.md`, `AGENTS.md`, `SECURITY.md`, `CONTRIBUTING.md`, `.sdlc/` (workflow, conventions, templates, ADRs), `.agents/skills/`, and `docs/` into a single actionable reference. Industry-standard practices from NIST SSDF, OpenSSF Baseline, SLSA, and GitHub hardening guides are included where the project has gaps.

> **Canonical sources.** This SOP summarizes and links to deeper documents. When a conflict exists, the canonical source wins. For architecture decisions, the relevant ADR is authoritative.

---

## Table of Contents

1. [Security](#1-security)
2. [Development Workflow](#2-development-workflow)
3. [Code Quality Standards](#3-code-quality-standards)
4. [Pre-commit and CI Gates](#4-pre-commit-and-ci-gates)
5. [Git Workflow and PR Process](#5-git-workflow-and-pr-process)
6. [Architectural Invariants](#6-architectural-invariants)
7. [Rule Development](#7-rule-development)
8. [Release Process](#8-release-process)
9. [Industry Alignment and Gap Analysis](#9-industry-alignment-and-gap-analysis)

---

## 1. Security

> This is a **public repository**. Every contributor must treat security as a first-class concern, not an afterthought. This section is intentionally placed first.

**Canonical sources:** [SECURITY.md](SECURITY.md), [CONTRIBUTING.md](CONTRIBUTING.md), [CLAUDE.md](CLAUDE.md), [ADR-019](.sdlc/adrs/ADR-019-dependency-governance.md)

### 1.1 Secrets Management

1. **Never commit secrets.** API keys, tokens, passwords, private keys, `.env` files, Ansible Vault passwords, cloud credentials, kubeconfig files, and database connection strings must never appear in the repository.
2. **Use environment variables or Ansible Vault** for runtime secrets. Provide `.env.example` with placeholder values only.
3. **Pre-commit hooks are mandatory.** The following hooks catch secrets before they reach the repository:
   - `gitleaks` — entropy and regex-based secret detection
   - `detect-secrets` — additional secret patterns with baseline support
   - `bandit` — Python security linting
   - `detect-private-key` — catches key files
4. **Never show secrets in documentation.** Command examples must use environment variables, not literal credentials. Shell history and process lists expose command-line arguments.
5. **Log `[REDACTED]`, not secrets.** Sanitize user input in log output. Never log passwords, tokens, or connection strings.

*Sources: [SECURITY.md](SECURITY.md) "Secrets Management", [CLAUDE.md](CLAUDE.md) "Security", [.agents/skills/pr-review/SKILL.md](.agents/skills/pr-review/SKILL.md) "Secrets in documentation"*

### 1.2 Safe Coding Patterns

1. **No `shell=True` with user input.** Always use list-form `subprocess.run(["cmd", arg])`.
2. **Prevent path traversal.** Resolve paths and verify with `resolved.is_relative_to(allowed_root)` before processing.
3. **Safe YAML loading.** Use `ruamel.yaml` with `typ='safe'` when round-trip is not needed. Never use `yaml.load()` without a safe loader.
4. **Validate all external input.** Protobuf message fields, file paths, and user-provided data must be validated before use.
5. **Custom exception hierarchy.** Use `APMEError` subclasses, not bare `Exception`. Never expose internal stack traces to users.

*Sources: [SECURITY.md](SECURITY.md) "Code Security", [.sdlc/context/conventions.md](.sdlc/context/conventions.md) "Error Handling"*

### 1.3 Container Security

1. **Run as non-root.** All containers must create and switch to a non-root user.
2. **No secrets in `ENV` directives.** Use runtime secrets injection instead.
3. **Pin image tags.** Use specific versions (e.g., `python:3.12-slim-bookworm`), never `:latest`.
4. **Minimize attack surface.** Use `--no-install-recommends`, remove `apt` caches, install only required packages.
5. **Scan images.** Use `trivy` or `grype` to check for vulnerabilities before publishing.

*Source: [SECURITY.md](SECURITY.md) "Container Security"*

### 1.4 Dependency Security

1. **Lock files must be committed.** Always commit `uv.lock` or `requirements.txt` so builds are reproducible.
2. **Review dependency changes in PRs.** Every new or updated dependency requires explicit review.
3. **Run vulnerability scans.** Use `pip-audit` or `safety check` regularly and before releases.
4. **Follow the 7-question checklist** (ADR-019) before adding any new runtime dependency:
   - (1) Complexity — genuinely hard problem or convenience wrapper?
   - (2) Footprint — install size and transitive dependencies?
   - (3) Maintenance health — stars, commit recency, release cadence?
   - (4) Type coverage — ships `py.typed` or has `types-*` stubs?
   - (5) License — compatible with Apache-2.0?
   - (6) Overlap — already covered by an existing dep or internal module?
   - (7) Stdlib alternative — can Python's standard library do this?

*Sources: [SECURITY.md](SECURITY.md) "Dependency Security", [ADR-019](.sdlc/adrs/ADR-019-dependency-governance.md)*

### 1.5 gRPC Security

1. **Use TLS in production.** Insecure channels are acceptable only in local development.
2. **Validate protobuf fields.** Never trust incoming message content without validation.
3. **Set maximum message sizes.** Prevent denial-of-service via oversized payloads.
4. **Implement rate limiting.** Protect services from excessive request volume.

*Source: [SECURITY.md](SECURITY.md) "gRPC Security"*

### 1.6 CI/CD Security

1. **Pin GitHub Actions to commit SHAs**, not mutable tags (`@v4`). Mutable tags allow upstream changes without review. Include a comment noting the original tag.
2. **Never add secrets or publishing steps** to CI without explicit maintainer approval.
3. **Separate build, publish, and deploy duties** to limit blast radius.

*Sources: [.agents/skills/lean-ci/SKILL.md](.agents/skills/lean-ci/SKILL.md), [.agents/skills/pr-review/SKILL.md](.agents/skills/pr-review/SKILL.md) "Supply-chain security"*

### 1.7 Vulnerability Reporting

1. **Do NOT open public GitHub issues** for security vulnerabilities.
2. Report via email (security@[your-domain].com) or GitHub Security Advisories.
3. Include: description, reproduction steps, potential impact, and suggested fix.
4. Response timeline: acknowledgment within 48 hours, initial assessment within 7 days.

*Source: [SECURITY.md](SECURITY.md) "Reporting a Vulnerability"*

### 1.8 Incident Response

1. **Rotate all credentials** immediately.
2. **Audit git history** for leaked secrets.
3. **Notify maintainers** via the security email.
4. **Document the incident** for post-mortem review.
5. If secrets were committed: use `git filter-repo` to scrub history, then coordinate a force push. Assume any secret pushed to a public repo is compromised — rotate it regardless.

*Source: [SECURITY.md](SECURITY.md) "Incident Response"*

### 1.9 PR Security Checklist

Every pull request must satisfy:

- [ ] No secrets in code or comments
- [ ] No hardcoded credentials
- [ ] Input validation for all external data
- [ ] Safe subprocess calls (no `shell=True` with user input)
- [ ] Dependencies updated and scanned
- [ ] Container runs as non-root user
- [ ] Sensitive data not logged
- [ ] `gitleaks` passes locally

*Source: [SECURITY.md](SECURITY.md) "Security Checklist for PRs"*

---

## 2. Development Workflow

APME follows **Spec-Driven Development (SDD)**: every feature flows through a formal lifecycle before code is written.

**Canonical sources:** [.sdlc/context/workflow.md](.sdlc/context/workflow.md), [.sdlc/context/getting-started.md](.sdlc/context/getting-started.md), [.sdlc/README.md](.sdlc/README.md)

### 2.1 The SDLC Lifecycle

```
1. ASSESS          2. UNBLOCK         3. SPECIFY         4. EXECUTE
──────────────     ──────────────     ──────────────     ──────────────
/sdlc-status  ───> /dr-review    ───> /req-new      ───> /task-new
(current state)    (blocking DRs)     (new feature)      (break down)
                                                              │
                        ^                                     v
                        │         architectural decision?  Implement
                        │                  yes                │
                   /adr-new  <────────────────────────────────┘
                        │
                        v
                   /dr-new (if question arises during work)
```

### 2.2 Step-by-Step

1. **Assess** (`/sdlc-status`). Always start here when resuming work. Check requirement status, open DRs, blockers, and recent activity.
2. **Unblock** (`/dr-review`). Resolve blocking Decision Requests before creating new work. Priority order: Blocking > High > Medium > Low.
3. **Specify** (`/req-new`). Define the feature with user stories, acceptance criteria, and dependencies before implementing. Requirements live in `.sdlc/specs/REQ-NNN-name/`.
4. **Execute** (`/task-new`). Break requirements into tasks sized at 1-2 hours of focused work. Each task has clear verification steps.
5. **During implementation**: use `/dr-new` for questions that arise, `/adr-new` for architectural decisions that affect multiple components.

### 2.3 Artifact Hierarchy

```
Phase (PHASE-NNN)
 └── Requirement (REQ-NNN)
      ├── requirement.md — user stories, acceptance criteria
      ├── design.md — technical approach
      ├── contract.md — API/interface definitions
      └── tasks/
           └── TASK-NNN.md — implementation steps, verification
```

**Status transitions:**
- REQ: Draft → In Review → Approved → In Progress → Implemented
- TASK: Pending → In Progress → Complete → Blocked
- Phase: Not Started → In Progress → Complete (derived from REQ statuses)

### 2.4 Decision Requests (DRs)

- Document blocking questions with `/dr-new` instead of making ad-hoc choices.
- Triage checklist: read context, verify completeness, identify stakeholders, set priority, schedule review.
- Resolution: discuss options → choose → record rationale → define action items → update status → move to `closed/` → update index.
- Review cadence: Blocking DRs immediately, High within a sprint, Medium/Low in regular cadence.

*Source: [.sdlc/decisions/README.md](.sdlc/decisions/README.md)*

### 2.5 Architecture Decision Records (ADRs)

- Create an ADR when a decision affects multiple components, introduces new patterns, or would be hard to reverse.
- Check existing ADRs and architectural invariants (AGENTS.md) before creating — no silent contradictions.
- If modifying an architectural invariant: requires explicit supersede/amend reference, AGENTS.md update, and human approval.
- ADRs require at least 2 options considered.

*Sources: [.sdlc/adrs/README.md](.sdlc/adrs/README.md), [.agents/skills/adr-new/SKILL.md](.agents/skills/adr-new/SKILL.md)*

### 2.6 Anti-Patterns

| Anti-Pattern | Consequence |
|--------------|-------------|
| Skip assessment (`/sdlc-status`) | Miss blocking DRs, duplicate work, miss recent decisions |
| Let DRs accumulate | Blocked work piles up, ad-hoc decisions made inconsistently |
| Skip specs | Scope creep, missing acceptance criteria, can't verify completion |
| Make silent decisions | Inconsistent patterns, lost context, repeated debates |
| Modify codebase to work around local environment | Breaks other contributors; the repo must work for the team, not one machine |

**Never change production code or project structure to work around a local sandbox, IDE limitation, or environment-specific issue.** This is a team repository — implementations must be straightforward and adhere to the structure defined in `.sdlc/` and the project's architectural conventions. If your local environment cannot run something, fix the environment or raise a DR; do not reshape the codebase to fit a single workstation.

*Source: [.sdlc/context/workflow.md](.sdlc/context/workflow.md) "Anti-Patterns to Avoid"*

---

## 3. Code Quality Standards

**Canonical source:** [.sdlc/context/conventions.md](.sdlc/context/conventions.md)

### 3.1 Python Style

| Rule | Standard |
|------|----------|
| Version | Python 3.11+ (use `match`, `X \| Y` type unions) |
| Formatter | Ruff (Black-compatible), 88-character line limit |
| Linter | Ruff (rules: E, F, W, I, UP, B, SIM, D) |
| Type checker | mypy strict + `disallow_any_explicit` (ADR-018) |
| Docstrings | Google style; enforced by Ruff D rules + pydoclint |

### 3.2 Imports

```python
# Order: stdlib → third-party → local (alphabetical within groups)
from pathlib import Path

import grpc
from ruamel.yaml import YAML

from apme_engine.engine.models import Task
```

### 3.3 Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Files | `snake_case.py` | `scan_state.py` |
| Documentation | `kebab-case.md` | `dependency-governance.md` |
| Root docs | `UPPER_CASE.md` | `CONTRIBUTING.md` |
| Classes | PascalCase | `PlaybookScanner` |
| Functions | `verb_noun` | `scan_playbook()` |
| Booleans | `is_` / `has_` prefix | `is_valid`, `has_issues` |
| Constants | UPPER_SNAKE | `MAX_BATCH_SIZE` |

### 3.4 Type Hints

Required on all function signatures. Do not put types in docstrings — types belong in signatures only. Include `Attributes` sections in dataclass docstrings.

### 3.5 Error Handling

Use the custom exception hierarchy (`APMEError` → `ScanError`, `TransformError`, etc.). Never catch bare `Exception` without re-raising or logging.

### 3.6 Logging

Use `structlog` for structured logging:
```python
logger = structlog.get_logger(__name__)
logger.info("scan_started", path=str(path), fix_mode=fix)
```

### 3.7 YAML Handling

- **Reads:** `ruamel.yaml` with `typ='safe'` when round-trip is not needed.
- **Writes:** `ruamel.yaml` round-trip mode to preserve comments, ordering, and formatting. Never use PyYAML for writes.

### 3.8 Testing

| Rule | Standard |
|------|----------|
| Framework | pytest |
| Location | `tests/` mirroring `src/` structure; rule tests colocated in `rules/` |
| Naming | `test_*.py` files, `test_*` functions |
| Assertions | Plain `assert` statements |
| Fixtures | `conftest.py`, shared helpers in `_test_helpers.py` |
| Slow tests | Mark with `@pytest.mark.integration` |
| Coverage | Floor: 36% (CI), target: 50% (`pyproject.toml`), ratchet up over time |

**Before running tests, always stop the apme daemon** (`apme daemon stop`). A running daemon may be serving a stale build that does not reflect recent code changes, causing tests to pass or fail for the wrong reasons. Stop it, then run tests against the current source.

**Never modify a test merely to make it pass.** When a test fails, the problem is in the recently written or changed production code, not in the test that caught it. Investigate the failure, discuss the root cause, and fix the implementation. Weakening assertions, loosening expected values, or deleting test cases to achieve a green run masks real defects and erodes test suite value.

**After testing, stop the apme daemon** (`apme daemon stop`). Do not leave a daemon running after a test session — it will go stale as development continues and silently interfere with the next round of work.

---

## 4. Pre-commit and CI Gates

**Canonical sources:** [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md), ADR-014, ADR-015, ADR-018

### 4.1 The Single Gate: `prek run --all-files`

All quality checks run through `prek` — both locally and in CI. This ensures the same checks pass everywhere.

| Hook | What it does |
|------|-------------|
| `ruff` | Lint (E, F, W, I, UP, B, SIM, D rules) with `--fix` |
| `ruff-format` | Code formatting (Black-compatible) |
| `mypy` | Strict type checking on `src/`, `tests/`, `scripts/` |
| `pydoclint` | Google-style docstring consistency |

### 4.2 Setup

```bash
# Install prek
uv tool install prek   # or: pip install prek

# Install git hooks
prek install

# Run manually
prek run --all-files
```

### 4.3 CI Enforcement

- CI runs `prek run --all-files` on every PR targeting `main` (`.github/workflows/prek.yml`).
- CI mirrors local hooks exactly (ADR-015) — no discrepancies between local and CI checks.
- PRs that fail ruff, mypy, or pydoclint checks cannot merge.

### 4.4 Proto Stub Regeneration

After modifying any `.proto` file, regenerate stubs:
```bash
./scripts/gen_grpc.sh
```
Generated `*_pb2.py` and `*_pb2_grpc.py` files in `src/apme/v1/` are committed to the repo. Never edit them by hand.

### 4.5 Container Rebuild Rules

Rebuild required after modifying: `src/**/*.py`, `validators/**/*.py`, `proto/**/*.proto`, `pyproject.toml`, `Containerfile*`.

**Workflow:** stop → build → start.

**No rebuild needed:** `docs/*.md`, `.sdlc/**/*.md`.

---

## 5. Git Workflow and PR Process

**Canonical sources:** [CONTRIBUTING.md](CONTRIBUTING.md), [.agents/skills/submit-pr/SKILL.md](.agents/skills/submit-pr/SKILL.md), ADR-016

### 5.1 Branch Strategy

- **`main`** is the only long-lived branch (ADR-016). **Never commit directly to `main`** — all changes must go through a feature branch and PR.
- Feature branches are short-lived and merge via PR.
- Always sync before branching to ensure you have the latest content:
  ```bash
  git fetch origin
  git pull origin main
  git switch --create feat/<slug> origin/main
  ```
- Branch naming: `feat/<slug>`, `fix/<slug>`, `docs/<slug>`, or `feature/REQ-NNN-description`.

### 5.2 Conventional Commits

All commits follow the [Conventional Commits](https://www.conventionalcommits.org/) format:

```
type(scope): description
```

| Type | When to use |
|------|-------------|
| `feat` | New feature (rule, validator, CLI subcommand, service) |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `style` | Code style / formatting (no logic change) |
| `refactor` | Code restructuring (no feature or fix) |
| `test` | Adding or updating tests |
| `build` | Build system, dependencies, containers |
| `ci` | CI/CD configuration |
| `chore` | Maintenance tasks |

Scopes: `engine`, `native`, `opa`, `ansible`, `gitleaks`, `daemon`, `cli`, `formatter`, `remediation`, `cache`, `proto`.

### 5.3 Branch/Artifact Alignment

Before pushing, verify the branch name matches any SDLC artifact IDs in the diff. A branch named `req-005` that contains `REQ-011` creates confusion. Use `/branch-align` to rename if mismatched.

### 5.4 PR Template

```markdown
## Summary
Brief description of changes.

## Related Specs
- REQ-NNN: [Requirement name]
- TASK-NNN: [Task name]

## Changes
- List of notable changes

## Security Checklist
- [ ] No secrets in code
- [ ] Input validation added
- [ ] Pre-commit hooks pass

## Test Plan
- [ ] prek run --all-files passes
- [ ] pytest passes
- [ ] Docs updated (if applicable)
```

### 5.5 Review Protocol

1. **Every review comment requires two actions**: a closing reply and explicit thread resolution. Unanswered comments block merge.
2. **Green CI is a prerequisite** for addressing review comments. Fix build failures first.
3. **PR body must stay current.** When pushing additional commits, update the Summary, Changes, and Test Plan sections to reflect all commits on the branch.
4. At least one maintainer review is required before merge.
5. All discussions must be resolved before merge.
6. Squash merge to `main`.

*Sources: [.agents/skills/pr-review/SKILL.md](.agents/skills/pr-review/SKILL.md), [.agents/skills/submit-pr/SKILL.md](.agents/skills/submit-pr/SKILL.md)*

### 5.6 Documentation Updates

Check whether changes affect existing docs before submitting:

| Doc | When to update |
|-----|---------------|
| `docs/DEVELOPMENT.md` | New dev workflows, setup changes, new rule patterns |
| `docs/ARCHITECTURE.md` | Container topology, gRPC contract changes, new services |
| `docs/DATA_FLOW.md` | Request lifecycle, serialization, payload changes |
| `docs/DEPLOYMENT.md` | Podman pod spec, container config, env vars |
| `docs/LINT_RULE_MAPPING.md` | New or renamed rule IDs |

If a new rule was added, regenerate the catalog:
```bash
python scripts/generate_rule_catalog.py
```

---

## 6. Architectural Invariants

These are non-negotiable. Violating any of them breaks the system or creates compounding debt. If you think one needs to change, write an ADR first.

**Canonical source:** [AGENTS.md](AGENTS.md) "Architectural Invariants"

1. **Validators are read-only** (ADR-009). Validators detect; they never modify files.
2. **gRPC everywhere between backend services** (ADR-001). No REST, no message queues, no direct function calls between services.
3. **Async servers with executor discipline** (ADR-007). All gRPC servers use `grpc.aio`. Blocking work goes through `run_in_executor()`.
4. **Unified Validator contract** (`validate.proto`). Every validator implements `Validator.Validate` + `Validator.Health`.
5. **Stateless engine, persistence at the edge** (ADR-020, ADR-029). Zero database code in the engine pod. Persistence lives in the Gateway.
6. **Scale pods, not individual services** (ADR-012). The engine runtime is a unit.
7. **Session venvs are Primary-owned** (ADR-022). Primary is the single writer to `/sessions`.
8. **Rule IDs follow ADR-008.** L = Lint, M = Modernize, R = Risk, P = Policy, SEC = Secrets. Plugins use `EXT-` prefix.
9. **OPA uses subprocess, not REST.** No HTTP client for OPA.
10. **`FixSession` is the unified client path** (ADR-039). Both `check` and `remediate` use the bidirectional `FixSession` RPC.
11. **The engine never queries out; it only emits** (ADR-020, ADR-029). Context enrichment is the Gateway's responsibility.
12. **Engine-core services are required, not optional.** Primary, Native, OPA, Ansible, Galaxy Proxy are all required. Only Gitleaks is optional.
13. **Transforms are semantically trusted; the engine owns state and syntax** (ADR-044). Transforms operate on ephemeral copies with transaction safety.
14. **Built-in validator bundles are closed** (ADR-042). No volume-mounted rules. Custom rules go through the Plugin service as a separate container.

### Design Thinking Rules

- **Two workarounds for the same interface = redesign the interface.** Do not defend existing code simply because effort was invested.
- **Design LLM contracts around LLM strengths.** LLMs return content; we handle positioning.
- **Two failed attempts = wrong abstraction.** Escalate to a design review.
- **Dependency direction is sacred.** Engine → Gateway → UI. Never invert.
- **When in doubt, read the ADR.** If no ADR covers it, write one before implementing.

---

## 7. Rule Development

**Canonical sources:** [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md), [docs/LINT_RULE_MAPPING.md](docs/LINT_RULE_MAPPING.md), [docs/RULE_DOC_FORMAT.md](docs/RULE_DOC_FORMAT.md), ADR-008

### 7.1 Rule ID Conventions

| Prefix | Category | Validators |
|--------|----------|-----------|
| **L** | Lint (style, correctness, best practice) | Native, OPA, Ansible |
| **M** | Modernize (ansible-core metadata) | Ansible, Native, OPA |
| **R** | Risk/security (annotation-based) | Native, OPA |
| **P** | Policy (legacy, superseded by L058/L059) | Native |
| **SEC** | Secrets (via Gitleaks) | Gitleaks |
| **EXT-** | Plugin/third-party rules (ADR-042) | Plugin service |

Rule IDs are independent of the validator that implements them.

### 7.2 Choosing a Validator

| Criteria | Native (Python) | OPA (Rego) | Ansible |
|----------|-----------------|------------|---------|
| Access to full task model (`Task.loop`, `Task.options`) | Yes | Limited (via `input.hierarchy`) | No |
| Declarative policy logic | Possible but verbose | Natural fit | No |
| Requires ansible-core runtime | No | No | Yes |
| Best for | Complex Python logic, annotations | Simple structural checks | Module argspec, FQCN resolution |

### 7.3 File Checklist for a New Rule

1. **Rule implementation:** `src/apme_engine/validators/<validator>/rules/<ID>_<name>.py` (or `.rego`)
2. **Rule documentation:** `<ID>_<name>.md` alongside the implementation, with YAML frontmatter and `### Example: violation` / `### Example: pass` sections
3. **Colocated tests:** `<ID>_<name>_test.py` (or `_test.rego`) with violation and pass cases
4. **Update `rule_versions.json`** for native rules
5. **Update `docs/LINT_RULE_MAPPING.md`** with the new entry
6. **Regenerate rule catalog:** `python scripts/generate_rule_catalog.py`

### 7.4 Rule Documentation Format

```markdown
---
rule_id: L0XX
validator: native
description: Short description.
---

## Rule title (L0XX)

Explanation of what the rule checks and why.

### Example: violation

```yaml
- name: Bad task
  some_module:
    bad_option: value
```

### Example: pass

```yaml
- name: Good task
  some_module:
    good_option: value
```
```

Examples must be valid Ansible YAML — the integration test runner parses them.

---

## 8. Release Process

**Canonical source:** [CLAUDE.md](CLAUDE.md) "Release Process"

### 8.1 Version Updates

1. Bump version in `pyproject.toml`
2. Update `CHANGELOG.md` with user-facing changes
3. Update container image tags

### 8.2 Release Checklist

- [ ] All unit tests pass (`pytest`)
- [ ] All pre-commit checks pass (`prek run --all-files`)
- [ ] Security audit green (`gitleaks`, `bandit`, `pip-audit`)
- [ ] `CHANGELOG.md` updated
- [ ] Version bumped in `pyproject.toml`
- [ ] Tag created: `vX.Y.Z`
- [ ] Container images built and pushed

---

## 9. Industry Alignment and Gap Analysis

This section compares APME's current practices against four industry frameworks:
- **NIST SSDF v1.2** (SP 800-218) — Secure Software Development Framework
- **OpenSSF OSPS Baseline** (2026-02-19) — Open Source Project Security controls
- **SLSA** — Supply Chain Levels for Software Artifacts
- **GitHub Hardening Guides** — Platform-specific security configuration

### 9.1 Current Alignment (what APME already does well)

| Practice | APME Implementation | Framework |
|----------|-------------------|-----------|
| Secret scanning pre-commit | gitleaks, detect-secrets, bandit, detect-private-key | NIST SSDF PW, OpenSSF L1 |
| Static analysis in CI | Ruff (lint + format), mypy strict, pydoclint via prek | NIST SSDF PW |
| Vulnerability reporting process | SECURITY.md with private disclosure, response SLAs | OpenSSF L1 |
| Dependency governance | ADR-019 two-tier model with 7-question checklist | NIST SSDF PS |
| Container hardening | Non-root, pinned tags, no secrets in ENV, image scanning | OpenSSF L2 |
| CI as thin wrapper | Actions pin to SHAs, local-reproducible steps (ADR-015) | SLSA Build L1, OpenSSF SCM |
| Spec-driven development | REQ → TASK → code with traceability | NIST SSDF PO |
| Incident response documented | SECURITY.md "Incident Response" section | NIST SSDF RV |
| License declared | Apache 2.0, documented in CONTRIBUTING.md | OpenSSF L1 |
| Structured logging with redaction | structlog, `[REDACTED]` for secrets | NIST SSDF PW |

### 9.2 High-Priority Gaps (Security)

These gaps are present in industry standards and are especially important for a public repository.

#### 9.2.1 CODEOWNERS File

**Gap:** No `CODEOWNERS` file to enforce review by domain experts on critical paths.

**Industry reference:** OpenSSF Baseline L2, GitHub Hardening Guide.

**Recommendation:** Create `.github/CODEOWNERS` mapping critical paths to required reviewers:
```
# Security-sensitive paths
/SECURITY.md                    @security-team
/.github/                       @maintainers
/containers/                    @maintainers
/proto/                         @maintainers

# Core engine
/src/apme_engine/engine/        @engine-team
/src/apme_engine/daemon/        @engine-team

# Validators
/src/apme_engine/validators/    @validator-team
```

#### 9.2.2 Signed Commits

**Gap:** No requirement or documentation for GPG/SSH commit signing.

**Industry reference:** OpenSSF Baseline L2, SLSA Source L2.

**Recommendation:** Document commit signing setup in `CONTRIBUTING.md`. Consider requiring verified signatures via branch protection rules. At minimum, maintainer commits should be signed.

#### 9.2.3 Automated Dependency Updates

**Gap:** No Dependabot or Renovate configuration for automated dependency update PRs.

**Industry reference:** OpenSSF Baseline L2, NIST SSDF RV.

**Recommendation:** Add `.github/dependabot.yml`:
```yaml
version: 2
updates:
  - package-ecosystem: pip
    directory: "/"
    schedule:
      interval: weekly
    reviewers:
      - maintainers
  - package-ecosystem: github-actions
    directory: "/"
    schedule:
      interval: weekly
```

#### 9.2.4 SBOM Generation

**Gap:** No Software Bill of Materials generated for releases. DR-002 (SBOM format) is deferred.

**Industry reference:** NIST SSDF PS, OpenSSF Baseline L3, Executive Order 14028.

**Recommendation:** Unblock DR-002 and add `syft` or `cyclonedx-bom` to the release pipeline. Generate SBOMs for both the Python package and container images.

#### 9.2.5 Artifact Signing

**Gap:** No container image or release artifact signing.

**Industry reference:** SLSA Build L2, Sigstore ecosystem.

**Recommendation:** Sign published container images with `cosign` (Sigstore). Include provenance attestations for builds produced in CI.

#### 9.2.6 CodeQL / SAST in CI

**Gap:** No CodeQL or equivalent deep static analysis beyond ruff and bandit pre-commit.

**Industry reference:** NIST SSDF PW, OpenSSF Scorecard.

**Recommendation:** Add `.github/workflows/codeql-analysis.yml` with Python language support. CodeQL catches vulnerability patterns (injection, path traversal, deserialization) that ruff and bandit may miss.

#### 9.2.7 Branch Protection Documentation

**Gap:** Branch protection rules are not documented as project policy.

**Industry reference:** GitHub Hardening Guide, OpenSSF SCM Best Practices.

**Recommendation:** Document the following as required branch protection settings for `main`:
- Require pull request reviews (at least 1 approver)
- Require status checks to pass (prek, tests)
- Require conversation resolution before merge
- Prevent force pushes and deletions
- Require linear commit history

#### 9.2.8 GitHub Security Tab Configuration

**Gap:** It is unclear whether `SECURITY.md` is linked via GitHub's Security tab.

**Industry reference:** OpenSSF Baseline L1.

**Recommendation:** Verify via Settings → Code security and analysis → Security policy that `SECURITY.md` is detected and shown in the Security tab.

### 9.3 Medium-Priority Gaps (Process)

#### 9.3.1 Threat Modeling in Requirements

**Gap:** No explicit threat modeling step for security-sensitive features.

**Industry reference:** NIST SSDF PW.1 ("Design software to meet security requirements and mitigate security risks").

**Recommendation:** Add a lightweight "Security Considerations" section to the REQ template (`.sdlc/templates/requirement.md`):
```markdown
## Security Considerations
- [ ] Threat model: what can go wrong?
- [ ] Trust boundaries: what input is untrusted?
- [ ] Data sensitivity: what data is handled?
- [ ] Attack surface: what new endpoints/interfaces are exposed?
```

#### 9.3.2 Post-Incident Review Template

**Gap:** No post-mortem / retrospective template.

**Industry reference:** NIST SSDF RV.3 ("Analyze vulnerabilities to identify their root causes").

**Recommendation:** Add `.sdlc/templates/postmortem.md` covering: timeline, root cause, impact, remediation, prevention measures, and action items.

#### 9.3.3 Developer Certificate of Origin

**Gap:** No explicit DCO or CLA requirement beyond the license statement.

**Industry reference:** OpenSSF Baseline L2.

**Recommendation:** The Apache 2.0 license is already chosen (DR-009) and `CONTRIBUTING.md` states contributions are licensed under it. Consider adding a DCO sign-off requirement (`Signed-off-by:` trailer) for stronger contributor attribution.

#### 9.3.4 Inconsistent Tooling Documentation

**Gap:** `CONTRIBUTING.md` references `pre-commit install` while `docs/DEVELOPMENT.md` and `AGENTS.md` reference `prek install`. Both exist but the canonical tool is `prek`.

**Recommendation:** Align `CONTRIBUTING.md` to reference `prek` as the canonical pre-commit tool, with `pre-commit` mentioned only as the underlying mechanism. A single answer avoids confusion for new contributors.

#### 9.3.5 Incomplete Skills Table in AGENTS.md

**Gap:** Three skills (`branch-align`, `rfe-capture`, `security-scan`) exist under `.agents/skills/` but are not listed in the AGENTS.md Project Skills table.

**Recommendation:** Add the missing entries to the table in `AGENTS.md`.

### 9.4 Summary Matrix

| Gap | Priority | Effort | Framework |
|-----|----------|--------|-----------|
| CODEOWNERS | High | Low | OpenSSF L2 |
| Signed commits | High | Low | OpenSSF L2, SLSA |
| Dependabot config | High | Low | OpenSSF L2, NIST |
| SBOM generation | High | Medium | NIST, OpenSSF L3 |
| Artifact signing | High | Medium | SLSA L2 |
| CodeQL in CI | High | Low | NIST, OpenSSF |
| Branch protection docs | High | Low | GitHub Hardening |
| Security tab config | High | Low | OpenSSF L1 |
| Threat modeling in REQ | Medium | Low | NIST PW.1 |
| Post-incident template | Medium | Low | NIST RV.3 |
| DCO sign-off | Medium | Low | OpenSSF L2 |
| Tooling docs alignment | Medium | Low | Internal |
| Skills table update | Medium | Low | Internal |

---

## Quick Reference: Daily Workflow

```
Start of session:
  1. git fetch origin            — sync with upstream
  2. git pull origin main        — ensure local main is current
  3. /sdlc-status                — check state and blockers
  4. /dr-review                  — resolve any blocking DRs
  5. Create a feature branch     — git switch --create feat/<slug> origin/main
  6. Pick a task or /req-new     — specify and execute

Before every commit:
  1. Verify you are on a feature branch, NOT main
  2. prek run --all-files      — lint, format, type check, docstrings
  3. pytest                    — run tests
  4. Review security checklist — no secrets, safe patterns

Before every PR:
  1. Branch name matches artifacts
  2. PR body has Summary, Changes, Security Checklist, Test Plan
  3. Docs updated if applicable
  4. CI green
```

---

*Last updated: 2026-03-23*
