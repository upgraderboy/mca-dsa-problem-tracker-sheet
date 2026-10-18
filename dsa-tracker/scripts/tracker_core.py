from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

VALID_DIFFICULTIES = {"Easy", "Medium", "Hard"}
VALID_STATUSES = {
    "not started",
    "attempted",
    "solved with help",
    "independently solved",
    "mastered",
}
ASSISTANCE_CATEGORIES = {
    "Independent",
    "Hint",
    "Tutor",
    "AI",
    "Editorial",
    "Existing solution",
    "Other",
}
REVISION_OUTCOMES = {
    "Easy recall",
    "Correct with minor hints",
    "Needed substantial help",
    "Could not solve",
    "Could solve but could not explain",
}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
DATETIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?(Z|[+-]\d{2}:\d{2})$")


class TrackerError(Exception):
    pass


@dataclass(frozen=True)
class TrackerPaths:
    root: Path

    @property
    def problems_root(self) -> Path:
        return self.root / "problems"

    @property
    def dashboards_root(self) -> Path:
        return self.root / "dashboards"

    @property
    def revision_policy_path(self) -> Path:
        return self.root / "config" / "revision-policy.json"


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise TrackerError(f"Missing YAML file: {path}")
    content = yaml.safe_load(path.read_text(encoding="utf-8"))
    if content is None:
        return {}
    if not isinstance(content, dict):
        raise TrackerError(f"Expected mapping in YAML file: {path}")
    return content


def dump_yaml(path: Path, data: dict[str, Any]) -> None:
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")


def parse_date(value: str) -> date:
    if not DATE_RE.match(value):
        raise TrackerError(f"Invalid date format: {value}. Use YYYY-MM-DD")
    return date.fromisoformat(value)


def _is_valid_optional_date(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, date):
        return True
    if not isinstance(value, str) or not DATE_RE.match(value):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _is_valid_optional_datetime(value: Any) -> bool:
    if value is None:
        return True
    if not isinstance(value, str) or not DATETIME_RE.match(value):
        return False
    normalized = value.replace("Z", "+00:00")
    try:
        datetime.fromisoformat(normalized)
    except ValueError:
        return False
    return True


def slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug or "untitled"


def difficulty_dir_name(difficulty: str) -> str:
    return difficulty.lower()


def list_problem_dirs(paths: TrackerPaths) -> list[Path]:
    result: list[Path] = []
    for difficulty in ("easy", "medium", "hard"):
        base = paths.problems_root / difficulty
        if not base.exists():
            continue
        for child in sorted(base.iterdir()):
            if child.is_dir() and (child / "problem.yaml").exists():
                result.append(child)
    return result


def load_problem(problem_dir: Path) -> dict[str, Any]:
    data = load_yaml(problem_dir / "problem.yaml")
    data.setdefault("attempts", [])
    data.setdefault("revisions", [])
    data.setdefault("approaches", [])
    data.setdefault("solution_files", [])
    data.setdefault("languages_used", [])
    data.setdefault("topic_tags", [])
    data.setdefault("patterns", [])
    data.setdefault("related_problem_ids", [])
    data.setdefault("key_insights", [])
    return data


def get_problem_dir_by_id(paths: TrackerPaths, problem_id: str) -> Path | None:
    for d in list_problem_dirs(paths):
        data = load_problem(d)
        if data.get("problem_id") == problem_id:
            return d
    return None


