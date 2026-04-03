"""Tests for AI escalation: AISkipped, discover_abbenay, JSON extraction, best practices."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

from apme_engine.remediation.abbenay_provider import (
    _extract_json_object,
    _get_best_practices_for_rules,
    _load_best_practices,
    discover_abbenay,
)
from apme_engine.remediation.ai_provider import (
    AISkipped,
)

# ---------------------------------------------------------------------------
# AISkipped tests
# ---------------------------------------------------------------------------


class TestAISkipped:
    """Tests for the AISkipped dataclass."""

    def test_create_skipped(self) -> None:
        """AISkipped fields are set correctly."""
        s = AISkipped(
            rule_id="P002",
            line=45,
            reason="Cannot determine valid params for custom module.",
            suggestion="Remove 'invalid_param' if not valid.",
        )
        assert s.rule_id == "P002"
        assert s.line == 45
        assert "custom module" in s.reason
        assert "invalid_param" in s.suggestion


# ---------------------------------------------------------------------------
# discover_abbenay tests
# ---------------------------------------------------------------------------


class TestDiscoverAbbenay:
    """Tests for Abbenay daemon auto-discovery."""

    def test_discover_from_xdg(self, tmp_path: Path) -> None:
        """Discovers socket via XDG_RUNTIME_DIR.

        Args:
            tmp_path: Pytest temporary directory fixture.
        """
        sock_dir = tmp_path / "abbenay"
        sock_dir.mkdir()
        sock_file = sock_dir / "daemon.sock"
        sock_file.touch()

        with patch.dict(os.environ, {"XDG_RUNTIME_DIR": str(tmp_path)}):
            result = discover_abbenay()

        assert result == f"unix://{sock_file}"

    def test_discover_from_tmp(self, tmp_path: Path) -> None:
        """Falls back to /tmp/abbenay/daemon.sock when XDG and /run/user paths miss.

        Args:
            tmp_path: Pytest temporary directory fixture.
        """
        sock_dir = tmp_path / "abbenay"
        sock_dir.mkdir(parents=True)
        sock_file = sock_dir / "daemon.sock"
        sock_file.touch()

        orig_path = Path

        def _path_factory(*args: object, **kwargs: object) -> Path:
            if args == ("/tmp/abbenay/daemon.sock",):
                return sock_file
            if (
                len(args) == 1
                and isinstance(args[0], str)
                and "/run/user/" in args[0]
                and args[0].endswith("/abbenay/daemon.sock")
            ):
                return orig_path(tmp_path / "no-run-user-sock" / "daemon.sock")
            return orig_path(*args, **kwargs)  # type: ignore[arg-type]

        with (
            patch.dict(os.environ, {}, clear=True),
            patch(
                "apme_engine.remediation.abbenay_provider.Path",
                side_effect=_path_factory,
            ),
        ):
            result = discover_abbenay()

        assert result == f"unix://{sock_file}"

    def test_discover_returns_none(self, tmp_path: Path) -> None:
        """Returns None when no socket exists.

        Args:
            tmp_path: Pytest temporary directory fixture.
        """
        orig_path = Path

        def _path_factory(*args: object, **kwargs: object) -> Path:
            if len(args) == 1 and isinstance(args[0], str) and args[0].endswith("/abbenay/daemon.sock"):
                return orig_path(tmp_path / "missing" / "daemon.sock")
            return orig_path(*args, **kwargs)  # type: ignore[arg-type]

        with (
            patch.dict(os.environ, {"XDG_RUNTIME_DIR": str(tmp_path)}),
            patch(
                "apme_engine.remediation.abbenay_provider.Path",
                side_effect=_path_factory,
            ),
        ):
            result = discover_abbenay()

        assert result is None


# ---------------------------------------------------------------------------
# _extract_json_object tests
# ---------------------------------------------------------------------------


class TestExtractJsonObject:
    """Tests for _extract_json_object which handles LLM preamble stripping."""

    def test_clean_json(self) -> None:
        """Parses clean JSON directly."""
        data = _extract_json_object('{"patches": []}')
        assert data == {"patches": []}

    def test_markdown_fences(self) -> None:
        """Strips markdown code fences."""
        data = _extract_json_object('```json\n{"patches": []}\n```')
        assert data == {"patches": []}

    def test_thinking_preamble(self) -> None:
        """Strips reasoning text before the JSON object."""
        text = (
            "Looking at the violations, I need to analyze the task context.\n\n"
            '{"patches": [{"rule_id": "M001", "line_start": 1, "line_end": 1, '
            '"fixed_lines": "fixed\\n", "explanation": "ok", "confidence": 0.9}]}'
        )
        data = _extract_json_object(text)
        assert data is not None
        assert len(data["patches"]) == 1
        assert data["patches"][0]["rule_id"] == "M001"

    def test_trailing_text(self) -> None:
        """Ignores text after the JSON object."""
        text = '{"patches": []} \n\nLet me know if you need anything else.'
        data = _extract_json_object(text)
        assert data == {"patches": []}

    def test_preamble_and_trailing(self) -> None:
        """Strips both preamble and trailing text."""
        text = 'Here is the fix:\n{"skipped": []}\nHope that helps!'
        data = _extract_json_object(text)
        assert data == {"skipped": []}

    def test_nested_braces(self) -> None:
        """Handles nested objects correctly."""
        inner = json.dumps(
            {
                "patches": [
                    {
                        "rule_id": "L026",
                        "line_start": 1,
                        "line_end": 2,
                        "fixed_lines": "- name: test\n",
                        "explanation": "ok",
                        "confidence": 0.9,
                    }
                ]
            }
        )
        text = f"Analysis complete.\n{inner}\nDone."
        data = _extract_json_object(text)
        assert data is not None
        assert data["patches"][0]["rule_id"] == "L026"

    def test_no_json(self) -> None:
        """Returns None when no JSON object is found."""
        assert _extract_json_object("no json here at all") is None

    def test_braces_in_strings(self) -> None:
        """Does not split on braces inside JSON string values."""
        text = '{"patches": [], "note": "use {item} syntax"}'
        data = _extract_json_object(text)
        assert data is not None
        assert data["note"] == "use {item} syntax"

    def test_empty_response(self) -> None:
        """Returns None for empty input."""
        assert _extract_json_object("") is None
        assert _extract_json_object("   ") is None


# ---------------------------------------------------------------------------
# Best practices tests
# ---------------------------------------------------------------------------


class TestBestPractices:
    """Tests for best practices mapping loading."""

    def test_load_best_practices(self) -> None:
        """Best practices YAML loads successfully."""
        bp = _load_best_practices()
        assert "universal" in bp
        assert "fqcn" in bp
        assert len(bp["universal"]) > 5

    def test_get_best_practices_for_fqcn(self) -> None:
        """Returns FQCN-specific practices for M001."""
        result = _get_best_practices_for_rules(["M001"])
        assert "FQCN" in result

    def test_get_best_practices_for_unknown_rule(self) -> None:
        """Returns universal practices for unknown rules."""
        result = _get_best_practices_for_rules(["UNKNOWN999"])
        assert "idempotent" in result.lower() or "YAML" in result

    def test_get_best_practices_for_multiple_rules(self) -> None:
        """Returns combined practices for multiple rule categories."""
        result = _get_best_practices_for_rules(["M001", "L011"])
        assert "FQCN" in result
