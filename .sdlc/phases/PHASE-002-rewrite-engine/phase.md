# PHASE-002: Rewrite Engine

## Status

Implemented

## Overview

Automated remediation engine with deterministic transforms for renamed parameters, module redirects, and syntax changes. Convergence loop re-scans until stable. AI-assisted remediation for complex cases via Abbenay (PHASE-004).

## Goals

- Implement safe auto-fixes for renamed parameters and module redirects
- Support iterative processing via convergence loop (scan → transform → re-scan)
- Generate before/after diff views for user approval
- Comment-preserving YAML transforms using ruamel.yaml

## Success Criteria

- [x] Auto-fix capability for common deprecations via TransformRegistry
- [x] Convergence loop uncovers nested issues iteratively
- [x] Diff generation shows before/after changes
- [x] No destructive changes without user approval
- [x] Graph-aware remediation engine integrated into FixSession path (ADR-044)

## Requirements

| REQ | Name | Status |
|-----|------|--------|
| REQ-002 | Automated Remediation | Implemented |

## Dependencies

- PHASE-001: CLI Scanner

## Timeline

- **Implemented**: 2026-03 (REQ-002 complete, ADR-044 Phase 3 merged)
