"""Unit tests for native rule L061: set_fact + loop + when anti-pattern."""

from __future__ import annotations

from apme_engine.validators.native.rules._test_helpers import (
    make_context,
    make_role_call,
    make_role_spec,
    make_task_call,
    make_task_spec,
)
from apme_engine.validators.native.rules.L061_set_fact_loop_when import (
    SetFactLoopWhenRule,
    _has_loop,
    _has_when,
)


def _make_set_fact_task(
    module: str = "ansible.builtin.set_fact",
    *,
    loop: dict[str, object] | None = None,
    options: dict[str, object] | None = None,
    module_options: dict[str, object] | None = None,
) -> object:
    """Build a TaskCall for a set_fact task with optional loop and when.

    Args:
        module: Module name.
        loop: Loop dict for Task.loop.
        options: Task-level options (when, with_items, etc.).
        module_options: Module args.

    Returns:
        TaskCall configured for testing.
    """
    spec = make_task_spec(
        name="test task",
        module=module,
        options=options,
        module_options=module_options or {"test_var": "{{ items }}"},
    )
    if loop is not None:
        spec.loop = loop  # type: ignore[assignment]
    return make_task_call(spec)


# ---------------------------------------------------------------------------
# _has_loop helper
# ---------------------------------------------------------------------------


class TestHasLoop:
    """Tests for _has_loop helper."""

    def test_modern_loop(self) -> None:
        """Task.loop populated returns True."""
        spec = make_task_spec(module="ansible.builtin.set_fact")
        spec.loop = {"item": "{{ items }}"}  # type: ignore[assignment]
        assert _has_loop(spec) is True

    def test_with_items(self) -> None:
        """with_items in options returns True."""
        spec = make_task_spec(
            module="ansible.builtin.set_fact",
            options={"with_items": "{{ all_services }}"},
        )
        assert _has_loop(spec) is True

    def test_with_dict(self) -> None:
        """with_dict in options returns True."""
        spec = make_task_spec(
            module="ansible.builtin.set_fact",
            options={"with_dict": {"a": 1}},
        )
        assert _has_loop(spec) is True

    def test_no_loop(self) -> None:
        """No loop or with_* returns False."""
        spec = make_task_spec(module="ansible.builtin.set_fact")
        assert _has_loop(spec) is False


# ---------------------------------------------------------------------------
# _has_when helper
# ---------------------------------------------------------------------------


class TestHasWhen:
    """Tests for _has_when helper."""

    def test_string_when(self) -> None:
        """String when condition returns True."""
        spec = make_task_spec(
            module="ansible.builtin.set_fact",
            options={"when": "item.state == 'running'"},
        )
        assert _has_when(spec) is True

    def test_list_when(self) -> None:
        """List when condition returns True."""
        spec = make_task_spec(
            module="ansible.builtin.set_fact",
            options={"when": ["item.state == 'running'", "item.enabled"]},
        )
        assert _has_when(spec) is True

    def test_no_when(self) -> None:
        """Missing when returns False."""
        spec = make_task_spec(module="ansible.builtin.set_fact")
        assert _has_when(spec) is False

    def test_empty_when(self) -> None:
        """Empty string when returns False."""
        spec = make_task_spec(
            module="ansible.builtin.set_fact",
            options={"when": ""},
        )
        assert _has_when(spec) is False

    def test_empty_list_when(self) -> None:
        """Empty list when returns False."""
        spec = make_task_spec(
            module="ansible.builtin.set_fact",
            options={"when": []},
        )
        assert _has_when(spec) is False


# ---------------------------------------------------------------------------
# SetFactLoopWhenRule — positive cases (should trigger)
# ---------------------------------------------------------------------------


