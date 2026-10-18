from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any

from .tracker_core import (
    TrackerError,
    TrackerPaths,
    add_problem,
    generate_dashboards,
    get_problem_dir_by_id,
    list_due_revisions,
    list_problems,
    load_problem,
    record_attempt,
    record_revision,
    tracker_statistics,
    update_problem,
    validate_all_metadata,
)


def _paths() -> TrackerPaths:
    return TrackerPaths(Path(__file__).resolve().parents[1])


def cmd_add_problem(args: argparse.Namespace) -> None:
    p = _paths()
    if args.interactive:
        problem_id = input("Problem ID (e.g. LC-0121): ").strip()
        title = input("Title: ").strip()
        difficulty = input("Difficulty [Easy/Medium/Hard]: ").strip()
        primary_topic = input("Primary topic: ").strip()
        platform_name = input("Platform name: ").strip()
        platform_problem_id = input("Platform problem ID: ").strip()
        platform_url = input("Platform URL: ").strip()
        date_added = input("Date added [YYYY-MM-DD]: ").strip() or date.today().isoformat()
    else:
        problem_id = args.problem_id
        title = args.title
        difficulty = args.difficulty
        primary_topic = args.primary_topic
        platform_name = args.platform_name
        platform_problem_id = args.platform_problem_id
        platform_url = args.platform_url
        date_added = args.date_added or date.today().isoformat()
    path = add_problem(
        p,
        problem_id=problem_id,
        title=title,
        difficulty=difficulty,
        primary_topic=primary_topic,
        platform_name=platform_name,
        platform_problem_id=platform_problem_id,
        platform_url=platform_url,
        date_added=date_added,
    )
    print(f"Created problem at {path}")


def cmd_view_problem(args: argparse.Namespace) -> None:
    p = _paths()
    problem_dir = get_problem_dir_by_id(p, args.problem_id)
    if not problem_dir:
        raise TrackerError(f"Problem not found: {args.problem_id}")
    print(json.dumps(load_problem(problem_dir), indent=2, default=str))


def _parse_update_pairs(pairs: list[str]) -> dict[str, Any]:
    updates: dict[str, Any] = {}
    for pair in pairs:
        if "=" not in pair:
            raise TrackerError(f"Invalid update pair '{pair}', expected key=value")
        key, value = pair.split("=", 1)
        updates[key] = None if value == "null" else value
    return updates


def cmd_update_problem(args: argparse.Namespace) -> None:
    p = _paths()
    updates = _parse_update_pairs(args.set)
    target = update_problem(p, args.problem_id, updates)
    print(f"Updated problem in {target}")


def cmd_record_attempt(args: argparse.Namespace) -> None:
    p = _paths()
    assistance = [x.strip() for x in args.assistance.split(",") if x.strip()]
    attempt = record_attempt(
        p,
        problem_id=args.problem_id,
        attempted_at=args.attempted_at,
        outcome=args.outcome,
        approach_id=args.approach_id,
        language=args.language,
        assistance=assistance,
        assistance_details=args.assistance_details,
        submission_url=args.submission_url,
        time_taken_minutes=args.time_taken_minutes,
        mistakes=args.mistakes,
        reflection=args.reflection,
        independently_reproduced_after=args.independently_reproduced_after,
    )
    print(json.dumps(attempt, indent=2))


def cmd_revise_problem(args: argparse.Namespace) -> None:
    p = _paths()
    revision = record_revision(
        p,
        problem_id=args.problem_id,
        revision_date_str=args.revision_date,
        recall_outcome=args.recall_outcome,
        solved_without_assistance=args.solved_without_assistance,
        explained_complexity=args.explained_complexity,
        time_taken_minutes=args.time_taken_minutes,
        mistakes=args.mistakes,
        policy_name=args.policy,
        manual_interval_days=args.manual_interval_days,
        manual_next_date=args.manual_next_date,
    )
    print(json.dumps(revision, indent=2))


def cmd_list_due(args: argparse.Namespace) -> None:
    p = _paths()
    rows = list_due_revisions(
        p,
        as_of_date=args.as_of or date.today().isoformat(),
        overdue_only=args.overdue,
    )
    print(json.dumps(rows, indent=2))


