# DSA Tracker — GitHub-Native DSA Knowledge Base

Track DSA problems, solution approaches, attempts, revisions, and learning signals using canonical YAML records and generated Markdown dashboards.

## Features

- One canonical record per unique problem (`problem.yaml`)
- Multiple platforms, approaches, languages, attempts, and revisions per problem
- Append-only attempt/revision history
- Configurable revision scheduling (daily, alternate days, weekly, monthly, spaced, custom)
- Deterministic dashboard generation
- Metadata validation and safe problem management CLI

## Directory structure

```text
dsa-tracker/
├── README.md
├── ROADMAP.md
├── CONTRIBUTING.md
├── .gitignore
├── pyproject.toml
├── config/
├── problems/
├── templates/
├── dashboards/
├── scripts/
├── tests/
└── .github/workflows/validate-tracker.yml
```

## Prerequisites

- Python 3.10+
- macOS or Linux shell

## Setup (macOS/Linux)

```bash
cd dsa-tracker
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

Dependency note: YAML support requires `PyYAML`.

## CLI

Entry point:

```bash
python -m scripts.dsa_tracker --help
```

### Add a problem

```bash
python -m scripts.dsa_tracker add-problem \
  --problem-id LC-0121 \
  --title "Best Time to Buy and Sell Stock" \
  --difficulty Easy \
  --primary-topic Arrays \
  --platform-name LeetCode \
  --platform-problem-id 121 \
  --platform-url https://leetcode.com/problems/best-time-to-buy-and-sell-stock/ \
  --date-added 2026-10-18
```

Interactive mode:

```bash
python -m scripts.dsa_tracker add-problem --interactive
```

### View / update metadata

```bash
python -m scripts.dsa_tracker view-problem LC-0121
python -m scripts.dsa_tracker update-problem LC-0121 --set status=attempted
```

### Record multiple approaches

Store approach objects in `problem.yaml` and implementation paths under `solutions/<lang>/...`.
Use analytical complexity claims in metadata (not inferred from file names).

### Record tutor/AI assistance during attempts

```bash
python -m scripts.dsa_tracker record-attempt LC-0121 \
  --attempted-at 2026-10-18T18:30:00Z \
  --outcome solved \
  --approach-id A1 \
  --language python \
  --assistance "Hint,AI" \
  --assistance-details "Needed a binary search hint" \
  --reflection "Could reproduce after review"
```

Assistance categories:
- Independent
- Hint
- Tutor
- AI
- Editorial
- Existing solution
- Other

### Record revision and spaced repetition

```bash
python -m scripts.dsa_tracker revise-problem LC-0121 \
  --revision-date 2026-10-20 \
  --recall-outcome "Correct with minor hints" \
  --solved-without-assistance \
  --explained-complexity
```

Revision outcomes:
- Easy recall
- Correct with minor hints
- Needed substantial help
- Could not solve
- Could solve but could not explain

Manual override examples:

```bash
python -m scripts.dsa_tracker revise-problem LC-0121 \
  --revision-date 2026-10-20 \
  --recall-outcome "Could not solve" \
  --manual-interval-days 2

python -m scripts.dsa_tracker revise-problem LC-0121 \
  --revision-date 2026-10-20 \
  --recall-outcome "Easy recall" \
  --manual-next-date 2026-11-01
```

### Due/overdue revisions

```bash
python -m scripts.dsa_tracker list-due-revisions --as-of 2026-10-21
python -m scripts.dsa_tracker list-due-revisions --as-of 2026-10-21 --overdue
```

### Filtering and stats

```bash
python -m scripts.dsa_tracker list-problems --difficulty Easy --status attempted
python -m scripts.dsa_tracker list-problems --topic Graphs
python -m scripts.dsa_tracker list-problems --platform LeetCode
python -m scripts.dsa_tracker stats
```

### Generate dashboards

```bash
python -m scripts.dsa_tracker generate-dashboards
```

Generated files are in `dashboards/` and are deterministic with unchanged input.

## Metadata field guide

- `problem_id`: Stable unique internal ID (e.g., `LC-0121`)
- `platforms`: list of `{name, problem_id, url}` records
- `difficulty`: `Easy|Medium|Hard`
- `status`: `not started|attempted|solved with help|independently solved|mastered`
- `date_added`, `first_attempted_date`, `first_solved_date`, `last_attempted_date`: `YYYY-MM-DD` or null where applicable
- `approaches`: multiple approach records with ID, idea, pattern, complexity, trade-offs, edge-cases, correctness, use-cases, implementation/test flags, and source paths by language
- `attempts`: append-only history with assistance, lessons, reflection, submission URL
- `revisions`: spaced-repetition events with recall outcome and next revision date

## What runs automatically vs locally

- **Automatically on GitHub push/PR**: metadata validation, tests, dashboard regeneration check.
- **Manual local commands**: adding problems, recording attempts/revisions, generating dashboards when you change data.

## Running tests

```bash
pytest
python -m scripts.dsa_tracker validate-metadata
```

## Troubleshooting

- `ModuleNotFoundError: yaml` → run `pip install -e .[dev]`
- Validation failure for solution files → ensure paths in `solution_files` exist relative to each problem folder
- Date/time errors → use `YYYY-MM-DD` and ISO datetime with timezone, e.g. `2026-10-18T18:30:00Z`
