# REQ-012: EDA Rulebook Validation

## Metadata

- **Phase**: PHASE-003 - Enterprise Dashboard
- **Status**: Draft
- **Created**: 2026-03-25
- **External Reference**: [AAPRFE-2642](https://redhat.atlassian.net/browse/AAPRFE-2642)
- **Priority**: High

## Overview

Add static validation rules for Event-Driven Ansible (EDA) rulebooks. Currently, EDA silently ignores rulebooks with validation errors during project import, leaving users confused when rulebooks don't appear in the activation list. APME should provide comprehensive rulebook validation with structured output that EDA can surface in its UI.

## User Stories

**As an EDA Content Developer**, I want my rulebooks validated before activation so that I can fix errors during development rather than at runtime.

**As an EDA Administrator**, I want to see which rulebooks have validation errors so that I can understand why certain rulebooks are not available for activation.

**As a Platform Engineer**, I want structured validation output so that I can integrate rulebook quality checks into CI/CD pipelines.

## Acceptance Criteria

### Scenario: Valid Rulebook

- **GIVEN**: A syntactically correct EDA rulebook
- **WHEN**: APME scans the rulebook
- **THEN**: No E-series violations are reported

### Scenario: Invalid Rulebook Syntax

- **GIVEN**: A rulebook with YAML syntax errors or invalid structure
- **WHEN**: APME scans the rulebook
- **THEN**: E001 (rulebook syntax) violations are reported with file, line, and error details

### Scenario: Missing Required Fields

- **GIVEN**: A rulebook with a rule missing the required `condition` field
- **WHEN**: APME scans the rulebook
- **THEN**: E002 (missing required field) violation is reported

### Scenario: Invalid Action Reference

- **GIVEN**: A rulebook referencing a non-existent job template
- **WHEN**: APME scans the rulebook with AAP context
- **THEN**: E003 (invalid action reference) violation is reported

## Proposed Rules

| Rule ID | Name | Severity | Description |
|---------|------|----------|-------------|
| E001 | rulebook-syntax | error | Validates rulebook YAML structure and schema |
| E002 | rulebook-required-fields | error | Checks for required fields (name, condition, action) |
| E003 | rulebook-action-reference | warning | Validates action references (job_template, workflow) |
| E004 | rulebook-source-plugin | warning | Validates source plugin configuration |
| E005 | rulebook-condition-syntax | error | Validates condition expression syntax |

**Note**: The E-series rule IDs are proposed pending an ADR-008 amendment. ADR-008 currently defines L/M/R/P/SEC categories. Adding E (EDA) requires updating ADR-008 to include the new category.

## Inputs / Outputs

### Inputs

| Name | Type | Description | Required |
|------|------|-------------|----------|
| Rulebook file | YAML | EDA rulebook content | Yes |
| AAP context | Optional | Controller inventory for action validation | No |

### Outputs

| Name | Type | Description |
|------|------|-------------|
| Violations | List[Violation] | E-series rule violations with metadata |
| Validation summary | Object | Count of errors, warnings by rule |

## Dependencies

### Internal

- REQ-001: Core Scanning Engine (parser infrastructure)
- REQ-004: Enterprise Integration (EDA UI integration)

### External

- EDA rulebook schema specification
- ansible-rulebook for schema reference

## Non-Functional Requirements

- **Performance**: Rulebook validation < 1 second per file
- **Compatibility**: Support current EDA rulebook schema

## Open Questions

- [ ] Should APME validate source plugin configurations against installed plugins?
- [ ] How does APME obtain AAP context for action reference validation? (See DR-014)
- [ ] Should E-series rules be in a separate validator or integrated into existing?

## References

- [AAPRFE-2642](https://redhat.atlassian.net/browse/AAPRFE-2642) - Original customer RFE
- [ansible-rulebook](https://github.com/ansible/ansible-rulebook) - Rulebook schema reference
- DR-014: EDA Integration Approach

---

## Change History

| Date | Author | Change |
|------|--------|--------|
| 2026-03-25 | Phil (AI-assisted) | Initial draft from AAPRFE-2642 |
