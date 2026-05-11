## Why

The codebase has zero automated tests despite having five Django apps, two core algorithm solvers, and a dataset import pipeline — all manually verified during development. A smoke test suite locks in what's already known to work, making it safe to refactor or extend anything without silent regressions.

## What Changes

- **New**: `pytest.ini` at the project root wiring `pytest-django` to `mdvrp_web.settings`
- **New**: `tests/conftest.py` with seven shared fixtures (SQLite in-memory DB override, minimal dataset frames, user/dataset/client fixtures, tiny algorithm problem)
- **New**: `tests/test_dataset_service.py` — unit tests for `validate_frames`, `save_dataset`, `parse_uploaded`
- **New**: `tests/test_runs_service.py` — unit tests for `create_batch`, `create_experiments`
- **New**: `tests/test_views_datasets.py` — HTTP smoke tests for upload, list, detail views
- **New**: `tests/test_views_runs.py` — HTTP smoke tests for configure, viewer, status, kill views (subprocess launch mocked)
- **New**: `tests/test_algorithms.py` — regression smoke tests running Greedy and HGA on a tiny dict-based problem
- **Modified**: `requirements.txt` — adds `pytest-django>=4.8`

## Capabilities

### New Capabilities

- `dataset-service-tests`: Smoke tests for the dataset import service layer (parsing, validation, DB persistence)
- `runs-service-tests`: Smoke tests for run batch and experiment creation service functions
- `views-smoke-tests`: HTTP-level smoke tests for dataset and run views via Django test client
- `algorithm-smoke-tests`: Regression smoke tests running Greedy and HGA solvers on a minimal in-memory problem

### Modified Capabilities

## Impact

- **New dependency**: `pytest-django>=4.8` (test-only; does not affect production)
- **No production code changes** — tests run against existing code unchanged
- **DB**: Tests use SQLite in-memory; no PostgreSQL instance required to run the suite
- **MILP excluded**: Gurobi license required; MILP solver tests are out of scope
- **Subprocess launch mocked**: `runs.services.launch_all` is patched in view tests to avoid spawning real solver processes
