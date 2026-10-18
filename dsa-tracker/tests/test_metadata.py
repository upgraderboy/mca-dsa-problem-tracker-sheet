from __future__ import annotations

import json
from pathlib import Path

from scripts.tracker_core import TrackerPaths, validate_all_metadata


def _init_tracker(tmp_path: Path) -> TrackerPaths:
    root = tmp_path
    (root / "problems" / "easy").mkdir(parents=True)
    (root / "problems" / "medium").mkdir(parents=True)
    (root / "problems" / "hard").mkdir(parents=True)
    (root / "dashboards").mkdir(parents=True)
    (root / "config").mkdir(parents=True)
    (root / "config" / "revision-policy.json").write_text(
        json.dumps(
            {
                "default_policy": "spaced",
                "named_policies": {
                    "spaced": {"type": "fixed_days", "days": [1, 3, 7, 14, 30]},
                    "monthly": {"type": "monthly", "months": 1},
                },
            }
        ),
        encoding="utf-8",
    )
    return TrackerPaths(root)


def _problem_yaml(valid: bool = True) -> str:
    if valid:
        return """
problem_id: LC-0001
title: Two Sum
platforms:
  - name: LeetCode
    problem_id: "1"
    url: https://leetcode.com/problems/two-sum/
difficulty: Easy
status: not started
primary_topic: Arrays
date_added: 2026-10-18
approaches:
  - approach_id: A1
    name: Brute Force
    complexity: {time: {worst: O(n^2)}, auxiliary_space: O(1), overall_space: O(1)}
solution_files:
  - solutions/python/a.py
languages_used: [python]
attempts: []
revisions: []
"""
    return """
problem_id: LC-0001
title: Two Sum
platforms: []
difficulty: Invalid
status: bad
primary_topic: Arrays
date_added: 18-10-2026
approaches: []
solution_files:
  - solutions/python/missing.py
attempts:
  - attempt_id: ATT-0001
    attempted_at: bad-date
    assistance: [Unknown]
revisions:
  - revision_date: 2026-01-01
    recall_outcome: Unknown
"""


def test_valid_metadata_passes(tmp_path: Path) -> None:
    paths = _init_tracker(tmp_path)
    pdir = paths.problems_root / "easy" / "LC-0001-two-sum"
    (pdir / "solutions" / "python").mkdir(parents=True)
    (pdir / "solutions" / "python" / "a.py").write_text("pass\n", encoding="utf-8")
    (pdir / "problem.yaml").write_text(_problem_yaml(valid=True), encoding="utf-8")

    assert validate_all_metadata(paths) == []


def test_invalid_metadata_and_broken_solution_reference(tmp_path: Path) -> None:
    paths = _init_tracker(tmp_path)
    pdir = paths.problems_root / "easy" / "LC-0001-two-sum"
    pdir.mkdir(parents=True)
    (pdir / "problem.yaml").write_text(_problem_yaml(valid=False), encoding="utf-8")

    errors = validate_all_metadata(paths)
    joined = "\n".join(errors)
    assert "difficulty must be one of Easy/Medium/Hard" in joined
    assert "status has invalid value" in joined
    assert "Broken solution reference" in joined


def test_duplicate_problem_ids_detected(tmp_path: Path) -> None:
    paths = _init_tracker(tmp_path)
    p1 = paths.problems_root / "easy" / "LC-0001-a"
    p2 = paths.problems_root / "medium" / "LC-0001-b"
    p1.mkdir(parents=True)
    p2.mkdir(parents=True)
    content = _problem_yaml(valid=True)
    (p1 / "problem.yaml").write_text(content, encoding="utf-8")
    (p2 / "problem.yaml").write_text(content.replace("Easy", "Medium", 1), encoding="utf-8")

    errors = validate_all_metadata(paths)
    assert any("Duplicate problem_id LC-0001" in e for e in errors)
