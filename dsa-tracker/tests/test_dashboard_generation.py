from __future__ import annotations

import json
from pathlib import Path

from scripts.tracker_core import TrackerPaths, add_problem, generate_dashboards, record_attempt


def _paths(tmp_path: Path) -> TrackerPaths:
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
                    "spaced": {"type": "fixed_days", "days": [1, 3, 7, 14, 30]}
                },
            }
        ),
        encoding="utf-8",
    )
    return TrackerPaths(root)


def test_dashboard_counts_links_and_determinism(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    add_problem(
        paths,
        problem_id="LC-0001",
        title="Two Sum",
        difficulty="Easy",
        primary_topic="Arrays",
        platform_name="LeetCode",
        platform_problem_id="1",
        platform_url="https://leetcode.com/problems/two-sum/",
        date_added="2026-01-01",
    )
    record_attempt(
        paths,
        problem_id="LC-0001",
        attempted_at="2026-01-02T10:00:00Z",
        outcome="solved",
        approach_id=None,
        language="python",
        assistance=["Independent"],
        assistance_details=None,
        submission_url=None,
        time_taken_minutes=10,
        mistakes=None,
        reflection=None,
        independently_reproduced_after=True,
    )

    generate_dashboards(paths, as_of_date="2026-01-05")
    first = (paths.dashboards_root / "all-problems.md").read_text(encoding="utf-8")

    assert "Unique problems: **1**" in first
    assert "problems/easy/LC-0001-two-sum" in first

    generate_dashboards(paths, as_of_date="2026-01-05")
    second = (paths.dashboards_root / "all-problems.md").read_text(encoding="utf-8")
    assert first == second
