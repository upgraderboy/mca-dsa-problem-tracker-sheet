from __future__ import annotations

import json
from pathlib import Path

from scripts.tracker_core import (
    TrackerPaths,
    add_problem,
    compute_next_revision_date,
    list_due_revisions,
    record_revision,
)


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
                    "spaced": {"type": "fixed_days", "days": [1, 3, 7, 14, 30]},
                    "monthly": {"type": "monthly", "months": 1},
                },
            }
        ),
        encoding="utf-8",
    )
    return TrackerPaths(root)


def test_spaced_and_manual_intervals() -> None:
    cfg = {
        "named_policies": {
            "spaced": {"type": "fixed_days", "days": [1, 3, 7, 14, 30]},
            "monthly": {"type": "monthly", "months": 1},
        }
    }
    from datetime import date

    assert (
        compute_next_revision_date(date(2026, 1, 1), "Easy recall", "spaced", 0, cfg)
        == "2026-01-04"
    )
    assert (
        compute_next_revision_date(date(2026, 1, 1), "Could not solve", "spaced", 3, cfg)
        == "2026-01-02"
    )
    assert (
        compute_next_revision_date(
            date(2026, 1, 1),
            "Easy recall",
            "spaced",
            1,
            cfg,
            manual_interval_days=5,
        )
        == "2026-01-06"
    )


def test_month_end_and_leap_year_handling() -> None:
    cfg = {"named_policies": {"monthly": {"type": "monthly", "months": 1}}}
    from datetime import date

    assert (
        compute_next_revision_date(date(2024, 1, 31), "Easy recall", "monthly", 0, cfg)
        == "2024-02-29"
    )


def test_due_and_overdue_classification(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    add_problem(
        paths,
        problem_id="LC-0200",
        title="X",
        difficulty="Easy",
        primary_topic="Arrays",
        platform_name="LeetCode",
        platform_problem_id="200",
        platform_url="https://example.com",
        date_added="2026-01-01",
    )
    record_revision(
        paths,
        problem_id="LC-0200",
        revision_date_str="2026-01-01",
        recall_outcome="Easy recall",
        solved_without_assistance=True,
        explained_complexity=True,
        time_taken_minutes=5,
        mistakes=None,
        policy_name="spaced",
        manual_interval_days=None,
        manual_next_date=None,
    )

    due = list_due_revisions(paths, "2026-01-10", overdue_only=False)
    overdue = list_due_revisions(paths, "2026-01-10", overdue_only=True)
    assert len(due) == 1
    assert len(overdue) == 1