def cmd_list_problems(args: argparse.Namespace) -> None:
    p = _paths()
    rows = list_problems(
        p,
        topic=args.topic,
        difficulty=args.difficulty,
        platform=args.platform,
        status=args.status,
    )
    print(json.dumps(rows, indent=2))


def cmd_generate_dashboards(args: argparse.Namespace) -> None:
    p = _paths()
    generate_dashboards(p, as_of_date=args.as_of)
    print("Dashboards generated")


def cmd_validate_metadata(_: argparse.Namespace) -> None:
    p = _paths()
    errors = validate_all_metadata(p)
    if errors:
        for err in errors:
            print(err)
        raise SystemExit(1)
    print("All metadata valid")


def cmd_stats(_: argparse.Namespace) -> None:
    print(json.dumps(tracker_statistics(_paths()), indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="DSA Tracker CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    add = sub.add_parser("add-problem", help="Add a new problem")
    add.add_argument("--interactive", action="store_true")
    add.add_argument("--problem-id")
    add.add_argument("--title")
    add.add_argument("--difficulty")
    add.add_argument("--primary-topic")
    add.add_argument("--platform-name")
    add.add_argument("--platform-problem-id")
    add.add_argument("--platform-url")
    add.add_argument("--date-added")
    add.set_defaults(func=cmd_add_problem)

    view = sub.add_parser("view-problem", help="View problem by ID")
    view.add_argument("problem_id")
    view.set_defaults(func=cmd_view_problem)

    upd = sub.add_parser("update-problem", help="Update problem metadata")
    upd.add_argument("problem_id")
    upd.add_argument("--set", nargs="+", required=True, help="key=value pairs")
    upd.set_defaults(func=cmd_update_problem)

    att = sub.add_parser("record-attempt", help="Record attempt")
    att.add_argument("problem_id")
    att.add_argument("--attempted-at", required=True)
    att.add_argument("--outcome", required=True)
    att.add_argument("--approach-id")
    att.add_argument("--language")
    att.add_argument("--assistance", default="Independent")
    att.add_argument("--assistance-details")
    att.add_argument("--submission-url")
    att.add_argument("--time-taken-minutes", type=int)
    att.add_argument("--mistakes")
    att.add_argument("--reflection")
    att.add_argument("--independently-reproduced-after", action="store_true")
    att.set_defaults(func=cmd_record_attempt)

    rev = sub.add_parser("revise-problem", help="Record revision")
    rev.add_argument("problem_id")
    rev.add_argument("--revision-date", required=True)
    rev.add_argument("--recall-outcome", required=True)
    rev.add_argument("--solved-without-assistance", action="store_true")
    rev.add_argument("--explained-complexity", action="store_true")
    rev.add_argument("--time-taken-minutes", type=int)
    rev.add_argument("--mistakes")
    rev.add_argument("--policy")
    rev.add_argument("--manual-interval-days", type=int)
    rev.add_argument("--manual-next-date")
    rev.set_defaults(func=cmd_revise_problem)

    due = sub.add_parser("list-due-revisions", help="List due revisions")
    due.add_argument("--as-of")
    due.add_argument("--overdue", action="store_true")
    due.set_defaults(func=cmd_list_due)

    lsp = sub.add_parser("list-problems", help="List problems with filters")
    lsp.add_argument("--topic")
    lsp.add_argument("--difficulty")
    lsp.add_argument("--platform")
    lsp.add_argument("--status")
    lsp.set_defaults(func=cmd_list_problems)

    gd = sub.add_parser("generate-dashboards", help="Generate markdown dashboards")
    gd.add_argument("--as-of")
    gd.set_defaults(func=cmd_generate_dashboards)

    vm = sub.add_parser("validate-metadata", help="Validate all problem metadata")
    vm.set_defaults(func=cmd_validate_metadata)

    st = sub.add_parser("stats", help="Show tracker statistics")
    st.set_defaults(func=cmd_stats)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.func(args)
    except TrackerError as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