def validate_problem_data(data: dict[str, Any], problem_dir: Path | None = None) -> list[str]:
    errors: list[str] = []

    for required in [
        "problem_id",
        "title",
        "platforms",
        "difficulty",
        "status",
        "date_added",
        "primary_topic",
        "approaches",
    ]:
        if required not in data:
            errors.append(f"Missing required field: {required}")

    if data.get("difficulty") not in VALID_DIFFICULTIES:
        errors.append("difficulty must be one of Easy/Medium/Hard")
    if data.get("status") not in VALID_STATUSES:
        errors.append("status has invalid value")

    if not _is_valid_optional_date(data.get("date_added")):
        errors.append("date_added must be YYYY-MM-DD")
    for field in ["first_attempted_date", "first_solved_date", "last_attempted_date"]:
        if field in data and not _is_valid_optional_date(data.get(field)):
            errors.append(f"{field} must be YYYY-MM-DD or null")

    platforms = data.get("platforms", [])
    if not isinstance(platforms, list) or not platforms:
        errors.append("platforms must be a non-empty list")
    else:
        for i, item in enumerate(platforms):
            if not isinstance(item, dict):
                errors.append(f"platforms[{i}] must be an object")
                continue
            for key in ["name", "problem_id", "url"]:
                if key not in item or not item.get(key):
                    errors.append(f"platforms[{i}] missing {key}")

    approaches = data.get("approaches", [])
    if not isinstance(approaches, list):
        errors.append("approaches must be a list")
    else:
        seen_approach_ids: set[str] = set()
        for i, ap in enumerate(approaches):
            if not isinstance(ap, dict):
                errors.append(f"approaches[{i}] must be an object")
                continue
            ap_id = ap.get("approach_id")
            if not ap_id:
                errors.append(f"approaches[{i}] missing approach_id")
            elif ap_id in seen_approach_ids:
                errors.append(f"Duplicate approach_id: {ap_id}")
            else:
                seen_approach_ids.add(ap_id)
            if not ap.get("name"):
                errors.append(f"approaches[{i}] missing name")
            complexity = ap.get("complexity")
            if not isinstance(complexity, dict):
                errors.append(f"approaches[{i}] missing complexity object")

    attempts = data.get("attempts", [])
    if not isinstance(attempts, list):
        errors.append("attempts must be a list")
    else:
        for i, attempt in enumerate(attempts):
            if not isinstance(attempt, dict):
                errors.append(f"attempts[{i}] must be an object")
                continue
            if not attempt.get("attempt_id"):
                errors.append(f"attempts[{i}] missing attempt_id")
            if not _is_valid_optional_datetime(attempt.get("attempted_at")):
                errors.append(f"attempts[{i}] attempted_at must be ISO datetime with timezone")
            assistance = attempt.get("assistance", [])
            if not isinstance(assistance, list):
                errors.append(f"attempts[{i}] assistance must be list")
            else:
                invalid = [x for x in assistance if x not in ASSISTANCE_CATEGORIES]
                if invalid:
                    errors.append(f"attempts[{i}] invalid assistance categories: {invalid}")

    revisions = data.get("revisions", [])
    if not isinstance(revisions, list):
        errors.append("revisions must be a list")
    else:
        for i, rev in enumerate(revisions):
            if not isinstance(rev, dict):
                errors.append(f"revisions[{i}] must be an object")
                continue
            if not _is_valid_optional_date(rev.get("revision_date")):
                errors.append(f"revisions[{i}] revision_date must be YYYY-MM-DD")
            if rev.get("recall_outcome") not in REVISION_OUTCOMES:
                errors.append(f"revisions[{i}] invalid recall_outcome")
            if "next_revision_date" in rev and not _is_valid_optional_date(rev.get("next_revision_date")):
                errors.append(f"revisions[{i}] next_revision_date must be YYYY-MM-DD or null")

    solution_files = data.get("solution_files", [])
    if not isinstance(solution_files, list):
        errors.append("solution_files must be a list")
    elif problem_dir is not None:
        for rel in solution_files:
            if not isinstance(rel, str):
                errors.append("solution_files entries must be string paths")
                continue
            if not (problem_dir / rel).exists():
                errors.append(f"Broken solution reference: {rel}")

    return errors


def validate_all_metadata(paths: TrackerPaths) -> list[str]:
    errors: list[str] = []
    seen_ids: dict[str, Path] = {}
    for problem_dir in list_problem_dirs(paths):
        try:
            data = load_problem(problem_dir)
        except Exception as exc:  # pragma: no cover
            errors.append(f"{problem_dir}: failed to load ({exc})")
            continue
        problem_id = data.get("problem_id")
        if problem_id in seen_ids:
            errors.append(
                f"Duplicate problem_id {problem_id}: {seen_ids[problem_id]} and {problem_dir}"
            )
        elif problem_id:
            seen_ids[problem_id] = problem_dir
        for msg in validate_problem_data(data, problem_dir=problem_dir):
            errors.append(f"{problem_dir.name}: {msg}")
    return errors


