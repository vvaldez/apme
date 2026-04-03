"""Remediation engine — graph-based convergence + AI escalation for scan violations."""

from apme_engine.remediation.ai_provider import AIProvider, AISkipped
from apme_engine.remediation.graph_engine import FilePatch, GraphFixReport
from apme_engine.remediation.partition import is_finding_resolvable
from apme_engine.remediation.registry import TransformRegistry

__all__ = [
    "AIProvider",
    "AISkipped",
    "FilePatch",
    "GraphFixReport",
    "TransformRegistry",
    "is_finding_resolvable",
]
