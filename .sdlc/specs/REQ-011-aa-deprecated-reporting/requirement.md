# REQ-011: Automation Analytics Deprecated Module Reporting

## Metadata

- **Phase**: PHASE-003 - Enterprise Dashboard
- **Status**: Draft
- **Created**: 2026-03-25
- **External Reference**: [AAPRFE-1607](https://redhat.atlassian.net/browse/AAPRFE-1607)

## Overview

Provide deprecated module detection data to Automation Analytics so customers can generate reports showing which Ansible jobs use deprecated modules. This enables proactive upgrade planning before ansible-core version migrations.

**Architecture**: This REQ is a specific consumer use case of ADR-038 (Public Data API). Deprecated module data is available via the Gateway REST API; Controller queries APME by project URL and includes the data in its telemetry to AA.

## User Stories

**As an AAP Administrator**, I want to see a report of all jobs using deprecated modules so that I can plan remediation before upgrading ansible-core.

**As a Platform Engineer**, I want deprecated module warnings captured and aggregated so that I don't have to manually parse job logs.

**As a Release Manager**, I want visibility into deprecated module usage across all automation so that I can assess upgrade readiness.

## Acceptance Criteria

### Scenario: Deprecated Module Detection

- **GIVEN**: An Ansible playbook using a deprecated module (e.g., `include` instead of `include_tasks`)
- **WHEN**: The playbook is scanned by APME
- **THEN**: L004 (deprecated module) violations are detected with module name and deprecation details

### Scenario: Data Available in Automation Analytics

- **GIVEN**: APME has scanned playbooks with deprecated modules
- **WHEN**: Scan results are made available to Automation Analytics (mechanism TBD — how APME services integrate with AAP is under discussion)
- **THEN**: The deprecated module data is available for dashboard/report generation

### Scenario: Report Generation

- **GIVEN**: Deprecated module data is in Automation Analytics
- **WHEN**: A user views the deprecation report
- **THEN**: The report shows: job name, deprecated module, recommended replacement, job template location

## Inputs / Outputs

### Inputs

| Name | Type | Description | Required |
|------|------|-------------|----------|
| Scan results | `ScanResponse` | APME scan results containing L004/M-rule violations | Yes |
| Job metadata | TBD | AAP job context (job ID, template, inventory) | TBD |

### Outputs

| Name | Type | Description |
|------|------|-------------|
| Deprecation report | Dashboard/Export | Aggregated view of deprecated module usage |
| Per-job violations | List | Deprecated modules per job with replacement guidance |

## Behavior

### Happy Path

1. AAP job executes playbook
2. APME scans playbook (pre-flight or post-run)
3. L004/M001-M004 violations detected for deprecated modules
4. Scan results made available for centralized metrics and reporting (integration mechanism TBD — see DR-013)
5. User views deprecation report in AA dashboard
6. Report shows jobs, modules, and remediation guidance

### Edge Cases

| Case | Handling |
|------|----------|
| Module deprecated in one ansible-core version but not another | Include version context in report |
| No deprecated modules found | Report shows clean status |
| Scan fails | Report indicates scan coverage gap |

### Error Conditions

| Error | Cause | Response |
|-------|-------|----------|
| Invalid scan data | Malformed response | Log error, skip record |

## Dependencies

### Internal

- REQ-001: Core Scanning Engine (L004, M001-M004 rules)
- REQ-004: Enterprise Integration (AAP/AA connectivity)
- **ADR-038**: Public Data API (defines how Controller queries APME)

### External

- Controller: Queries APME and includes data in AA telemetry
- Automation Analytics: Dashboard/report visualization

## Non-Functional Requirements

- **Performance**: Scan overhead < 5% of job execution time
- **Security**: Data in transit encrypted (TLS)
- **Compatibility**: Support AAP 2.4+ and AA current version

## Open Questions

- [ ] What is the integration mechanism with Automation Analytics? (See DR-013)
- [ ] Is this pre-flight scanning, post-run analysis, or both?
- [ ] What job metadata is available from AAP for correlation?
- [ ] Does AA have an existing schema for deprecation data?

## References

- [AAPRFE-1607](https://redhat.atlassian.net/browse/AAPRFE-1607) - Original customer RFE
- [ADR-008](../../adrs/ADR-008-rule-id-conventions.md) - Rule ID conventions (L004 = deprecated module)
- [ADR-038](../../adrs/ADR-038-public-data-api.md) - Public Data API (defines integration pattern)
- [DR-013](../../decisions/open/DR-013-aa-integration-approach.md) - AA Integration Approach (reframed per ADR-038)
- [DR-004](../../decisions/closed/deferred/DR-004-aap-integration.md) - AAP Pre-Flight Integration (deferred)

---

## Change History

| Date | Author | Change |
|------|--------|--------|
| 2026-03-25 | Claude | Initial draft from AAPRFE-1607 |
