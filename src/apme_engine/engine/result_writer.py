"""Disk I/O helpers for saving ARI scan artifacts (trees, contexts, definitions, rule results)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

import jsonpickle

from .findings import Findings
from .models import YAMLDict

if TYPE_CHECKING:
    from .models import AnsibleRunContext, ObjectList, TaskCallsInTree


def save_trees(root_def_dir: str, trees: list[ObjectList], silent: bool = False) -> None:
    """Serialize and write call trees to tree.json.

    Args:
        root_def_dir: Root definitions directory.
        trees: Object lists (call trees) to serialize.
        silent: Suppress log output.
    """
    from . import logger

    tree_rel_file = os.path.join(root_def_dir, "tree.json")
    if tree_rel_file != "":
        lines = []
        for t_obj_list in trees:
            lines.append(t_obj_list.to_one_line_json())
        Path(tree_rel_file).write_text("\n".join(lines))
        if not silent:
            logger.info("  tree file saved")


def save_tasks_in_trees(root_def_dir: str, taskcalls_in_trees: list[TaskCallsInTree]) -> None:
    """Serialize and write task calls per tree to tasks_in_trees.json.

    Args:
        root_def_dir: Root definitions directory.
        taskcalls_in_trees: List of TaskCallsInTree to serialize.
    """
    tasks_in_t_path = os.path.join(root_def_dir, "tasks_in_trees.json")
    tasks_in_t_lines = []
    for d in taskcalls_in_trees:
        line = jsonpickle.encode(d, make_refs=False)
        tasks_in_t_lines.append(line)
    Path(tasks_in_t_path).write_text("\n".join(tasks_in_t_lines))


def save_contexts(root_def_dir: str, contexts: list[AnsibleRunContext]) -> None:
    """Serialize and write analysis contexts to contexts_with_analysis.json.

    Args:
        root_def_dir: Root definitions directory.
        contexts: AnsibleRunContext list to serialize.
    """
    contexts_a_path = os.path.join(root_def_dir, "contexts_with_analysis.json")
    conetxts_a_lines = []
    for d in contexts:
        line = jsonpickle.encode(d, make_refs=False)
        conetxts_a_lines.append(line)
    Path(contexts_a_path).write_text("\n".join(conetxts_a_lines))


def save_rule_result(findings: Findings, out_dir: str) -> None:
    """Save rule result JSON to out_dir.

    Args:
        findings: Findings containing rule results.
        out_dir: Output directory path.

    Raises:
        ValueError: If out_dir is empty.
    """
    if out_dir == "":
        raise ValueError("output dir must be a non-empty value")

    if not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    findings.save_rule_result(fpath=os.path.join(out_dir, "rule_result.json"))


def save_definitions(definitions: dict[str, object], out_dir: str) -> None:
    """Save definition objects to objects.json in out_dir.

    Args:
        definitions: Dict with definitions key containing serializable objects.
        out_dir: Output directory path.

    Raises:
        ValueError: If out_dir is empty.
    """
    if out_dir == "":
        raise ValueError("output dir must be a non-empty value")

    if not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    objects_json_str = jsonpickle.encode(definitions["definitions"], make_refs=False)
    fpath = os.path.join(out_dir, "objects.json")
    with open(fpath, "w") as file:
        file.write(objects_json_str)


def get_root_def_dir(path_mappings: YAMLDict) -> str:
    """Extract root definitions directory from path mappings.

    Args:
        path_mappings: Path mappings dict from SingleScan.

    Returns:
        Root definitions directory string, or empty string if not set.
    """
    root_def_dir_val = path_mappings.get("root_definitions")
    return str(root_def_dir_val) if isinstance(root_def_dir_val, str) else ""
