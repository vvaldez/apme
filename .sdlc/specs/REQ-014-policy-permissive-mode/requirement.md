# REQ-014: Policy Permissive Mode

## Metadata

- **Phase**: PHASE-003 - Enterprise Dashboard
- **Status**: Draft
- **Created**: 2026-03-25
- **External Reference**: [AAPRFE-2258](https://redhat.atlassian.net/browse/AAPRFE-2258)
- **Priority**: Medium

## Overview

Add a "permissive" (warn-only) mode for policy enforcement, similar to SELinux's permissive mode. When enabled, policy violations are logged and reported but do not block job execution. This enables gradual policy rollout, allowing users to see what would be blocked without disrupting production workflows.

**Scope clarification**: APME provides policy analysis and advisory results. Enforcement (blocking/allowing jobs) happens at runtime in AAP Controller. APME also supports CI/CD environments that integrate with AAP, where policy checks can gate deployments before content reaches Controller.

## User Stories

**As a Platform Administrator**, I want to test new policies in permissive mode so that I can identify what would be blocked before enforcing the policy.

**As an Automation Team Lead**, I want users to see policy warnings so that they can proactively fix violations before enforcement begins.

**As a Security Engineer**, I want audit logs of policy violations (even when not enforced) so that I can assess policy impact and compliance gaps.

## Acceptance Criteria

### Scenario: Permissive Mode Enabled

- **GIVEN**: A policy with `mode: permissive`
- **WHEN**: Content violates the policy during APME scan
- **THEN**: APME reports advisory violations (warnings) AND AAP/CI decides whether to proceed

### Scenario: Enforcing Mode (Default)

- **GIVEN**: A policy with `mode: enforcing` (or no mode specified)
- **WHEN**: Content violates the policy during APME scan
- **THEN**: APME reports blocking violations AND AAP/CI can use this to block the job/deployment

### Scenario: Mode Transition

- **GIVEN**: A policy in permissive mode
- **WHEN**: The administrator changes the policy to enforcing mode
- **THEN**: Subsequent violations block execution

### Scenario: Audit Log

- **GIVEN**: Any policy violation (permissive or enforcing)
- **WHEN**: The violation is detected
- **THEN**: An audit log entry is created with policy name, violation details, and action taken

## Proposed Configuration

```yaml
# Policy configuration with mode
policies:
  - name: no-shell-module
    mode: permissive  # or "enforcing" (default)
    rules:
      - deny_shell_usage

  - name: require-become-false
    mode: enforcing
    rules:
      - check_become_setting
```

## Policy Modes

| Mode | Behavior | Use Case |
|------|----------|----------|
| `enforcing` | Block on violation | Production policy enforcement |
| `permissive` | Warn on violation, allow execution | Policy testing, gradual rollout |
| `disabled` | Skip policy evaluation | Emergency bypass |

## Inputs / Outputs

### Inputs

| Name | Type | Description | Required |
|------|------|-------------|----------|
| Policy mode | Enum | enforcing, permissive, disabled | No (default: enforcing) |
| Policy rules | List | OPA/Rego rules to evaluate | Yes |

### Outputs

| Name | Type | Description |
|------|------|-------------|
| Decision | Object | allow/deny with reason |
| Warnings | List | Violations that would block in enforcing mode |
| Audit entry | Object | Log entry for compliance tracking |

## Dependencies

### Internal

- REQ-003: Security & Compliance (policy framework)
- REQ-013: Extended OPA Policy Input Schema

### External

- AAP Controller (for job execution integration)
- Logging/audit infrastructure

## Non-Functional Requirements

- **Performance**: Mode check adds < 10ms to policy evaluation
- **Auditability**: All violations logged regardless of mode
- **Compatibility**: Existing policies default to enforcing mode

## Open Questions

- [ ] Where is policy mode configured? APME config, Controller settings, or per-policy?
- [ ] How does permissive mode interact with Controller's policy enforcement? (See DR-015)
- [ ] Should there be a global mode override (e.g., "all policies permissive during maintenance")?

## References

- [AAPRFE-2258](https://redhat.atlassian.net/browse/AAPRFE-2258) - Original customer RFE
- SELinux permissive mode (conceptual reference)
- DR-015: Controller Policy Integration

---

## Change History

| Date | Author | Change |
|------|--------|--------|
| 2026-03-25 | Phil (AI-assisted) | Initial draft from AAPRFE-2258 |
