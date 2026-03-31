"""Native rule L061: set_fact + loop + when is a scaling anti-pattern.

Using ``set_fact`` inside a ``loop`` (or ``with_*``) with a ``when`` conditional
to build a filtered subset is O(n) task evaluations.  A single Jinja2 filter
expression (``selectattr``, ``select``, ``reject``, etc.) achieves the same
result in one pass.
"""

from dataclasses import dataclass
from typing import cast

from apme_engine.engine.models import (
    AnsibleRunContext,
    Rule,
    RuleResult,
    RunTargetType,
    Severity,
    YAMLDict,
)
from apme_engine.engine.models import (
    RuleTag as Tag,
)

_SET_FACT_MODULES = frozenset(
    {
        "ansible.builtin.set_fact",
        "ansible.legacy.set_fact",
        "set_fact",
    }
)

_WITH_KEYS = frozenset(
    {
        "with_items",
        "with_list",
        "with_dict",
        "with_flattened",
        "with_together",
        "with_subelements",
        "with_sequence",
        "with_nested",
        "with_cartesian",
        "with_indexed_items",
        "with_ini",
        "with_file",
        "with_fileglob",
        "with_lines",
        "with_inventory_hostnames",
        "with_random_choice",
    }
)


def _has_loop(task_spec: object) -> bool:
    """Return True if the task uses any looping construct.

    Checks both the modern ``loop:`` field and legacy ``with_*`` options.

    Args:
        task_spec: The ``Task`` spec from a ``TaskCall``.

    Returns:
        True when a loop is present on the task.
    """
    loop = getattr(task_spec, "loop", None)
    if loop:
        return True
    options: dict[str, object] = getattr(task_spec, "options", None) or {}
    return any(options.get(wk) is not None for wk in _WITH_KEYS)


def _has_when(task_spec: object) -> bool:
    """Return True if the task has a ``when`` conditional.

    Args:
        task_spec: The ``Task`` spec from a ``TaskCall``.

    Returns:
        True when a ``when`` condition is present.
    """
    options: dict[str, object] = getattr(task_spec, "options", None) or {}
    when = options.get("when")
    if when is None:
        return False
    if isinstance(when, str):
        return bool(when.strip())
    if isinstance(when, list):
        return len(when) > 0
    return bool(when)


@dataclass
class SetFactLoopWhenRule(Rule):
    """Detect set_fact tasks that combine a loop with a when conditional.

    This pattern is an O(n) anti-pattern; Jinja2 filters like ``selectattr``,
    ``select``, and ``reject`` should be used instead.

    Attributes:
        rule_id: Rule identifier.
        description: Rule description.
        enabled: Whether the rule is enabled.
        name: Rule name.
        version: Rule version.
        severity: Severity level.
        tags: Rule tags.
    """

    rule_id: str = "L061"
    description: str = "set_fact with loop and when is a scaling anti-pattern; use Jinja2 filters instead"
    enabled: bool = True
    name: str = "SetFactLoopWhen"
    version: str = "v0.0.1"
    severity: str = Severity.MEDIUM
    tags: tuple[str, ...] = (Tag.QUALITY,)

    def match(self, ctx: AnsibleRunContext) -> bool:
        """Check if context has a task target.

        Args:
            ctx: AnsibleRunContext to evaluate.

        Returns:
            True if current target is a task.
        """
        if ctx.current is None:
            return False
        return bool(ctx.current.type == RunTargetType.Task)

    def process(self, ctx: AnsibleRunContext) -> RuleResult | None:
        """Check for the set_fact + loop + when anti-pattern.

        Args:
            ctx: AnsibleRunContext to process.

        Returns:
            RuleResult with verdict=True when all three signals are present.
        """
        task = ctx.current
        if task is None:
            return None

        spec = task.spec
        if spec is None:
            return None

        module = getattr(spec, "module", "") or ""
        resolved = getattr(task, "module", "") or ""
        effective_module = resolved or module

        is_set_fact = effective_module in _SET_FACT_MODULES
        has_loop = _has_loop(spec)
        has_when = _has_when(spec)

        verdict = is_set_fact and has_loop and has_when

        detail: YAMLDict = {}
        if verdict:
            detail["message"] = (
                "set_fact with loop and when is a scaling anti-pattern; "
                "use Jinja2 filters (selectattr, select, reject) instead"
            )

        return RuleResult(
            verdict=verdict,
            detail=cast("YAMLDict | None", detail),
            file=cast("tuple[str | int, ...] | None", task.file_info()),
            rule=self.get_metadata(),
        )
