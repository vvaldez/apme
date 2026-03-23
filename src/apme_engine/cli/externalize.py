"""Externalize-secrets subcommand: extract hardcoded secrets to a separate vars file.

Detects secrets in Ansible YAML files using gitleaks, removes the affected variables
from the source playbook, inserts a ``vars_files:`` reference, and writes two output
files — neither of which is the original source.

Per ADR-034 this is a local-only operation; no gRPC or daemon connection is required.
"""

from __future__ import annotations

import argparse
import io
import shutil
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq

from apme_engine.validators.gitleaks.scanner import GITLEAKS_BIN, run_gitleaks


def _make_yaml() -> YAML:
    """Return a round-trip YAML instance that preserves comments and quoting."""
    y: YAML = YAML(typ="rt")
    y.preserve_quotes = True
    y.default_flow_style = False
    y.width = 4096
    return y


@dataclass
class ExternalizeResult:
    """Result of processing one source file."""

    secrets_count: int
    externalized_path: Path | None
    secrets_path: Path | None
    skipped: bool = False
    skip_reason: str = ""
    secret_names: list[str] = field(default_factory=list)


def _secret_ranges(findings: list[dict[str, str | int | list[int] | None]]) -> list[tuple[int, int]]:
    """Convert violation dicts to 1-indexed (start, end) line ranges.

    Args:
        findings: Violation dicts from ``run_gitleaks``.

    Returns:
        List of (start_line, end_line) tuples, both 1-indexed inclusive.
    """
    ranges: list[tuple[int, int]] = []
    for f in findings:
        line = f.get("line")
        if isinstance(line, list) and len(line) == 2:
            ranges.append((int(line[0]), int(line[1])))
        elif isinstance(line, int):
            ranges.append((line, line))
    return ranges


def _overlaps(key_start: int, key_end: int, ranges: list[tuple[int, int]]) -> bool:
    """Return True if any range overlaps [key_start, key_end].

    Args:
        key_start: First line of this key's span (1-indexed, inclusive).
        key_end: Last line of this key's span (1-indexed, inclusive).
        ranges: List of (start, end) secret line ranges.

    Returns:
        True when at least one range intersects the key span.
    """
    return any(s <= key_end and e >= key_start for s, e in ranges)


def _find_secret_keys(vars_map: CommentedMap, ranges: list[tuple[int, int]]) -> list[str]:
    """Identify which keys in *vars_map* fall on or contain a secret line.

    Uses ruamel.yaml line-column metadata to determine each key's span:
    from its own line to one line before the next key (or +100 for the last
    key, covering any multi-line block value).

    Args:
        vars_map: The ``vars:`` CommentedMap from a play.
        ranges: Secret line ranges from ``_secret_ranges``.

    Returns:
        List of variable names whose values were flagged as secrets.
    """
    keys: list[str] = [str(k) for k in vars_map]
    secret_keys: list[str] = []

    for i, key in enumerate(keys):
        try:
            key_line = vars_map.lc.key(key)[0] + 1  # 0-indexed → 1-indexed
        except (KeyError, TypeError):
            continue

        if i + 1 < len(keys):
            next_key_line = vars_map.lc.key(keys[i + 1])[0] + 1
            key_end = next_key_line - 1
        else:
            key_end = key_line + 100  # generous upper bound for multi-line values

        if _overlaps(key_line, key_end, ranges):
            secret_keys.append(key)

    return secret_keys


def _insert_vars_files(play: CommentedMap, secrets_ref: str) -> None:
    """Insert ``vars_files: [secrets_ref]`` immediately before ``vars:`` in *play*.

    If ``vars_files`` already exists the reference is appended (deduplicated).
    If ``vars:`` is not present the key is appended at the end.

    Args:
        play: A single play CommentedMap.
        secrets_ref: Filename or relative path to add as a vars_files entry.
    """
    if "vars_files" in play:
        vf = play["vars_files"]
        if isinstance(vf, (list, CommentedSeq)) and secrets_ref not in list(vf):
            vf.append(secrets_ref)
        return

    keys: list[str] = [str(k) for k in play]
    if "vars" in keys:
        idx = keys.index("vars")
        play.insert(idx, "vars_files", [secrets_ref])
    else:
        play["vars_files"] = [secrets_ref]


def _build_secrets_yaml(secrets: dict[str, object], source_name: str) -> str:
    """Render *secrets* as a YAML string with a header comment.

    Args:
        secrets: Variable name → value mapping to write.
        source_name: Base filename of the source playbook (for the comment).

    Returns:
        YAML text ready to write to the secrets file.
    """
    y = _make_yaml()
    data: CommentedMap = CommentedMap(secrets)
    data.yaml_set_start_comment(
        f"Externalized secrets — store securely, do not commit to version control\n"
        f"# Generated from: {source_name}\n"
        f"# Consider encrypting this file with: ansible-vault encrypt secrets.yml"
    )
    buf = io.StringIO()
    y.dump(data, buf)
    return buf.getvalue()


