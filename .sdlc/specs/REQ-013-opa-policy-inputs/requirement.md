# REQ-013: Extended OPA Policy Input Schema

## Metadata

- **Phase**: PHASE-003 - Enterprise Dashboard
- **Status**: Draft
- **Created**: 2026-03-25
- **External Reference**: [AAPRFE-2545](https://redhat.atlassian.net/browse/AAPRFE-2545)
- **Priority**: High

## Overview

Extend the OPA policy input schema to include parsed playbook content, enabling richer policy enforcement. Currently, AAP's policy enforcement is limited to specific API endpoints. This feature exposes the full playbook AST (tasks, modules, variables, roles) to OPA policies, allowing policies like "block playbooks that use shell module" or "require become: false for production inventories."

## Current OPA Input Schema

APME's OPA validator already passes a parsed AST to Rego rules. Each node includes:

```json
{
  "type": "task|play|role|...",
  "module": "ansible.builtin.copy",
  "key": "copy",
  "file": "/path/to/playbook.yml",
  "line": 42,
  "column": 5,
  "content": { /* raw task content */ }
}
```

This schema is defined in `src/apme_engine/validators/opa/` and used by existing rules (L002-L025, R118). The current input is **per-node** — policies evaluate one AST node at a time.

## Proposed Extensions

This REQ extends the current schema to support **cross-node** policy evaluation:

## User Stories

**As a Security Engineer**, I want to write OPA policies that inspect playbook content so that I can enforce security standards at the code level.

**As a Platform Administrator**, I want to block jobs that use dangerous modules (shell, raw, command) so that I can maintain compliance with security policies.

**As an Automation Architect**, I want policies that check variable references so that I can ensure playbooks don't expose sensitive data.

## Acceptance Criteria

### Scenario: Policy Accesses Task List

- **GIVEN**: An OPA policy that checks for shell module usage
- **WHEN**: A playbook using `ansible.builtin.shell` is submitted
- **THEN**: The policy can access the task list and detect the shell module usage

### Scenario: Policy Accesses Variables

- **GIVEN**: An OPA policy that checks for hardcoded passwords
- **WHEN**: A playbook with `password: "secret"` is submitted
- **THEN**: The policy can access variable definitions and flag the violation

### Scenario: Policy Accesses Role Dependencies

- **GIVEN**: An OPA policy that checks for approved roles only
- **WHEN**: A playbook includes an unapproved role
- **THEN**: The policy can access role references and block execution

## Proposed Input Schema

```json
{
  "playbook": {
    "path": "string",
    "plays": [
      {
        "name": "string",
        "hosts": "string",
        "become": "boolean",
        "tasks": [
          {
            "name": "string",
            "module": "string",
            "module_fqcn": "string",
            "args": {},
            "when": "string",
            "loop": "any",
            "register": "string"
          }
        ],
        "roles": [
          {
            "name": "string",
            "fqcn": "string"
          }
        ],
        "vars": {},
        "handlers": []
      }
    ]
  },
  "context": {
    "inventory": "string",
    "job_template": "string",
    "organization": "string"
  }
}
```

## Inputs / Outputs

### Inputs

| Name | Type | Description | Required |
|------|------|-------------|----------|
| Playbook content | YAML | Raw playbook for parsing | Yes |
| Job context | Object | AAP context (inventory, org, template) | No |

### Outputs

| Name | Type | Description |
|------|------|-------------|
| Policy input | Object | Extended schema with parsed playbook |
| Policy decision | Object | OPA evaluation result |

## Dependencies

### Internal

- REQ-001: Core Scanning Engine (tree parser)
- REQ-003: Security & Compliance (policy rules)

### External

- OPA/Rego runtime
- AAP Controller for job context

## Non-Functional Requirements

- **Performance**: Schema generation < 500ms per playbook
- **Security**: Sanitize sensitive data before policy evaluation
- **Compatibility**: Backward compatible with existing policies

## Open Questions

- [ ] How much playbook detail should be exposed? Full AST vs. summary?
- [ ] Should variable values be included or just variable names?
- [ ] How does this integrate with AAP Controller's policy enforcement? (See DR-015)

## References

- [AAPRFE-2545](https://redhat.atlassian.net/browse/AAPRFE-2545) - Original customer RFE
- [ansible-policy](https://github.com/ansible/ansible-policy) - Reference implementation
- [ADR-002](../../adrs/ADR-002-opa-rego-policy.md) - OPA/Rego policy architecture
- [ADR-038](../../adrs/ADR-038-public-data-api.md) - Public Data API for platform consumers
- DR-015: Controller Policy Integration

---

## Change History

| Date | Author | Change |
|------|--------|--------|
| 2026-03-25 | Phil (AI-assisted) | Initial draft from AAPRFE-2545 |
