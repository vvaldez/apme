"""AIProvider protocol and data models for graph-native AI remediation.

See ADR-024 for the rationale behind this abstraction and ADR-044
for the graph-native transform design.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from apme_engine.remediation.ai_context import AINodeContext


@dataclass
class AISkipped:
    """A violation the AI could not fix, with an explanation.

    Attributes:
        rule_id: Rule ID that was not fixed.
        line: 1-based line number of the violation.
        reason: Why the AI could not fix it.
        suggestion: Manual remediation guidance for the user.
    """

    rule_id: str
    line: int
    reason: str
    suggestion: str


@dataclass
class AINodeFix:
    """AI-generated fix for a single graph node.

    Returned by ``AIProvider.propose_node_fix()``.  Contains the
    corrected YAML text that will be applied via
    ``ContentGraph.apply_transform()``.

    Attributes:
        fixed_snippet: Corrected YAML text for the node.
        rule_ids: Rule IDs addressed by this fix.
        explanation: Human-readable summary of changes.
        confidence: Confidence score (0.0-1.0).
        skipped: Violations the AI could not fix.
    """

    fixed_snippet: str
    rule_ids: list[str] = field(default_factory=list)
    explanation: str = ""
    confidence: float = 0.85
    skipped: list[AISkipped] = field(default_factory=list)


class AIProvider(Protocol):
    """Protocol for AI-powered fix proposal providers.

    The engine depends only on this protocol, never on a concrete
    LLM client library.  See ADR-024.

    The sole entry point is ``propose_node_fix()``, which receives
    graph-derived context and returns a node-level fix.
    """

    async def propose_node_fix(
        self,
        context: AINodeContext,
        *,
        model: str | None = None,
    ) -> AINodeFix | None:
        """Propose a fix for a single graph node using graph-derived context.

        The graph-native entry point for AI remediation.  Receives an
        ``AINodeContext`` containing the node's YAML, violations, parent
        context, and sibling snippets — all derived from the ContentGraph.
        Returns an ``AINodeFix`` with the corrected YAML, or ``None``
        if the AI cannot fix any of the violations.

        Args:
            context: Graph-derived context bundle for this node.
            model: Optional model identifier.

        Returns:
            ``AINodeFix`` with corrected YAML, or ``None`` on failure.
        """
        ...