def externalize_file(
    source: Path,
    secrets_path: Path,
    *,
    dry_run: bool = False,
) -> ExternalizeResult:
    """Process *source*, extract secrets, and write output files.

    The original file is never modified.  Two files are written:

    - ``<source.stem>.externalized<source.suffix>`` — playbook with secret vars
      removed and ``vars_files:`` added.
    - *secrets_path* — extracted secret key-value pairs.

    Args:
        source: Path to the Ansible YAML file to process.
        secrets_path: Destination path for the extracted secrets file.
        dry_run: When True, no files are written; only a report is printed.

    Returns:
        ExternalizeResult describing what was (or would be) done.
    """
    # Run gitleaks on a copy of the file in a temp directory.
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_file = Path(tmpdir) / source.name
        shutil.copy2(source, tmp_file)
        findings = run_gitleaks(tmpdir)

    if not findings:
        return ExternalizeResult(0, None, None)

    ranges = _secret_ranges(findings)

    y = _make_yaml()
    try:
        text = source.read_text()
        data: object = y.load(text)
    except Exception as exc:  # noqa: BLE001
        return ExternalizeResult(0, None, None, skipped=True, skip_reason=f"YAML parse error: {exc}")

    if not isinstance(data, list):
        return ExternalizeResult(0, None, None, skipped=True, skip_reason="not a playbook (expected list of plays)")

    all_secrets: dict[str, object] = {}
    secrets_ref = secrets_path.name

    for play in data:
        if not isinstance(play, CommentedMap):
            continue
        if "vars" not in play:
            continue

        vars_map = play["vars"]
        if not isinstance(vars_map, CommentedMap):
            continue

        secret_keys = _find_secret_keys(vars_map, ranges)
        if not secret_keys:
            continue

        for key in secret_keys:
            all_secrets[key] = vars_map[key]
            del vars_map[key]

        _insert_vars_files(play, secrets_ref)

        if not vars_map:
            del play["vars"]

    if not all_secrets:
        return ExternalizeResult(0, None, None)

    output_path = source.parent / f"{source.stem}.externalized{source.suffix}"

    if dry_run:
        sys.stdout.write(f"  Would write: {output_path}\n")
        sys.stdout.write(f"  Would write: {secrets_path}\n")
        sys.stdout.write(f"  Secrets: {', '.join(all_secrets)}\n")
        return ExternalizeResult(
            len(all_secrets),
            output_path,
            secrets_path,
            secret_names=list(all_secrets),
        )

    buf = io.StringIO()
    y.dump(data, buf)
    output_path.write_text(buf.getvalue())

    secrets_text = _build_secrets_yaml(all_secrets, source.name)
    if secrets_path.exists():
        sys.stderr.write(f"WARNING: {secrets_path} already exists — overwriting.\n")
    secrets_path.write_text(secrets_text)

    return ExternalizeResult(
        len(all_secrets),
        output_path,
        secrets_path,
        secret_names=list(all_secrets),
    )


def _check_gitleaks() -> bool:
    """Return True if the gitleaks binary is reachable.

    Returns:
        True when ``gitleaks`` is found on PATH, False otherwise.
    """
    return shutil.which(GITLEAKS_BIN) is not None


def run_externalize(args: argparse.Namespace) -> None:
    """Execute the ``externalize-secrets`` subcommand.

    Args:
        args: Parsed CLI arguments (``target``, ``secrets_file``, ``dry_run``).
    """
    if not _check_gitleaks():
        sys.stderr.write(
            "Error: gitleaks binary not found — install gitleaks to use this command.\n"
            "  https://github.com/gitleaks/gitleaks#installing\n"
        )
        sys.exit(1)

    target = Path(getattr(args, "target", ".")).resolve()
    if not target.exists():
        sys.stderr.write(f"Error: target not found: {args.target}\n")
        sys.exit(1)

    secrets_file_arg: str = getattr(args, "secrets_file", "secrets.yml") or "secrets.yml"
    dry_run: bool = bool(getattr(args, "dry_run", False))

    if target.is_file():
        files = [target]
    else:
        yml = sorted(target.rglob("*.yml"))
        yaml = sorted(target.rglob("*.yaml"))
        files = yml + yaml

    if not files:
        sys.stderr.write(f"No YAML files found under {target}\n")
        sys.exit(0)

    total_secrets = 0
    total_written = 0

    for source in files:
        secrets_path = (
            Path(secrets_file_arg) if Path(secrets_file_arg).is_absolute() else source.parent / secrets_file_arg
        )

        result = externalize_file(source, secrets_path, dry_run=dry_run)

        if result.skipped:
            sys.stderr.write(f"Skipped {source}: {result.skip_reason}\n")
            continue

        if result.secrets_count == 0:
            if len(files) == 1:
                sys.stderr.write("No secrets detected.\n")
            continue

        total_secrets += result.secrets_count

        if dry_run:
            sys.stderr.write(
                f"[dry-run] {source}: {result.secrets_count} secret(s) would be externalized"
                f" ({', '.join(result.secret_names)})\n"
            )
        else:
            total_written += 2
            sys.stderr.write(f"{source}:\n")
            sys.stderr.write(f"  → {result.externalized_path}\n")
            sys.stderr.write(f"  → {result.secrets_path}\n")
            sys.stderr.write(f"  {result.secrets_count} secret(s) externalized: {', '.join(result.secret_names)}\n")

    if total_secrets == 0:
        if len(files) > 1:
            sys.stderr.write("No secrets detected in any file.\n")
    elif dry_run:
        sys.stderr.write(f"\n[dry-run] {total_secrets} secret(s) total would be externalized.\n")
    else:
        sys.stderr.write(f"\n{total_secrets} secret(s) externalized, {total_written} file(s) written.\n")
