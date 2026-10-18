from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.tracker_core import (
    TrackerError,
    TrackerPaths,
    add_problem,
    get_problem_dir_by_id,
    load_problem,
    record_attempt,
    update_problem,
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
                    "spaced": {"type": "fixed_days", "days": [1, 3, 7, 14, 30]}
                },
            }
        ),
        encoding="utf-8",
    )
    return TrackerPaths(root)


def test_safe_problem_creation_and_duplicate_id_rejected(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    folder = add_problem(
        paths,
        problem_id="LC-0100",
        title="Same Tree",
        difficulty="Easy",
        primary_topic="Trees",
        platform_name="LeetCode",
        platform_problem_id="100",
        platform_url="https://example.com",
        date_added="2026-01-01",
    )
    assert (folder / "problem.yaml").exists()

    with pytest.raises(TrackerError):
        add_problem(
            paths,
            problem_id="LC-0100",
            title="Same Tree Copy",
            difficulty="Easy",
            primary_topic="Trees",
            platform_name="LeetCode",
            platform_problem_id="100",
            platform_url="https://example.com",
            date_added="2026-01-01",
        )


def test_attempts_are_append_only_and_status_progression(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    add_problem(
        paths,
        problem_id="LC-0002",
        title="Add Two Numbers",
        difficulty="Medium",
        primary_topic="Linked List",
        platform_name="LeetCode",
        platform_problem_id="2",
        platform_url="https://example.com",
        date_added="2026-01-01",
    )
    record_attempt(
        paths,
        problem_id="LC-0002",
        attempted_at="2026-01-02T10:00:00Z",
        outcome="failed",
        approach_id="A1",
        language="python",
        assistance=["Hint"],
        assistance_details=None,
        submission_url=None,
        time_taken_minutes=20,
        mistakes="edge case",
        reflection="retry",
        independently_reproduced_after=False,
    )
    record_attempt(
        paths,
        problem_id="LC-0002",
        attempted_at="2026-01-03T10:00:00Z",
        outcome="solved",
        approach_id="A2",
        language="python",
        assistance=["Independent"],
        assistance_details=None,
        submission_url=None,
        time_taken_minutes=15,
        mistakes=None,
        reflection=None,
        independently_reproduced_after=True,
    )

    pdir = get_problem_dir_by_id(paths, "LC-0002")
    data = load_problem(pdir)
    assert len(data["attempts"]) == 2
    assert data["attempts"][0]["attempt_id"] == "ATT-0001"
    assert data["attempts"][1]["attempt_id"] == "ATT-0002"
    assert data["status"] == "independently solved"


def test_difficulty_change_moves_folder_safely(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    add_problem(
        paths,
        problem_id="LC-0300",
        title="LIS",
        difficulty="Easy",
        primary_topic="DP",
        platform_name="LeetCode",
        platform_problem_id="300",
        platform_url="https://example.com",
        date_added="2026-01-01",
    )
    old = get_problem_dir_by_id(paths, "LC-0300")
    assert old is not None

    new = update_problem(paths, "LC-0300", {"difficulty": "Medium"})
    assert "medium" in str(new)
    assert not old.exists()

    collision = paths.problems_root / "hard" / new.name
    collision.mkdir(parents=True)
    with pytest.raises(TrackerError):
        update_problem(paths, "LC-0300", {"difficulty": "Hard"})
