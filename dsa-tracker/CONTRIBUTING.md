# Contributing

1. Create or update problem metadata under `problems/<difficulty>/<problem-id-folder>/problem.yaml`.
2. Keep generated dashboard files in `dashboards/` deterministic by running:
   - `python -m scripts.dsa_tracker generate-dashboards`
3. Validate metadata and run tests before committing:
   - `python -m scripts.dsa_tracker validate-metadata`
   - `pytest`
4. Do not fabricate attempts, solve dates, or revision history.
