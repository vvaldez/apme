# DR-014: EDA Integration Approach

## Status

Open

## Raised By

Phil (AI-assisted from AAPRFE-2642 analysis) — 2026-03-25

## Category

Architecture

## Priority

High

---

## Question

How should APME's EDA rulebook validation integrate with the EDA platform to surface validation results in the UI?

## Context

REQ-012 defines rulebook validation rules (E001-E005) that APME will implement. The question is how these validation results reach EDA users:

- Currently, EDA silently ignores invalid rulebooks during project import
- Users have no visibility into why rulebooks don't appear in the activation list
- APME can provide structured validation output, but EDA needs to consume it

This is similar to DR-013 (AA integration) but specific to EDA.

## Impact of Not Deciding

- REQ-012 can be implemented, but validation results won't reach users
- The core problem (silent failures) remains unsolved
- Customer RFE (AAPRFE-2642) is only partially addressed

---

## Options Considered

### Option A: EDA Calls APME During Project Import

**Description**: EDA's project sync process calls APME to validate rulebooks before import. Invalid rulebooks are marked with validation errors in EDA's database.

**Pros**:
- Validation happens at the natural point (import)
- EDA owns the UI for displaying errors
- APME remains a validation service

**Cons**:
- Requires EDA code changes to call APME
- Dependency on APME availability during import
- May slow down project sync

**Effort**: Medium

### Option B: APME Pre-Flight in EDA Activation

**Description**: APME validates rulebooks when users attempt to create an activation, similar to Controller's pre-flight checks.

**Pros**:
- Validation at point of use (activation creation)
- APME integration pattern consistent with Controller
- EDA code changes more contained

**Cons**:
- Invalid rulebooks still appear in list (validated on selection)
- Delayed feedback (not at import time)

**Effort**: Medium

### Option C: Hub Validates on Upload

**Description**: Private Automation Hub validates rulebook content when projects are uploaded, before they reach EDA.

**Pros**:
- Single validation point
- Consistent with collection validation
- EDA doesn't need APME integration

**Cons**:
- Requires Hub changes
- Git-synced projects bypass Hub
- Different flow than most EDA users

**Effort**: High

### Option D: Standalone Validation (CI/CD Only)

**Description**: APME provides rulebook validation via CLI/API. Users run validation in CI/CD pipelines before deploying to EDA.

**Pros**:
- No EDA/Hub changes required
- Works today once REQ-012 is implemented
- Shift-left validation

**Cons**:
- Doesn't solve UI visibility problem
- Requires users to set up CI/CD integration
- Doesn't fully address RFE

**Effort**: Low

---

## Recommendation

**Option A (EDA calls APME during import)** with **Option D (CLI)** as fallback.

Rationale:
1. Option A solves the core UX problem (users see why rulebooks fail)
2. Option D provides immediate value for CI/CD users
3. Consistent with how Controller might integrate APME for playbook validation

---

## Related Artifacts

- [ADR-038](../../adrs/ADR-038-public-data-api.md): Public Data API for Platform Consumers (defines the pull model)
- [REQ-012](../../specs/REQ-012-eda-rulebook-validation/requirement.md): EDA Rulebook Validation
- [REQ-004](../../specs/REQ-004-enterprise-integration/requirement.md): Enterprise Integration
- [AAPRFE-2642](https://redhat.atlassian.net/browse/AAPRFE-2642): Original customer RFE
- DR-004: AAP Pre-Flight Integration (deferred, related pattern)

**Note**: ADR-038 defines the data-sharing mechanism. Options A (EDA calls APME during import) and D (standalone CLI/API) are both instances of ADR-038's pull model — EDA would query the Gateway REST API by project URL. The question here is *when* EDA calls APME, not *how* (ADR-038 answers the how).

---

## Discussion Log

| Date | Participant | Input |
|------|-------------|-------|
| 2026-03-25 | Phil (AI) | Initial DR created from REQ-012 analysis |

---

## Decision

**Status**: Open
**Date**:
**Decided By**:

**Decision**:

**Rationale**:

**Action Items**:
- [ ] Discuss with EDA team on integration approach
- [ ] Review EDA project sync architecture
- [ ] Prototype APME validation call from EDA

---

## Post-Decision Updates

| Date | Update |
|------|--------|