class TestL061Triggers:
    """Cases where L061 should fire."""

    def test_set_fact_loop_when_fqcn(self) -> None:
        """FQCN set_fact + loop + when triggers L061."""
        task = _make_set_fact_task(
            module="ansible.builtin.set_fact",
            loop={"item": "{{ items }}"},
            options={"when": "item.state == 'running'"},
        )
        ctx = make_context(task)  # type: ignore[arg-type]
        rule = SetFactLoopWhenRule()
        assert rule.match(ctx)
        result = rule.process(ctx)
        assert result is not None
        assert result.verdict is True
        assert result.rule is not None and result.rule.rule_id == "L061"
        assert result.detail is not None
        assert "anti-pattern" in result.detail["message"]

    def test_set_fact_with_items_when(self) -> None:
        """set_fact + with_items + when triggers L061."""
        task = _make_set_fact_task(
            module="ansible.builtin.set_fact",
            options={
                "with_items": "{{ all_services }}",
                "when": "item.state == 'running'",
            },
        )
        ctx = make_context(task)  # type: ignore[arg-type]
        rule = SetFactLoopWhenRule()
        result = rule.process(ctx)
        assert result is not None
        assert result.verdict is True

    def test_set_fact_short_name(self) -> None:
        """Short-form module name set_fact triggers L061."""
        task = _make_set_fact_task(
            module="set_fact",
            loop={"item": "{{ items }}"},
            options={"when": "item.role == 'admin'"},
        )
        ctx = make_context(task)  # type: ignore[arg-type]
        rule = SetFactLoopWhenRule()
        result = rule.process(ctx)
        assert result is not None
        assert result.verdict is True

    def test_set_fact_legacy_name(self) -> None:
        """Legacy ansible.legacy.set_fact triggers L061."""
        task = _make_set_fact_task(
            module="ansible.legacy.set_fact",
            loop={"item": "{{ items }}"},
            options={"when": "item.enabled"},
        )
        ctx = make_context(task)  # type: ignore[arg-type]
        rule = SetFactLoopWhenRule()
        result = rule.process(ctx)
        assert result is not None
        assert result.verdict is True

    def test_set_fact_with_dict_when(self) -> None:
        """set_fact + with_dict + when triggers L061."""
        task = _make_set_fact_task(
            module="ansible.builtin.set_fact",
            options={
                "with_dict": {"a": 1, "b": 2},
                "when": "item.value | bool",
            },
        )
        ctx = make_context(task)  # type: ignore[arg-type]
        rule = SetFactLoopWhenRule()
        result = rule.process(ctx)
        assert result is not None
        assert result.verdict is True

    def test_list_when_condition(self) -> None:
        """Multi-condition when list still triggers L061."""
        task = _make_set_fact_task(
            module="ansible.builtin.set_fact",
            loop={"item": "{{ items }}"},
            options={"when": ["item.a", "item.b"]},
        )
        ctx = make_context(task)  # type: ignore[arg-type]
        rule = SetFactLoopWhenRule()
        result = rule.process(ctx)
        assert result is not None
        assert result.verdict is True


# ---------------------------------------------------------------------------
# SetFactLoopWhenRule — negative cases (should NOT trigger)
# ---------------------------------------------------------------------------


class TestL061DoesNotTrigger:
    """Cases where L061 should not fire."""

    def test_set_fact_no_loop_no_when(self) -> None:
        """Plain set_fact (no loop, no when) does not trigger."""
        task = _make_set_fact_task(module="ansible.builtin.set_fact")
        ctx = make_context(task)  # type: ignore[arg-type]
        rule = SetFactLoopWhenRule()
        result = rule.process(ctx)
        assert result is not None
        assert result.verdict is False

    def test_set_fact_loop_no_when(self) -> None:
        """set_fact with loop but no when does not trigger."""
        task = _make_set_fact_task(
            module="ansible.builtin.set_fact",
            loop={"item": "{{ items }}"},
        )
        ctx = make_context(task)  # type: ignore[arg-type]
        rule = SetFactLoopWhenRule()
        result = rule.process(ctx)
        assert result is not None
        assert result.verdict is False

    def test_set_fact_when_no_loop(self) -> None:
        """set_fact with when but no loop does not trigger."""
        task = _make_set_fact_task(
            module="ansible.builtin.set_fact",
            options={"when": "use_replica | default(false)"},
        )
        ctx = make_context(task)  # type: ignore[arg-type]
        rule = SetFactLoopWhenRule()
        result = rule.process(ctx)
        assert result is not None
        assert result.verdict is False

    def test_debug_loop_when(self) -> None:
        """Non-set_fact module (debug) with loop + when does not trigger."""
        spec = make_task_spec(
            module="ansible.builtin.debug",
            options={
                "when": "item.state == 'running'",
            },
            module_options={"msg": "{{ item }}"},
        )
        spec.loop = {"item": "{{ items }}"}  # type: ignore[assignment]
        task = make_task_call(spec)
        ctx = make_context(task)
        rule = SetFactLoopWhenRule()
        result = rule.process(ctx)
        assert result is not None
        assert result.verdict is False

    def test_role_target_no_match(self) -> None:
        """Role targets do not match (match returns False)."""
        role = make_role_call(make_role_spec(name="test-role"))
        ctx = make_context(role)
        rule = SetFactLoopWhenRule()
        assert not rule.match(ctx)

    def test_set_fact_empty_when(self) -> None:
        """set_fact with loop + empty when string does not trigger."""
        task = _make_set_fact_task(
            module="ansible.builtin.set_fact",
            loop={"item": "{{ items }}"},
            options={"when": ""},
        )
        ctx = make_context(task)  # type: ignore[arg-type]
        rule = SetFactLoopWhenRule()
        result = rule.process(ctx)
        assert result is not None
        assert result.verdict is False
