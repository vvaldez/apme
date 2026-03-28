# DR-013: Automation Analytics Integration Approach

## Status

Open (reframed per ADR-038)

## Raised By

Claude (from AAPRFE-1607 analysis) — 2026-03-25

## Category

Architecture

## Priority

Medium (narrowed by ADR-038)

---

## Question

How does Controller/AA consume the ADR-038 public API for deprecated module reporting?

## Context

**ADR-038 (Public Data API)** defines how platform consumers access APME data:
- **Pull model**: Consumers query the Gateway REST API by project URL
- **Webhook notifications**: Consumers subscribe to scan-complete events
- **Controller as bridge**: Controller knows the project SCM URL, queries APME for health/violations, and AA gets the data transitively through Controller's existing telemetry

This DR is now a **specific consumer use case** within the ADR-038 architecture. The original question ("how does APME send data to AA?") is answered by ADR-038: consumers pull from the public REST API.

The narrower question is: **What AA-specific behaviors are needed beyond the standard ADR-038 pattern?**

APME already detects deprecated modules via:
- **L004**: Deprecated module usage
- **M001-M004**: Modernization rules for outdated patterns

## Impact of Not Deciding

- Cannot proceed with REQ-011 implementation
- Customer use case (AAPRFE-1607) remains unaddressed
- Telco customers cannot plan ansible-core upgrades effectively

---

## Options (Post-ADR-038)

ADR-038 collapses the original options (event-driven, direct API, Insights client, export-only) into a single pattern: **Controller queries APME's public REST API**.

The remaining questions are AA-specific:

### Option A: Controller Includes APME Data in Existing AA Telemetry

**Description**: Controller queries APME for project health/violations and includes the deprecated module data in its existing telemetry to AA.

**Pros**:
- Uses existing Controller → AA data pipeline
- No AA API changes needed
- APME data automatically correlated with job context

**Cons**:
- Requires Controller code to query APME and include data
- AA dashboard needs to visualize new data fields

**Effort**: Medium (Controller-side)

### Option B: AA Directly Queries APME (Bypass Controller)

**Description**: AA subscribes to APME webhooks or periodically pulls project health data directly.

**Pros**:
- Decoupled from Controller
- AA controls the polling/refresh cadence

**Cons**:
- Requires AA to correlate project URLs with Controller job metadata
- Additional service-to-service auth
- Duplicates ADR-038 consumer pattern

**Effort**: High (AA-side)

### Option C: Dashboard-Only (No AA Integration)

**Description**: APME provides deprecated module data via its own dashboard (REQ-008/REQ-010 scope). Customers who want AA reports can export and import.

**Pros**:
- No cross-product integration needed
- Works with ADR-038's existing public API
- Customers already have export capability

**Cons**:
- Doesn't address RFE request for AA-native reports
- Manual workflow for customers

**Effort**: Low

---

## Recommendation

**Option A (Controller includes APME data in AA telemetry)**.

Rationale:
1. Aligns with ADR-038's "Controller as bridge" pattern
2. Controller already has job context that AA needs for correlation
3. AA team can add dashboard visualizations without API changes
4. Consistent with how other Controller data flows to AA

---

## Related Artifacts

- [ADR-038](../../adrs/ADR-038-public-data-api.md): Public Data API for Platform Consumers (defines pull model)
- [REQ-011](../../specs/REQ-011-aa-deprecated-reporting/requirement.md): Automation Analytics Deprecated Module Reporting
- [DR-004](../closed/deferred/DR-004-aap-integration.md): AAP Pre-Flight Integration (deferred)
- [REQ-004](../../specs/REQ-004-enterprise-integration/requirement.md): Enterprise Integration
- [AAPRFE-1607](https://redhat.atlassian.net/browse/AAPRFE-1607): Original customer RFE

---

## Discussion Log

| Date | Participant | Input |
|------|-------------|-------|
| 2026-03-25 | Claude | Initial DR created from AAPRFE-1607 analysis |
| 2026-03-25 | — | AA team comment on Jira suggests 2H 2026 reporting roadmap |
| 2026-03-26 | cidrblock | ADR-038 defines public data API; reframe DR to narrower question |
| 2026-03-26 | Claude | Reframed per ADR-038; updated options to post-ADR-038 choices |

---

## Decision

**Status**: Open
**Date**:
**Decided By**:

**Decision**:

**Rationale**:

**Action Items**:
- [ ] Coordinate with AA team on reporting roadmap
- [ ] Review AA API documentation for integration patterns
- [ ] Determine if pre-flight or post-run scanning is preferred

---

## Post-Decision Updates

| Date | Update |
|------|--------|
