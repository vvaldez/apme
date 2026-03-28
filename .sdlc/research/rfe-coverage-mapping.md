# RFE Coverage Mapping

**Created:** 2026-03-25
**Updated:** 2026-03-26
**Purpose:** Track external RFEs and their coverage by APME capabilities

---

## Integration Architecture

**ADR-038 (Public Data API)** defines how platform consumers (Controller, EDA, Automation Analytics, CI/CD) access APME's scan data:

- **Pull model**: Consumers query the Gateway REST API by project URL
- **Webhook notifications**: Consumers subscribe to scan-complete events
- **Controller as bridge**: Controller queries APME; AA gets data via Controller telemetry

Many RFEs in this document note "integration gaps" — the gap between APME's detection capability and surfacing results in platform UIs. **ADR-038 is the architectural answer** to these integration concerns.

---

## Coverage Status Legend

| Status | Meaning |
|--------|---------|
| **Covered** | APME already provides this capability |
| **Partial** | APME detects, but integration/UI surfacing is separate |
| **Roadmap** | Planned APME feature will address |
| **Tracked Upstream** | Depends on upstream project fix |
| **Candidate** | Could be an APME feature (needs REQ) |
| **Out of Scope** | Not appropriate for APME |

---

## Covered by APME (2 RFEs)

These RFEs are fully addressed by existing APME capabilities.

### AAPRFE-2472: Native Playbook Sanity Command

| Field | Value |
|-------|-------|
| **Summary** | Add native ansible sanity command for playbook validation |
| **Status** | Closed |
| **Classification** | **Covered** |
| **APME Rules** | **L057** (syntax validation), **L058-L059** (argspec validation), **M001/L026** (FQCN), plus 100+ lint rules |
| **How APME Addresses** | `apme-scan check` provides comprehensive playbook validation: YAML syntax, deprecated modules, undefined variables, module argument validation, best practices. This is exactly what the RFE requests. |
| **Gap** | None — APME is the implementation of this request |
| **Action** | Close with reference to APME |

---

### AAPRFE-2376: ansible-policy Rego Documentation

| Field | Value |
|-------|-------|
| **Summary** | Enhance ansible-policy docs with clearer Rego syntax mapping |
| **Status** | Closed |
| **Classification** | **Covered** |
| **APME Rules** | OPA/Rego validator with inline documentation |
| **How APME Addresses** | APME includes a full OPA validator with Rego policy support. Each `.rego` rule has colocated `.md` documentation. `DESIGN_VALIDATORS.md` and `DEVELOPMENT.md` provide authoring guides. |
| **Gap** | Documentation is for APME's OPA validator, not ansible-policy (different tool) |
| **Action** | Close; APME provides good Rego docs |

---

## Partial Coverage (3 RFEs)

These RFEs involve capabilities where APME provides detection, but platform integration is needed to fully address the request. ADR-038 defines the integration mechanism.

### AAPRFE-2515: Deprecation Warning Search

| Field | Value |
|-------|-------|
| **Summary** | Enable Searching for jobs that include deprecation warnings |
| **Status** | Backlog |
| **Classification** | **Partial** |
| **APME Rules** | **M002** (deprecated modules), **M004** (tombstoned modules), **L004** (OPA deprecated check) |
| **Detection** | ✅ APME detects deprecated modules at scan time via L004 (OPA static list), M002/M004 (ansible-core runtime introspection) |
| **Gap** | RFE asks for runtime job search in Controller UI. APME provides detection; surfacing in Controller requires ADR-038 integration. |
| **Action** | Link to APME for detection; note ADR-038 for integration |

---

### AAPRFE-2313: Linting Problems Noted in UI

| Field | Value |
|-------|-------|
| **Summary** | Rulebooks/playbooks with linting problems should be noted |
| **Status** | Closed |
| **Classification** | **Partial** |
| **APME Rules** | L-series rules (38 covered, 4 partial per ANSIBLELINT_COVERAGE.md) |
| **Detection** | ✅ APME detects linting issues with structured output. Note: APME implements its own rules, not ansible-lint directly. |
| **Gap** | RFE asks for problems "noted in UI" (EDA/Controller). APME provides detection; UI integration requires ADR-038. |
| **Action** | Link to APME for detection; note ADR-038 for UI surfacing |

---

### AAPRFE-1607: Deprecated Module Reports in Analytics