def _next_attempt_id(problem: dict[str, Any]) -> str:
    return f"ATT-{len(problem.get('attempts', [])) + 1:04d}"


def _next_revision_id(problem: dict[str, Any]) -> str:
    return f"REV-{len(problem.get('revisions', [])) + 1:04d}"


def _load_revision_policy(paths: TrackerPaths) -> dict[str, Any]:
    if not paths.revision_policy_path.exists():
        raise TrackerError("Missing revision policy config")
    return json.loads(paths.revision_policy_path.read_text(encoding="utf-8"))


def _add_months(base: date, months: int) -> date:
    month_index = base.month - 1 + months
    year = base.year + month_index // 12
    month = month_index % 12 + 1
    day = base.day
    while True:
        try:
            return date(year, month, day)
        except ValueError:
            day -= 1


def compute_next_revision_date(
    revision_date: date,
    recall_outcome: str,
    policy_name: str,
    previous_revisions_count: int,
    policy_config: dict[str, Any],
    manual_interval_days: int | None = None,
    manual_next_date: str | None = None,
) -> str:
    if manual_next_date:
        parse_date(manual_next_date)
        return manual_next_date

    if manual_interval_days is not None:
        if manual_interval_days <= 0:
            raise TrackerError("manual_interval_days must be positive")
        return (revision_date + timedelta(days=manual_interval_days)).isoformat()

    named = policy_config.get("named_policies", {})
    if policy_name not in named:
        raise TrackerError(f"Unknown revision policy: {policy_name}")
    policy = named[policy_name]

    if policy.get("type") == "monthly":
        months = int(policy.get("months", 1))
        return _add_months(revision_date, months).isoformat()

    intervals = list(policy.get("days", []))
    if not intervals:
        raise TrackerError("Revision policy has no intervals")

    idx = min(previous_revisions_count, len(intervals) - 1)
    if recall_outcome == "Easy recall":
        idx = min(idx + 1, len(intervals) - 1)
    elif recall_outcome in {"Needed substantial help", "Could not solve"}:
        idx = 0
    elif recall_outcome == "Could solve but could not explain":
        idx = max(0, idx - 1)

    return (revision_date + timedelta(days=int(intervals[idx]))).isoformat()


def _difficulty_path(paths: TrackerPaths, difficulty: str) -> Path:
    return paths.problems_root / difficulty_dir_name(difficulty)


def _build_problem_folder_name(problem_id: str, title: str) -> str:
    return f"{problem_id}-{slugify(title)}"


def add_problem(
    paths: TrackerPaths,
    problem_id: str,
    title: str,
    difficulty: str,
    primary_topic: str,
    platform_name: str,
    platform_problem_id: str,
    platform_url: str,
    date_added: str,
) -> Path:
    if difficulty not in VALID_DIFFICULTIES:
        raise TrackerError("Invalid difficulty")
    parse_date(date_added)

    if get_problem_dir_by_id(paths, problem_id):
        raise TrackerError(f"Problem ID already exists: {problem_id}")

    folder = _difficulty_path(paths, difficulty) / _build_problem_folder_name(problem_id, title)
    if folder.exists():
        raise TrackerError(f"Target folder already exists: {folder}")

    (folder / "attempts").mkdir(parents=True)
    (folder / "solutions").mkdir(parents=True)
    (folder / "attempts" / ".gitkeep").write_text("", encoding="utf-8")

    data = {
        "problem_id": problem_id,
        "title": title,
        "platforms": [
            {
                "name": platform_name,
                "problem_id": platform_problem_id,
                "url": platform_url,
            }
        ],
        "difficulty": difficulty,
        "primary_topic": primary_topic,
        "topic_tags": [],
        "patterns": [],
        "status": "not started",
        "date_added": date_added,
        "first_attempted_date": None,
        "first_solved_date": None,
        "last_attempted_date": None,
        "languages_used": [],
        "solution_files": [],
        "approaches": [],
        "attempts": [],
        "revisions": [],
        "related_problem_ids": [],
        "notes": None,
        "key_insights": [],
    }
    dump_yaml(folder / "problem.yaml", data)
    (folder / "README.md").write_text(
        f"# {problem_id} — {title}\n\nAdd notes, approaches, and lessons learned here.\n",
        encoding="utf-8",
    )
    return folder


