"""Transform registry — maps rule IDs to deterministic node-level fix functions.

Each transform has the signature ``(CommentedMap, ViolationDict) -> bool``:
it modifies the task CommentedMap in-place and returns True if a change was
made.  Used by ``ContentGraph.apply_transform()`` in the graph-aware
convergence loop.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import TYPE_CHECKING

from apme_engine.engine.models import ViolationDict

if TYPE_CHECKING:
    from ruamel.yaml.comments import CommentedMap

NodeTransformFn = Callable[["CommentedMap", ViolationDict], bool]


class TransformRegistry:
    """Maps rule IDs to node-level transform functions."""

    def __init__(self) -> None:
        """Initialize an empty transform registry."""
        self._node: dict[str, NodeTransformFn] = {}

    def register(
        self,
        rule_id: str,
        *,
        node: NodeTransformFn | None = None,
    ) -> None:
        """Register a node transform function for a rule ID.

        Args:
            rule_id: Rule identifier (e.g. L007, M001).
            node: Node transform (CommentedMap, violation) -> bool.

        Raises:
            ValueError: If *node* is None.
        """
        if node is None:
            msg = f"register({rule_id!r}): node transform is required"
            raise ValueError(msg)
        self._node[rule_id] = node

    def get_node_transform(self, rule_id: str) -> NodeTransformFn | None:
        """Return the node-level transform for a rule, or None.

        Args:
            rule_id: Rule identifier to look up.

        Returns:
            NodeTransformFn if registered, else None.
        """
        return self._node.get(rule_id)

    def __contains__(self, rule_id: str) -> bool:
        """Check if a rule has a registered transform.

        Args:
            rule_id: Rule identifier to look up.

        Returns:
            True if rule_id is registered.
        """
        return rule_id in self._node

    def __len__(self) -> int:
        """Return the number of registered rule IDs.

        Returns:
            Count of registered rule IDs.
        """
        return len(self._node)

    def __iter__(self) -> Iterator[str]:
        """Iterate over registered rule IDs in sorted order.

        Returns:
            Iterator of rule ID strings (deterministic, sorted).
        """
        return iter(sorted(self._node))

    @property
    def rule_ids(self) -> list[str]:
        """Return sorted list of registered rule IDs.

        Returns:
            Sorted list of rule ID strings.
        """
        return sorted(self._node)

    def apply_node(
        self,
        rule_id: str,
        task: CommentedMap,
        violation: ViolationDict,
    ) -> bool:
        """Apply a node-level transform directly on a CommentedMap.

        Used by ``ContentGraph.apply_transform()`` in the graph-aware
        convergence loop.

        Args:
            rule_id: Rule identifier.
            task: Task/handler CommentedMap to modify in-place.
            violation: Violation dict for context.

        Returns:
            True if the transform was applied.
        """
        nfn = self._node.get(rule_id)
        if nfn is None:
            return False
        return nfn(task, violation)
