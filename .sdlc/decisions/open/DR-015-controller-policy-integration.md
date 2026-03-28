# DR-015: Controller Policy Integration

## Status

Open

## Raised By

Phil (AI-assisted from AAPRFE-2258/2545 analysis) — 2026-03-25

## Category

Architecture

## Priority

High

---

## Question

How should APME's policy features (extended inputs, permissive mode) integrate with AAP Controller's existing policy enforcement?

## Context

Two RFEs require integration with Controller's policy enforcement:

1. **AAPRFE-2545 (REQ-013)**: Extended OPA inputs including parsed playbook content
2. **AAPRFE-2258 (REQ-014)**: Permissive (warn-only) mode for policies

Controller already has policy enforcement (OPA-based), but:
- Current inputs are limited to API endpoints, not playbook content
- No permissive mode exists today
- APME provides richer parsing than Controller's current capabilities

The question is whether APME enhances/replaces Controller's policy evaluation or runs alongside it.

## Impact of Not Deciding

- REQ-013 and REQ-014 can be implemented in APME standalone
- But policy enforcement in Controller won't benefit
- Two separate policy systems may confuse users

---

## Options Considered

### Option A: APME as Controller's Policy Backend

**Description**: Controller delegates policy evaluation to APME, which returns structured decisions. APME becomes the single policy engine.

**Pros**:
- Single source of truth for policies
- APME's rich parsing available to Controller
- Permissive mode implemented once

**Cons**:
- Tight coupling between Controller and APME
- Requires Controller architecture changes
- APME must be highly available

**Effort**: High

### Option B: APME Augments Controller's Inputs

**Description**: APME provides enriched policy inputs (parsed playbook) that Controller feeds to its existing OPA engine. Controller retains policy evaluation.

**Pros**:
- Less invasive to Controller
- APME provides data, Controller owns decisions
- Can be optional enhancement

**Cons**:
- Two OPA instances (duplication)
- Controller changes still needed
- Permissive mode in Controller, not APME

**Effort**: Medium

### Option C: Parallel Evaluation

**Description**: Controller evaluates its policies; APME evaluates additional policies. Results are merged.

**Pros**:
- No changes to Controller's existing policies
- APME adds new capabilities without replacing
- Gradual adoption

**Cons**:
- Complex merge logic
- Potential for conflicting decisions
- User confusion about which system evaluated what

**Effort**: Medium

### Option D: APME Pre-Flight Only

**Description**: APME evaluates policies before job submission (CI/CD, pre-commit). Controller's runtime policy is separate.

**Pros**:
- Clear separation of concerns
- No Controller changes
- Shift-left validation

**Cons**:
- Runtime policy gaps remain
- Users must configure two systems
- RFE for Controller integration not addressed

**Effort**: Low

---

## Recommendation

**Option B (APME augments inputs)** for near-term, with path to **Option A** long-term.

Rationale:
1. Option B is less invasive and can be shipped sooner
2. APME's parsing capability is the key differentiator
3. Controller team owns policy enforcement UX
4. Long-term, consolidating on APME as policy engine reduces complexity

---

## Related Artifacts

- [ADR-038](../../adrs/ADR-038-public-data-api.md): Public Data API for Platform Consumers (defines data sharing)
- [REQ-013](../../specs/REQ-013-opa-policy-inputs/requirement.md): Extended OPA Policy Input Schema
- [REQ-014](../../specs/REQ-014-policy-permissive-mode/requirement.md): Policy Permissive Mode
- [ADR-002](../../adrs/ADR-002-opa-rego-policy.md): OPA/Rego policy architecture
- [AAPRFE-2545](https://redhat.atlassian.net/browse/AAPRFE-2545): Expand OPA inputs
- [AAPRFE-2258](https://redhat.atlassian.net/browse/AAPRFE-2258): Permissive mode
- DR-004: AAP Pre-Flight Integration (deferred, broader context)

**Note**: ADR-038 answers the data-sharing question: Controller queries APME's public REST API by project URL. The "decided architecture" refers to ADR-038's pull model — APME exposes data, consumers query it. This most closely aligns with **Option D** (APME Pre-Flight Only) for the near term, since APME provides analysis and Controller/AAP decides how to consume it. The recommendation above (**Option B**) describes a tighter integration that would require Controller changes; this is a longer-term possibility pending Controller team alignment.

---

## Discussion Log

| Date | Participant | Input |
|------|-------------|-------|
| 2026-03-25 | Phil (AI) | Initial DR created from REQ-013/014 analysis |

---

## Decision

**Status**: Open
**Date**:
**Decided By**:

**Decision**:

**Rationale**:

**Action Items**:
- [ ] Discuss with Controller team on policy architecture direction
- [ ] Review Controller's current OPA integration code
- [ ] Prototype input augmentation approach

---

## Post-Decision Updates

| Date | Update |
|------|--------|