def update_problem(
    paths: TrackerPaths,
    problem_id: str,
    updates: dict[str, Any],
    move_on_difficulty_change: bool = True,
) -> Path:
    problem_dir = get_problem_dir_by_id(paths, problem_id)
    if problem_dir is None:
        raise TrackerError(f"Problem not found: {problem_id}")

    data = load_problem(problem_dir)
    old_difficulty = data.get("difficulty")

    for key, value in updates.items():
        data[key] = value

    errors = validate_problem_data(data, problem_dir=problem_dir)
    if errors:
        raise TrackerError("Invalid update: " + "; ".join(errors))

    target_dir = problem_dir
    if move_on_difficulty_change and "difficulty" in updates and updates["difficulty"] != old_difficulty:
        new_base = _difficulty_path(paths, updates["difficulty"])
        target_dir = new_base / problem_dir.name
        if target_dir.exists() and target_dir != problem_dir:
            raise TrackerError(f"Cannot move problem: destination exists ({target_dir})")
        problem_dir.rename(target_dir)

    dump_yaml(target_dir / "problem.yaml", data)
    return target_dir


def record_attempt(
    paths: TrackerPaths,
    problem_id: str,
    attempted_at: str,
    outcome: str,
    approach_id: str | None,
    language: str | None,
    assistance: list[str],
    assistance_details: str | None,
    submission_url: str | None,
    time_taken_minutes: int | None,
    mistakes: str | None,
    reflection: str | None,
    independently_reproduced_after: bool,
) -> dict[str, Any]:
    problem_dir = get_problem_dir_by_id(paths, problem_id)
    if not problem_dir:
        raise TrackerError(f"Problem not found: {problem_id}")

    if not _is_valid_optional_datetime(attempted_at):
        raise TrackerError("attempted_at must be ISO datetime with timezone")

    invalid_assistance = [x for x in assistance if x not in ASSISTANCE_CATEGORIES]
    if invalid_assistance:
        raise TrackerError(f"Invalid assistance categories: {invalid_assistance}")

    data = load_problem(problem_dir)
    attempt = {
        "attempt_id": _next_attempt_id(data),
        "attempted_at": attempted_at,
        "approach_id": approach_id,
        "language": language,
        "outcome": outcome,
        "time_taken_minutes": time_taken_minutes,
        "assistance": assistance,
        "assistance_details": assistance_details,
        "submission_url": submission_url,
        "mistakes_lessons": mistakes,
        "reflection": reflection,
        "independently_reproduced_after": independently_reproduced_after,
    }

    data.setdefault("attempts", []).append(attempt)
    attempt_date = attempted_at[:10]
    if data.get("first_attempted_date") is None:
        data["first_attempted_date"] = attempt_date
    data["last_attempted_date"] = attempt_date

    if outcome.lower() in {"solved", "accepted", "success"}:
        if data.get("first_solved_date") is None:
            data["first_solved_date"] = attempt_date
        if assistance == ["Independent"]:
            data["status"] = "independently solved"
        elif "Independent" not in assistance:
            data["status"] = "solved with help"
    else:
        if data.get("status") == "not started":
            data["status"] = "attempted"

    if language and language not in data.get("languages_used", []):
        data.setdefault("languages_used", []).append(language)

    dump_yaml(problem_dir / "problem.yaml", data)

    attempt_file = problem_dir / "attempts" / f"{attempt['attempt_id']}.md"
    attempt_file.write_text(
        "\n".join(
            [
                f"# {attempt['attempt_id']}",
                f"- Attempted At: {attempted_at}",
                f"- Outcome: {outcome}",
                f"- Approach ID: {approach_id}",
                f"- Language: {language}",
                f"- Assistance: {', '.join(assistance) if assistance else 'None'}",
                f"- Submission URL: {submission_url}",
                "",
                "## Mistakes / Lessons",
                mistakes or "",
                "",
                "## Reflection",
                reflection or "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    return attempt


def record_revision(
    paths: TrackerPaths,
    problem_id: str,
    revision_date_str: str,
    recall_outcome: str,
    solved_without_assistance: bool,
    explained_complexity: bool,
    time_taken_minutes: int | None,
    mistakes: str | None,
    policy_name: str | None,
    manual_interval_days: int | None,
    manual_next_date: str | None,
) -> dict[str, Any]:
    problem_dir = get_problem_dir_by_id(paths, problem_id)
    if not problem_dir:
        raise TrackerError(f"Problem not found: {problem_id}")
    if recall_outcome not in REVISION_OUTCOMES:
        raise TrackerError("Invalid revision outcome")

    revision_date = parse_date(revision_date_str)
    policy_cfg = _load_revision_policy(paths)
    policy = policy_name or policy_cfg.get("default_policy", "spaced")

    data = load_problem(problem_dir)
    next_revision = compute_next_revision_date(
        revision_date=revision_date,
        recall_outcome=recall_outcome,
        policy_name=policy,
        previous_revisions_count=len(data.get("revisions", [])),
        policy_config=policy_cfg,
        manual_interval_days=manual_interval_days,
        manual_next_date=manual_next_date,
    )

    event = {
        "revision_id": _next_revision_id(data),
        "revision_date": revision_date_str,
        "recall_outcome": recall_outcome,
        "solved_without_assistance": solved_without_assistance,
        "explained_approach_and_complexity": explained_complexity,
        "time_taken_minutes": time_taken_minutes,
        "mistakes_or_forgotten_details": mistakes,
        "next_revision_date": next_revision,
        "policy_used": policy,
        "manual_interval_days": manual_interval_days,
        "manual_next_date_override": manual_next_date,
    }

    data.setdefault("revisions", []).append(event)
    if solved_without_assistance and explained_complexity and recall_outcome == "Easy recall":
        if data.get("status") in {"independently solved", "solved with help"}:
            data["status"] = "mastered"
    dump_yaml(problem_dir / "problem.yaml", data)
    return event


def _latest_next_revision_date(problem: dict[str, Any]) -> str | None:
    revisions = problem.get("revisions", [])
    if not revisions:
        return None
    return revisions[-1].get("next_revision_date")


def list_due_revisions(
    paths: TrackerPaths,
    as_of_date: str,
    overdue_only: bool = False,
) -> list[dict[str, Any]]:
    today = parse_date(as_of_date)
    result: list[dict[str, Any]] = []
    for pdir in list_problem_dirs(paths):
        problem = load_problem(pdir)
        next_date_str = _latest_next_revision_date(problem)
        if not next_date_str:
            continue
        due_date = parse_date(next_date_str)
        if overdue_only and due_date >= today:
            continue
        if not overdue_only and due_date > today:
            continue
        result.append(
            {
                "problem_id": problem.get("problem_id"),
                "title": problem.get("title"),
                "difficulty": problem.get("difficulty"),
                "next_revision_date": next_date_str,
                "overdue": due_date < today,
                "problem_dir": str(pdir.relative_to(paths.root)),
            }
        )
    return sorted(result, key=lambda x: (x["next_revision_date"], x["problem_id"]))


def list_problems(
    paths: TrackerPaths,
    topic: str | None = None,
    difficulty: str | None = None,
    platform: str | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for pdir in list_problem_dirs(paths):
        p = load_problem(pdir)
        if topic:
            tags = [p.get("primary_topic", "")] + list(p.get("topic_tags", []))
            if topic not in tags:
                continue
        if difficulty and p.get("difficulty") != difficulty:
            continue
        if status and p.get("status") != status:
            continue
        if platform:
            names = [item.get("name") for item in p.get("platforms", []) if isinstance(item, dict)]
            if platform not in names:
                continue
        rows.append(
            {
                "problem_id": p.get("problem_id"),
                "title": p.get("title"),
                "difficulty": p.get("difficulty"),
                "status": p.get("status"),
                "primary_topic": p.get("primary_topic"),
                "dir": str(pdir.relative_to(paths.root)),
            }
        )
    return sorted(rows, key=lambda x: x["problem_id"])


def _count_assisted_and_independent_solves(problem: dict[str, Any]) -> tuple[int, int]:
    independent = 0
    assisted = 0
    for attempt in problem.get("attempts", []):
        outcome = str(attempt.get("outcome", "")).lower()
        if outcome not in {"solved", "accepted", "success"}:
            continue
        assistance = attempt.get("assistance", [])
        if assistance == ["Independent"]:
            independent += 1
        elif assistance:
            assisted += 1
    return independent, assisted


def generate_dashboards(paths: TrackerPaths, as_of_date: str | None = None) -> None:
    today = parse_date(as_of_date) if as_of_date else date.today()

    problems: list[dict[str, Any]] = []
    for pdir in list_problem_dirs(paths):
        p = load_problem(pdir)
        p["_dir"] = pdir
        problems.append(p)

    problems.sort(key=lambda x: x.get("problem_id", ""))

    total_unique = len(problems)
    total_attempts = sum(len(p.get("attempts", [])) for p in problems)
    total_approaches = sum(len(p.get("approaches", [])) for p in problems)
    total_implementations = sum(len(p.get("solution_files", [])) for p in problems)
    independent_solves = 0
    assisted_solves = 0
    mastered = sum(1 for p in problems if p.get("status") == "mastered")
    for p in problems:
        indep, assist = _count_assisted_and_independent_solves(p)
        independent_solves += indep
        assisted_solves += assist

    all_problems_lines = [
        "<!-- GENERATED FILE: DO NOT EDIT MANUALLY -->",
        "",
        "# All Problems Index",
        "",
        f"- Unique problems: **{total_unique}**",
        f"- Total attempts: **{total_attempts}**",
        f"- Total approaches: **{total_approaches}**",
        f"- Implementations: **{total_implementations}**",
        f"- Independent solves: **{independent_solves}**",
        f"- Assisted solves: **{assisted_solves}**",
        f"- Problems mastered: **{mastered}**",
        "",
        "| ID | Title | Difficulty | Status | Topic | Folder |",
        "|---|---|---|---|---|---|",
    ]
    for p in problems:
        rel = p["_dir"].relative_to(paths.root)
        all_problems_lines.append(
            f"| {p.get('problem_id')} | {p.get('title')} | {p.get('difficulty')} | {p.get('status')} | {p.get('primary_topic')} | [{rel}]({rel.as_posix()}) |"
        )

    difficulty_counts = {"Easy": 0, "Medium": 0, "Hard": 0}
    for p in problems:
        difficulty_counts[p.get("difficulty", "Easy")] += 1
    all_problems_lines += ["", "## Difficulty-wise counts", ""]
    for d in ["Easy", "Medium", "Hard"]:
        all_problems_lines.append(f"- {d}: {difficulty_counts[d]}")

    topic_counts: dict[str, int] = {}
    for p in problems:
        t = p.get("primary_topic")
        topic_counts[t] = topic_counts.get(t, 0) + 1
    topic_lines = [
        "<!-- GENERATED FILE: DO NOT EDIT MANUALLY -->",
        "",
        "# Topic Progress",
        "",
        "| Topic | Problems |",
        "|---|---|",
    ]
    for t in sorted(topic_counts):
        topic_lines.append(f"| {t} | {topic_counts[t]} |")

    platform_counts: dict[str, int] = {}
    for p in problems:
        seen = set()
        for plat in p.get("platforms", []):
            name = plat.get("name") if isinstance(plat, dict) else None
            if name and name not in seen:
                platform_counts[name] = platform_counts.get(name, 0) + 1
                seen.add(name)
    platform_lines = [
        "<!-- GENERATED FILE: DO NOT EDIT MANUALLY -->",
        "",
        "# Platform Progress",
        "",
        "| Platform | Unique Problems |",
        "|---|---|",
    ]
    for name in sorted(platform_counts):
        platform_lines.append(f"| {name} | {platform_counts[name]} |")

    due = list_due_revisions(paths, today.isoformat(), overdue_only=False)
    overdue = list_due_revisions(paths, today.isoformat(), overdue_only=True)
    rev_lines = [
        "<!-- GENERATED FILE: DO NOT EDIT MANUALLY -->",
        "",
        "# Revision Queue",
        "",
        f"Generated as of: {today.isoformat()}",
        "",
        "## Due Today or Earlier",
    ]
    if due:
        for row in due:
            rev_lines.append(f"- {row['problem_id']} ({row['next_revision_date']})")
    else:
        rev_lines.append("- None")
    rev_lines.append("")
    rev_lines.append("## Overdue")
    if overdue:
        for row in overdue:
            rev_lines.append(f"- {row['problem_id']} ({row['next_revision_date']})")
    else:
        rev_lines.append("- None")

    assistance_lines = [
        "<!-- GENERATED FILE: DO NOT EDIT MANUALLY -->",
        "",
        "# Assistance Dependency Analysis",
        "",
        "| ID | Independent Solves | Assisted Solves |",
        "|---|---:|---:|",
    ]
    for p in problems:
        indep, assist = _count_assisted_and_independent_solves(p)
        assistance_lines.append(f"| {p.get('problem_id')} | {indep} | {assist} |")

    approach_lines = [
        "<!-- GENERATED FILE: DO NOT EDIT MANUALLY -->",
        "",
        "# Approach Comparison",
        "",
        "| Problem ID | Approaches | Implementations |",
        "|---|---:|---:|",
    ]
    one_approach: list[str] = []
    attempted_not_independent: list[str] = []
    recent_activity: list[tuple[str, str]] = []

    for p in problems:
        ap_count = len(p.get("approaches", []))
        imp_count = len(p.get("solution_files", []))
        approach_lines.append(f"| {p.get('problem_id')} | {ap_count} | {imp_count} |")
        if ap_count == 1:
            one_approach.append(str(p.get("problem_id")))

        if p.get("attempts") and p.get("status") not in {"independently solved", "mastered"}:
            attempted_not_independent.append(str(p.get("problem_id")))

        for attempt in p.get("attempts", []):
            at = attempt.get("attempted_at")
            if isinstance(at, str):
                recent_activity.append((at, f"Attempt {p.get('problem_id')}"))
        for rev in p.get("revisions", []):
            rd = rev.get("revision_date")
            if isinstance(rd, str):
                recent_activity.append((rd + "T00:00:00Z", f"Revision {p.get('problem_id')}"))

    approach_lines += ["", "## Problems with only one documented approach", ""]
    if one_approach:
        approach_lines += [f"- {pid}" for pid in sorted(one_approach)]
    else:
        approach_lines.append("- None")

    approach_lines += ["", "## Attempted problems not yet independently solved", ""]
    if attempted_not_independent:
        approach_lines += [f"- {pid}" for pid in sorted(attempted_not_independent)]
    else:
        approach_lines.append("- None")

    approach_lines += ["", "## Recent solving and revision activity", ""]
    for ts, label in sorted(recent_activity, reverse=True)[:20]:
        approach_lines.append(f"- {ts} — {label}")
    if not recent_activity:
        approach_lines.append("- None")

    (paths.dashboards_root / "all-problems.md").write_text("\n".join(all_problems_lines) + "\n", encoding="utf-8")
    (paths.dashboards_root / "topic-progress.md").write_text("\n".join(topic_lines) + "\n", encoding="utf-8")
    (paths.dashboards_root / "platform-progress.md").write_text("\n".join(platform_lines) + "\n", encoding="utf-8")
    (paths.dashboards_root / "revision-queue.md").write_text("\n".join(rev_lines) + "\n", encoding="utf-8")
    (paths.dashboards_root / "assistance-analysis.md").write_text(
        "\n".join(assistance_lines) + "\n", encoding="utf-8"
    )
    (paths.dashboards_root / "approach-comparison.md").write_text(
        "\n".join(approach_lines) + "\n", encoding="utf-8"
    )


def tracker_statistics(paths: TrackerPaths) -> dict[str, Any]:
    problems = [load_problem(p) for p in list_problem_dirs(paths)]
    return {
        "unique_problems": len(problems),
        "total_attempts": sum(len(p.get("attempts", [])) for p in problems),
        "total_revisions": sum(len(p.get("revisions", [])) for p in problems),
        "status_counts": {
            status: sum(1 for p in problems if p.get("status") == status)
            for status in sorted(VALID_STATUSES)
        },
    }