| Field | Value |
|-------|-------|
| **Summary** | Report in Automation Analytics showing deprecated module usage |
| **Status** | Closed |
| **Classification** | **Partial** |
| **APME Rules** | **M002** (deprecated), **M004** (tombstoned), **L004** (OPA deprecated check) |
| **Detection** | ✅ APME detects deprecated modules with full metadata (module name, replacement, deprecation version) |
| **Gap** | RFE asks for reports **in Automation Analytics**. APME detects; ADR-038 defines how AA gets data via Controller telemetry. |
| **SDLC Artifacts** | REQ-011, DR-013 (reframing based on ADR-038) |
| **Action** | Link to APME detection; reframe REQ-011/DR-013 per ADR-038 |

---

## Tracked Upstream (1 RFE)

### AAPRFE-2374: var-naming Rule Collision

| Field | Value |
|-------|-------|
| **Summary** | ansible-lint collision between var-naming[no-role-prefix] and var-naming[pattern] |
| **Status** | Backlog |
| **Classification** | **Tracked Upstream** |
| **Clarification** | APME does **not** inherit ansible-lint rules. APME has its own independent implementations: L050 (var_naming.py), L100-L102 (keyword, invalid chars, reserved names). These are APME's own code, not inherited from ansible-lint. |
| **Gap** | The RFE is about an upstream ansible-lint bug ([#4142](https://github.com/ansible/ansible-lint/issues/4142)). APME didn't fix it and doesn't inherit any fix. |
| **Action** | Track upstream; not an APME concern |

---

## Not Covered (1 RFE)

### AAPRFE-2059: Skip YAML Rules in ansible-lint

| Field | Value |
|-------|-------|
| **Summary** | Allow ansible-lint to skip `yaml` rules while still fixing other rules |
| **Status** | Closed |
| **Classification** | **Not Covered** |
| **Current State** | No end-user mechanism to exclude specific rule IDs exists today. CLI `scan` has no `--skip` or `--exclude-rules` flag. No `[tool.apme]` section in `pyproject.toml` for rule exclusion. Only file/path-based exclusion via `.apmeignore`. |
| **Gap** | Rule exclusion configuration needs to be implemented |
| **Action** | Track as roadmap item; consider adding to REQ-001 or new REQ |

---

## Roadmap (7 RFEs)

These RFEs will be addressed by planned APME features.

### AAPRFE-1628: Smart ansible-galaxy Version Decisions

| Field | Value |
|-------|-------|
| **Summary** | ansible-galaxy should make smart decisions regarding ansible-core and collection versions |
| **Status** | Release Pending |
| **Classification** | **Roadmap** |
| **APME Rules** | **M005-M013** (migration rules) — partially implemented |
| **Implementation Status** | M005 ✅, M006 ✅, M007 ❌, M008 ✅, M009 ✅, M010 ✅, M011 ✅, M012 ❌, M013 ❌ (6 of 9 implemented) |
| **How APME Will Address** | APME's migration rules analyze `requires_ansible` constraints and detect version incompatibilities. |
| **Gap** | RFE is about ansible-galaxy making smart decisions during **installation**. APME provides static analysis of content compatibility, not installation decisions. |
| **Action** | Track as roadmap; complete M007/M012/M013 implementation |

### AAPRFE-2552: Collection Version Range for Cisco Gear

| Field | Value |
|-------|-------|
| **Summary** | Add version range to collections for cisco gear |
| **Status** | Backlog |
| **APME Roadmap** | **R505-R507** (EE compatibility checks), collection dependency analysis |
| **How APME Will Address** | APME's planned EE compatibility rules will analyze collection metadata including tested versions, `requires_ansible`, and platform compatibility. This enables validation of collection compatibility with specific network OS versions. |
| **Timeline** | Planned for Phase 3 (Enterprise Dashboard) |
| **Action** | Track; will be addressed by R505-R507 |

---

### AAPRFE-2551: Compatible OS Version Range

| Field | Value |
|-------|-------|
| **Summary** | Looking for a range of compatible OS versions |
| **Status** | Backlog |
| **APME Roadmap** | **R505** (EE base image compatibility) |
| **How APME Will Address** | Related to AAPRFE-2552. APME's EE compatibility analysis will include platform/OS version compatibility checking based on collection metadata and runtime requirements. |
| **Timeline** | Planned for Phase 3 (Enterprise Dashboard) |
| **Action** | Track; will be addressed by R505 |

---

### AAPRFE-2664: AAP 2.6 EEs on RHEL 10

| Field | Value |
|-------|-------|
| **Summary** | Provide AAP2.6 EEs (Supported and Minimal) based on RHEL 10 image |
| **Status** | Backlog |
| **APME Roadmap** | **R505** (EE base image compatibility), **R507** (Python version compatibility) |
| **How APME Will Address** | APME's EE validation rules will check base image compatibility, Python version requirements (3.12+), and collection compatibility with RHEL 10 ecosystem. This helps customers validate their content works with new EE images. |
| **Timeline** | Planned for Phase 3; depends on RHEL 10 EE availability |
| **Action** | Track; APME validates content compatibility with new EEs |

---

### AAPRFE-2580: Zero-CVE EE Base Images

| Field | Value |
|-------|-------|
| **Summary** | Base ee-supported-* images on zero-CVE images (Project Hummingbird) |
| **Status** | Backlog |
| **APME Roadmap** | **R506** (EE system package compatibility), security scanning integration |
| **How APME Will Address** | APME's EE analysis can validate that EE images meet security requirements. While APME doesn't build images, it can flag EE configurations that may introduce CVE risks (e.g., pinned vulnerable package versions). |
| **Timeline** | Planned for Phase 3 |
| **Action** | Track; APME provides content-level security analysis |

---

### AAPRFE-2739: Python 3.11 to 3.12 for EE

| Field | Value |
|-------|-------|
| **Summary** | Update python3.11 to python3.12 for execution environment in AAP 2.5/2.6 |
| **Status** | Closed |
| **APME Roadmap** | **R507** (EE Python package compatibility), Python version rules |
| **How APME Will Address** | APME's planned Python version compatibility rules will detect content that requires specific Python versions or uses syntax/libraries incompatible with Python 3.12. This helps validate playbooks work with upgraded EEs. |
| **Timeline** | In progress (M005-M013 partially cover this) |
| **Action** | Closed in Jira; APME validates content compatibility |

---

### AAPRFE-2070: DNF Module with Newer Python

| Field | Value |
|-------|-------|
| **Summary** | DNF module broken with newer python versions |
| **Status** | Release Pending |
| **APME Roadmap** | **M005-M013** (migration rules), Python/module compatibility |
| **How APME Will Address** | APME's migration rules detect module compatibility issues across ansible-core versions. The DNF module's Python version requirements are part of this analysis. APME can flag playbooks using `ansible.builtin.dnf` with incompatible Python configurations. |
| **Timeline** | In progress |
| **Action** | Release Pending in Jira; APME detects compatibility issues |

---

## Summary: RFE Coverage by Status

This section consolidates all RFEs by their actual classification status.

### Fully Covered (Detection Implemented)

| RFE | APME Rules | Action |
|-----|-----------|--------|
| AAPRFE-2472 | L057, L058-L059, M001/L026 | Close with APME reference |
| AAPRFE-2376 | OPA validator docs | Close |

### Partial (Detection Yes, Integration via ADR-038)

| RFE | APME Rules | Gap | Action |
|-----|-----------|-----|--------|
| AAPRFE-2515 | M002, M004, L004 | UI surfacing | ADR-038 integration |
| AAPRFE-2313 | L-series | UI surfacing | ADR-038 integration |
| AAPRFE-1607 | M002, M004, L004 | AA integration | REQ-011/DR-013 + ADR-038 |

### Tracked Upstream

| RFE | Issue | Action |
|-----|-------|--------|
| AAPRFE-2374 | ansible-lint #4142 | Track upstream; not APME concern |

### Not Covered (Feature Gap)

| RFE | Gap | Action |
|-----|-----|--------|
| AAPRFE-2059 | No rule exclusion config | Add to roadmap |

### Roadmap (Planned)

| RFE | APME Feature | Timeline |
|-----|-------------|----------|
| AAPRFE-1628 | M005-M013 (6/9 done) | In progress |

## Summary: Roadmap RFEs

| RFE | APME Roadmap | Status | Timeline |
|-----|-------------|--------|----------|
| AAPRFE-2552 | R505-R507 | Roadmap | Phase 3 |
| AAPRFE-2551 | R505 | Roadmap | Phase 3 |
| AAPRFE-2664 | R505, R507 | Roadmap | Phase 3 |
| AAPRFE-2580 | R506 | Roadmap | Phase 3 |
| AAPRFE-2739 | R507 | Roadmap | In progress |
| AAPRFE-2070 | M005-M013 | Roadmap | In progress |

---

## APME Candidates (12 RFEs)

These RFEs were labeled as candidates but require research to determine if they fit APME's scope (static code analysis).

### Analysis Summary

| RFE | Summary | APME Fit | Recommendation |
|-----|---------|----------|----------------|
| AAPRFE-2642 | EDA rulebook validation | **Yes** | Create REQ (E-series rules) |
| AAPRFE-2545 | Expand OPA inputs | **Yes** | Create REQ (policy input schema) |
| AAPRFE-2258 | Policy permissive mode | **Yes** | Create REQ (warn-only mode) |
| AAPRFE-2218 | EE signing status | **Partial** | Track (R509 validation rule) |
| AAPRFE-1689 | EE image field validation | **Partial** | Track (R510, already Closed) |
| AAPRFE-2791 | Collection migration playbook | No | Content request, not analysis |
| AAPRFE-2627 | Monitor parsing tasks | No | Platform feature |
| AAPRFE-2432 | Front-end input validation | No | Platform UI feature |
| AAPRFE-2310 | Input sanitization in AAP | No | Platform security feature |
| AAPRFE-2233 | Strong password policy | No | Platform security feature |
| AAPRFE-2205 | Rulebook job_args by name | No | EDA/Controller API feature |
| AAPRFE-2175 | Versionless EE image | No | Container registry issue |

---

### Genuine APME Candidates (3 RFEs → New REQs)

#### AAPRFE-2642: EDA Rulebook Validation (HIGH PRIORITY)

| Field | Value |
|-------|-------|
| **Summary** | Improve visibility for rulebook validation failures in EDA |
| **Status** | Backlog |
| **APME Fit** | **Yes** — Static validation of rulebook content |
| **Proposed Feature** | New rule category: **E-series** (EDA rules) |
| **Proposed Rules** | E001: Rulebook YAML syntax, E002: Action reference validation, E003: Source plugin validation |
| **Why APME** | APME already validates playbooks; extending to rulebooks is natural. Structured output enables UI integration. |
| **Action** | **Create REQ-012: EDA Rulebook Validation** |

---

#### AAPRFE-2545: Expand OPA Policy Inputs (HIGH PRIORITY)

| Field | Value |
|-------|-------|
| **Summary** | Expand OPA inputs to include playbook content |
| **Status** | Backlog |
| **APME Fit** | **Yes** — APME already parses playbooks for OPA |
| **Proposed Feature** | Extended policy input schema with parsed playbook content |
| **Current State** | APME's OPA validator receives parsed AST. RFE asks for richer input (task list, module calls, variable refs). |
| **Why APME** | APME's tree parser already extracts this data; exposing it to OPA policies is straightforward. |
| **Action** | **Create REQ-013: Extended OPA Policy Input Schema** |

---

#### AAPRFE-2258: Policy Permissive Mode

| Field | Value |
|-------|-------|
| **Summary** | Add permissive/warn-only mode for policy enforcement |
| **Status** | Backlog |
| **APME Fit** | **Yes** — Policy execution mode is APME configuration |
| **Proposed Feature** | Warn-only mode that logs violations without blocking |
| **Use Case** | Gradual policy rollout (like SELinux permissive mode) |
| **Why APME** | APME already has severity levels; adding enforcement modes extends this naturally. |
| **Action** | **Create REQ-014: Policy Permissive Mode** |

---

### Borderline Candidates (2 RFEs → Track on Roadmap)

#### AAPRFE-2218: EE Image Signing Status

| Field | Value |
|-------|-------|
| **Summary** | Indicate signing status per EE image tag in Hub |
| **Status** | Backlog |
| **APME Fit** | **Partial** — Validation rule possible, UI is Hub concern |
| **Proposed Rule** | **R509**: EE signing verification (check if image ref is signed) |
| **Gap** | APME can validate EE references in playbooks; signing status requires registry API. |
| **Action** | Track as roadmap item (R509) |

---

#### AAPRFE-1689: EE Image Field Validation

| Field | Value |
|-------|-------|
| **Summary** | Validate EE image field on creation |
| **Status** | Closed |
| **APME Fit** | **Partial** — APME can validate EE references in content |
| **Proposed Rule** | **R510**: EE image reference validation |
| **Gap** | RFE is about Controller UI; APME validates content, not UI forms. |
| **Action** | Track as roadmap item (R510); already Closed |

---

### Out of Scope (7 RFEs)

These RFEs don't fit APME's mission (static code analysis). Keep in AAP backlog.

| RFE | Summary | Reason Out of Scope |
|-----|---------|---------------------|
| AAPRFE-2791 | Collection migration playbook for rhel_idm | Content request, not analysis tool |
| AAPRFE-2627 | Monitor parsing tasks from Dashboard | Platform operations feature |
| AAPRFE-2432 | Front-end input validation | Platform UI feature (OWASP compliance) |
| AAPRFE-2310 | Input sanitization in AAP | Platform security feature |
| AAPRFE-2233 | Strong password policy | Platform authentication feature |
| AAPRFE-2205 | Rulebook job_args by name | EDA/Controller API feature |
| AAPRFE-2175 | Versionless EE image missing | Container registry/catalog issue |

---

## Summary Tables

### Covered (2 RFEs)

| RFE | APME Rules | Action |
|-----|-----------|--------|
| AAPRFE-2472 | L057, L058-L059, M001/L026 | Close with APME reference |
| AAPRFE-2376 | OPA validator docs | Close |

### Partial (3 RFEs)

| RFE | APME Rules | Gap | Action |
|-----|-----------|-----|--------|
| AAPRFE-2515 | M002, M004, L004 | UI surfacing | ADR-038 integration |
| AAPRFE-2313 | L-series | UI surfacing | ADR-038 integration |
| AAPRFE-1607 | M002, M004, L004 | AA integration | REQ-011/DR-013 + ADR-038 |

### Tracked Upstream (1 RFE)

| RFE | Issue | Action |
|-----|-------|--------|
| AAPRFE-2374 | ansible-lint #4142 | Track upstream; not APME concern |

### Not Covered (1 RFE)

| RFE | Gap | Action |
|-----|-----|--------|
| AAPRFE-2059 | No rule exclusion config | Add to roadmap |

### Roadmap (7 RFEs)

| RFE | APME Feature | Timeline |
|-----|-------------|----------|
| AAPRFE-1628 | M005-M013 (6/9 done) | In progress |
| AAPRFE-2552 | R505-R507 | Phase 3 |
| AAPRFE-2551 | R505 | Phase 3 |
| AAPRFE-2664 | R505, R507 | Phase 3 |
| AAPRFE-2580 | R506 | Phase 3 |
| AAPRFE-2739 | R507 | In progress |
| AAPRFE-2070 | M005-M013 | In progress |

### Candidate RFEs (12)

| RFE | APME Fit | Action |
|-----|----------|--------|
| AAPRFE-2642 | Yes | **REQ-012** (EDA validation) ✅ Created |
| AAPRFE-2545 | Yes | **REQ-013** (OPA inputs) ✅ Created |
| AAPRFE-2258 | Yes | **REQ-014** (permissive mode) ✅ Created |
| AAPRFE-2218 | Partial | Track (R509) |
| AAPRFE-1689 | Partial | Track (R510, Closed) |
| AAPRFE-2791 | No | Out of scope |
| AAPRFE-2627 | No | Out of scope |
| AAPRFE-2432 | No | Out of scope |
| AAPRFE-2310 | No | Out of scope |
| AAPRFE-2233 | No | Out of scope |
| AAPRFE-2205 | No | Out of scope |
| AAPRFE-2175 | No | Out of scope |

---

## Change History

| Date | Author | Change |
|------|--------|--------|
| 2026-03-25 | Phil (AI-assisted) | Initial mapping of 8 covered RFEs |
| 2026-03-25 | Phil (AI-assisted) | Added 6 roadmap RFEs (R505-R507, M005-M013) |
| 2026-03-25 | Phil (AI-assisted) | Analyzed 12 candidate RFEs; identified 3 for new REQs |
| 2026-03-26 | Phil (AI-assisted) | Reclassified based on code verification (PR #108 review) |
| 2026-03-26 | Phil (AI-assisted) | Added ADR-038 integration architecture note |
| 2026-03-26 | Phil (AI-assisted) | Corrected rule references (L002→M001/L026, clarified ansible-lint independence) |
