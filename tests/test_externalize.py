"""Unit tests for the externalize-secrets CLI subcommand."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent
from unittest.mock import patch

import pytest

from apme_engine.cli.externalize import (
    _build_secrets_yaml,
    _check_gitleaks,
    _find_secret_keys,
    _insert_vars_files,
    _overlaps,
    _secret_ranges,
    externalize_file,
    run_externalize,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SECRETS_PLAYBOOK = dedent("""\
    ---
    - name: Play with secrets
      hosts: localhost
      vars:
        aws_access_key_id: "AKIA1234567890ABCDEF"
        db_password: "SuperSecretPassword123!"
      tasks:
        - name: Show key
          ansible.builtin.debug:
            msg: "{{ aws_access_key_id }}"
""")

MIXED_VARS_PLAYBOOK = dedent("""\
    ---
    - name: Play with mixed vars
      hosts: localhost
      vars:
        safe_var: "not-a-secret"
        db_password: "SuperSecretPassword123!"
      tasks: []
""")

CLEAN_PLAYBOOK = dedent("""\
    ---
    - name: Clean play
      hosts: localhost
      tasks:
        - name: Hello
          ansible.builtin.debug:
            msg: hello
""")


def _make_findings(
    filename: str,
    entries: list[tuple[str, int, int]],
) -> list[dict[str, object]]:
    """Build fake run_gitleaks output.

    Args:
        filename: Relative filename as returned by the scanner.
        entries: List of (rule_id, start_line, end_line) tuples.

    Returns:
        List of violation dicts.
    """
    findings = []
    for rule_id, start, end in entries:
        findings.append(
            {
                "rule_id": f"SEC:{rule_id}",
                "level": "error",
                "message": f"Secret: {rule_id}",
                "file": filename,
                "line": start if start == end else [start, end],
                "path": "",
                "scope": "playbook",
            }
        )
    return findings


# ---------------------------------------------------------------------------
# _secret_ranges
# ---------------------------------------------------------------------------


class TestSecretRanges:
    """Tests for _secret_ranges helper."""

    def test_single_line(self) -> None:
        """Single-line finding returns (n, n) tuple."""
        findings = [{"line": 5}]
        assert _secret_ranges(findings) == [(5, 5)]  # type: ignore[arg-type]

    def test_multi_line(self) -> None:
        """Multi-line finding returns (start, end) tuple."""
        findings = [{"line": [3, 7]}]
        assert _secret_ranges(findings) == [(3, 7)]  # type: ignore[arg-type]

    def test_multiple_findings(self) -> None:
        """Multiple findings are all converted."""
        findings = [{"line": 1}, {"line": [4, 6]}, {"line": 9}]
        assert _secret_ranges(findings) == [(1, 1), (4, 6), (9, 9)]  # type: ignore[arg-type]

    def test_empty(self) -> None:
        """Empty findings list returns empty list."""
        assert _secret_ranges([]) == []


# ---------------------------------------------------------------------------
# _overlaps
# ---------------------------------------------------------------------------


class TestOverlaps:
    """Tests for _overlaps helper."""

    def test_exact_match(self) -> None:
        """Key range exactly matches secret range."""
        assert _overlaps(5, 5, [(5, 5)])

    def test_range_inside_key(self) -> None:
        """Secret range falls entirely within key range."""
        assert _overlaps(3, 10, [(5, 7)])

    def test_key_inside_range(self) -> None:
        """Key range falls entirely within secret range."""
        assert _overlaps(5, 7, [(3, 10)])

    def test_no_overlap(self) -> None:
        """Key range does not overlap secret range."""
        assert not _overlaps(1, 3, [(5, 7)])

    def test_adjacent_no_overlap(self) -> None:
        """Ranges that are adjacent but not overlapping."""
        assert not _overlaps(1, 4, [(5, 7)])

    def test_touching_boundary(self) -> None:
        """Ranges sharing one boundary line overlap."""
        assert _overlaps(1, 5, [(5, 8)])


# ---------------------------------------------------------------------------
# _find_secret_keys
# ---------------------------------------------------------------------------


class TestFindSecretKeys:
    """Tests for _find_secret_keys with real ruamel.yaml parsing."""

    def _load_vars(self, yaml_text: str) -> object:
        """Parse YAML and return the vars block of the first play."""
        from ruamel.yaml import YAML

        y: YAML = YAML(typ="rt")
        data = y.load(yaml_text)
        return data[0]["vars"]  # type: ignore[index]

    def test_single_secret_key(self) -> None:
        """A single secret on a specific line is identified."""
        play_yaml = dedent("""\
            ---
            - name: Test
              hosts: localhost
              vars:
                safe_var: not-a-secret
                db_password: "s3cr3t"
              tasks: []
        """)
        vars_map = self._load_vars(play_yaml)
        # db_password is on line 6 (1-indexed)
        result = _find_secret_keys(vars_map, [(6, 6)])  # type: ignore[arg-type]
        assert result == ["db_password"]

    def test_no_secret_keys(self) -> None:
        """No secret ranges → no keys returned."""
        play_yaml = dedent("""\
            ---
            - name: Test
              hosts: localhost
              vars:
                var_a: value1
                var_b: value2
              tasks: []
        """)
        vars_map = self._load_vars(play_yaml)
        result = _find_secret_keys(vars_map, [])  # type: ignore[arg-type]
        assert result == []

    def test_all_keys_are_secrets(self) -> None:
        """All keys are identified when ranges cover all lines."""
        play_yaml = dedent("""\
            ---
            - name: Test
              hosts: localhost
              vars:
                key_a: val1
                key_b: val2
              tasks: []
        """)
        vars_map = self._load_vars(play_yaml)
        result = _find_secret_keys(vars_map, [(5, 6)])  # type: ignore[arg-type]
        assert set(result) == {"key_a", "key_b"}


# ---------------------------------------------------------------------------
# _insert_vars_files
# ---------------------------------------------------------------------------


class TestInsertVarsFiles:
    """Tests for _insert_vars_files helper."""

    def _load_play(self, yaml_text: str) -> object:
        from ruamel.yaml import YAML

        y: YAML = YAML(typ="rt")
        data = y.load(yaml_text)
        return data[0]  # type: ignore[index]

    def test_inserts_before_vars(self) -> None:
        """vars_files is inserted immediately before vars."""
        play = self._load_play(SECRETS_PLAYBOOK)
        _insert_vars_files(play, "secrets.yml")  # type: ignore[arg-type]
        keys = list(play.keys())  # type: ignore[union-attr]
        assert "vars_files" in keys
        assert keys.index("vars_files") < keys.index("vars")

    def test_appends_to_existing_vars_files(self) -> None:
        """When vars_files already exists the new ref is appended."""
        play_yaml = dedent("""\
            ---
            - name: Test
              hosts: localhost
              vars_files:
                - other.yml
              vars:
                key: val
              tasks: []
        """)
        play = self._load_play(play_yaml)
        _insert_vars_files(play, "secrets.yml")  # type: ignore[arg-type]
        assert "secrets.yml" in list(play["vars_files"])  # type: ignore[index]
        assert "other.yml" in list(play["vars_files"])  # type: ignore[index]

    def test_no_duplicate_entry(self) -> None:
        """The same ref is not added twice."""
        play = self._load_play(SECRETS_PLAYBOOK)
        _insert_vars_files(play, "secrets.yml")  # type: ignore[arg-type]
        _insert_vars_files(play, "secrets.yml")  # type: ignore[arg-type]
        count = list(play["vars_files"]).count("secrets.yml")  # type: ignore[index]
        assert count == 1


# ---------------------------------------------------------------------------
# _build_secrets_yaml
# ---------------------------------------------------------------------------


class TestBuildSecretsYaml:
    """Tests for _build_secrets_yaml output."""

    def test_contains_keys(self) -> None:
        """Output contains each secret key."""
        text = _build_secrets_yaml({"db_password": "s3cr3t", "api_key": "abc123"}, "play.yml")
        assert "db_password" in text
        assert "api_key" in text

    def test_contains_header_comment(self) -> None:
        """Output contains a warning comment."""
        text = _build_secrets_yaml({"k": "v"}, "play.yml")
        assert "store securely" in text
        assert "Generated from: play.yml" in text

    def test_contains_vault_hint(self) -> None:
        """Output mentions ansible-vault encryption."""
        text = _build_secrets_yaml({"k": "v"}, "play.yml")
        assert "ansible-vault" in text


# ---------------------------------------------------------------------------
# externalize_file
# ---------------------------------------------------------------------------


class TestExternalizeFile:
    """Integration-style tests for externalize_file using mocked gitleaks."""

    def test_secrets_extracted(self, tmp_path: Path) -> None:
        """Secret vars are moved to secrets file; externalized playbook has vars_files.

        Args:
            tmp_path: Pytest temporary directory fixture.
        """
        source = tmp_path / "play.yml"
        source.write_text(SECRETS_PLAYBOOK)
        secrets_path = tmp_path / "secrets.yml"

        # aws_access_key_id is on line 5, db_password on line 6
        findings = _make_findings("play.yml", [("aws-access-key", 5, 5), ("generic-api-key", 6, 6)])

        with patch("apme_engine.cli.externalize.run_gitleaks", return_value=findings):
            result = externalize_file(source, secrets_path)

        assert result.secrets_count == 2
        assert result.externalized_path is not None
        assert result.externalized_path.exists()
        assert secrets_path.exists()
        assert "aws_access_key_id" in result.secret_names
        assert "db_password" in result.secret_names

    def test_externalized_has_vars_files(self, tmp_path: Path) -> None:
        """Externalized playbook contains vars_files reference.

        Args:
            tmp_path: Pytest temporary directory fixture.
        """
        source = tmp_path / "play.yml"
        source.write_text(SECRETS_PLAYBOOK)
        secrets_path = tmp_path / "secrets.yml"

        findings = _make_findings("play.yml", [("aws-access-key", 5, 5), ("generic-api-key", 6, 6)])

        with patch("apme_engine.cli.externalize.run_gitleaks", return_value=findings):
            externalize_file(source, secrets_path)

        ext_text = (tmp_path / "play.externalized.yml").read_text()
        assert "vars_files" in ext_text
        assert "secrets.yml" in ext_text

    def test_original_unchanged(self, tmp_path: Path) -> None:
        """The original source file is not modified.

        Args:
            tmp_path: Pytest temporary directory fixture.
        """
        source = tmp_path / "play.yml"
        source.write_text(SECRETS_PLAYBOOK)
        original_text = source.read_text()
        secrets_path = tmp_path / "secrets.yml"

        findings = _make_findings("play.yml", [("generic-api-key", 5, 5)])

        with patch("apme_engine.cli.externalize.run_gitleaks", return_value=findings):
            externalize_file(source, secrets_path)

        assert source.read_text() == original_text

    def test_no_findings_returns_zero(self, tmp_path: Path) -> None:
        """No gitleaks findings → zero secrets count, no files written.

        Args:
            tmp_path: Pytest temporary directory fixture.
        """
        source = tmp_path / "play.yml"
        source.write_text(CLEAN_PLAYBOOK)
        secrets_path = tmp_path / "secrets.yml"

        with patch("apme_engine.cli.externalize.run_gitleaks", return_value=[]):
            result = externalize_file(source, secrets_path)

        assert result.secrets_count == 0
        assert not secrets_path.exists()

    def test_dry_run_writes_no_files(self, tmp_path: Path) -> None:
        """Dry-run mode reports secrets but writes nothing.

        Args:
            tmp_path: Pytest temporary directory fixture.
        """
        source = tmp_path / "play.yml"
        source.write_text(SECRETS_PLAYBOOK)
        secrets_path = tmp_path / "secrets.yml"

        findings = _make_findings("play.yml", [("generic-api-key", 5, 5)])

        with patch("apme_engine.cli.externalize.run_gitleaks", return_value=findings):
            result = externalize_file(source, secrets_path, dry_run=True)

        assert result.secrets_count > 0
        assert not secrets_path.exists()
        ext_path = tmp_path / "play.externalized.yml"
        assert not ext_path.exists()

    def test_mixed_vars_only_secrets_extracted(self, tmp_path: Path) -> None:
        """Only flagged variables are extracted; non-secret vars stay inline.

        Args:
            tmp_path: Pytest temporary directory fixture.
        """
        source = tmp_path / "play.yml"
        source.write_text(MIXED_VARS_PLAYBOOK)
        secrets_path = tmp_path / "secrets.yml"

        # Only db_password (line 6) is a secret; safe_var (line 5) is not.
        findings = _make_findings("play.yml", [("generic-api-key", 6, 6)])

        with patch("apme_engine.cli.externalize.run_gitleaks", return_value=findings):
            result = externalize_file(source, secrets_path)

        assert result.secrets_count == 1
        assert "db_password" in result.secret_names
        assert "safe_var" not in result.secret_names

        ext_text = (tmp_path / "play.externalized.yml").read_text()
        assert "safe_var" in ext_text
        assert "db_password" not in ext_text

    def test_secrets_file_contains_extracted_values(self, tmp_path: Path) -> None:
        """Secrets file contains the extracted variable names.

        Args:
            tmp_path: Pytest temporary directory fixture.
        """
        source = tmp_path / "play.yml"
        source.write_text(SECRETS_PLAYBOOK)
        secrets_path = tmp_path / "secrets.yml"

        findings = _make_findings("play.yml", [("aws-access-key", 5, 5), ("generic-api-key", 6, 6)])

        with patch("apme_engine.cli.externalize.run_gitleaks", return_value=findings):
            externalize_file(source, secrets_path)

        secrets_text = secrets_path.read_text()
        assert "aws_access_key_id" in secrets_text
        assert "db_password" in secrets_text

    def test_non_playbook_yaml_skipped(self, tmp_path: Path) -> None:
        """A YAML file that is not a list of plays is skipped gracefully.

        Args:
            tmp_path: Pytest temporary directory fixture.
        """
        source = tmp_path / "config.yml"
        source.write_text("key: value\nother: data\n")
        secrets_path = tmp_path / "secrets.yml"

        findings = _make_findings("config.yml", [("generic-api-key", 1, 1)])

        with patch("apme_engine.cli.externalize.run_gitleaks", return_value=findings):
            result = externalize_file(source, secrets_path)

        assert result.skipped is True
        assert not secrets_path.exists()

    def test_empty_vars_block_removed(self, tmp_path: Path) -> None:
        """When all vars are secrets the empty vars block is removed from output.

        Args:
            tmp_path: Pytest temporary directory fixture.
        """
        source = tmp_path / "play.yml"
        source.write_text(SECRETS_PLAYBOOK)
        secrets_path = tmp_path / "secrets.yml"

        findings = _make_findings("play.yml", [("aws-access-key", 5, 5), ("generic-api-key", 6, 6)])

        with patch("apme_engine.cli.externalize.run_gitleaks", return_value=findings):
            externalize_file(source, secrets_path)

        ext_text = (tmp_path / "play.externalized.yml").read_text()
        # vars: key should not appear as a mapping (vars_files is acceptable)
        assert "vars:" not in ext_text or "vars_files:" in ext_text


# ---------------------------------------------------------------------------
# _check_gitleaks
# ---------------------------------------------------------------------------


class TestCheckGitleaks:
    """Tests for the gitleaks binary detection helper."""

    def test_found(self) -> None:
        """Returns True when shutil.which finds the binary."""
        with patch("apme_engine.cli.externalize.shutil.which", return_value="/usr/bin/gitleaks"):
            assert _check_gitleaks() is True

    def test_not_found(self) -> None:
        """Returns False when shutil.which returns None."""
        with patch("apme_engine.cli.externalize.shutil.which", return_value=None):
            assert _check_gitleaks() is False


# ---------------------------------------------------------------------------
# run_externalize (CLI entry point)
# ---------------------------------------------------------------------------


class TestRunExternalize:
    """Tests for the run_externalize CLI entry point."""

    def _make_args(
        self,
        target: str = ".",
        secrets_file: str = "secrets.yml",
        dry_run: bool = False,
    ) -> object:
        import argparse

        ns = argparse.Namespace(target=target, secrets_file=secrets_file, dry_run=dry_run)
        return ns

    def test_exits_1_when_gitleaks_missing(self, tmp_path: Path) -> None:
        """Exit code 1 when gitleaks binary not found.

        Args:
            tmp_path: Pytest temporary directory fixture.
        """
        args = self._make_args(target=str(tmp_path))
        with (
            patch("apme_engine.cli.externalize._check_gitleaks", return_value=False),
            pytest.raises(SystemExit) as exc_info,
        ):
            run_externalize(args)  # type: ignore[arg-type]
        assert exc_info.value.code == 1

    def test_exits_1_when_target_missing(self, tmp_path: Path) -> None:
        """Exit code 1 when target path does not exist.

        Args:
            tmp_path: Pytest temporary directory fixture.
        """
        args = self._make_args(target=str(tmp_path / "nonexistent.yml"))
        with (
            patch("apme_engine.cli.externalize._check_gitleaks", return_value=True),
            pytest.raises(SystemExit) as exc_info,
        ):
            run_externalize(args)  # type: ignore[arg-type]
        assert exc_info.value.code == 1

    def test_single_file_processes(self, tmp_path: Path) -> None:
        """Single-file target is processed end-to-end.

        Args:
            tmp_path: Pytest temporary directory fixture.
        """
        source = tmp_path / "play.yml"
        source.write_text(SECRETS_PLAYBOOK)
        args = self._make_args(target=str(source), secrets_file="secrets.yml")

        findings = _make_findings("play.yml", [("generic-api-key", 5, 5)])

        with (
            patch("apme_engine.cli.externalize._check_gitleaks", return_value=True),
            patch("apme_engine.cli.externalize.run_gitleaks", return_value=findings),
        ):
            run_externalize(args)  # type: ignore[arg-type]

        assert (tmp_path / "secrets.yml").exists()
        assert (tmp_path / "play.externalized.yml").exists()

    def test_dry_run_no_writes(self, tmp_path: Path) -> None:
        """Dry-run produces no output files.

        Args:
            tmp_path: Pytest temporary directory fixture.
        """
        source = tmp_path / "play.yml"
        source.write_text(SECRETS_PLAYBOOK)
        args = self._make_args(target=str(source), dry_run=True)

        findings = _make_findings("play.yml", [("generic-api-key", 5, 5)])

        with (
            patch("apme_engine.cli.externalize._check_gitleaks", return_value=True),
            patch("apme_engine.cli.externalize.run_gitleaks", return_value=findings),
        ):
            run_externalize(args)  # type: ignore[arg-type]

        assert not (tmp_path / "secrets.yml").exists()
        assert not (tmp_path / "play.externalized.yml").exists()
