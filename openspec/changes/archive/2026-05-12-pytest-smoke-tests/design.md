## Context

The project has five Django apps (`accounts`, `datasets`, `runs`, `results`, plus the solver algorithms in `algorithms/` and `src/`). All behaviour has been manually verified. Every `tests.py` file is an empty stub. There are no pytest fixtures, no CI gate, and no SQLite override — running `pytest` today would try to connect to the production PostgreSQL database and collect zero tests.

Two pieces are already in place from the initial scaffolding work:
- `pytest.ini` (project root) — points `pytest-django` at `mdvrp_web.settings` and sets `testpaths = tests`
- `tests/conftest.py` — seven shared fixtures (DB override, frames, user, datasets, clients, tiny problem)

The remaining work is writing the actual test modules.

## Goals / Non-Goals

**Goals:**
- A `pytest` run with no external services (no PostgreSQL, no Gurobi, no running Django server) that passes green
- Cover the three layers: service functions, HTTP views, algorithm solvers
- Serve as regression guards — fail loudly if a refactor breaks something that was known to work

**Non-Goals:**
- Full coverage — these are smoke tests, not exhaustive unit tests
- MILP solver testing (requires a Gurobi license)
- Testing subprocess internals (`launch_subprocess`, `_pid_alive`, `terminate_experiment`) — too much OS coupling for a smoke suite
- Frontend / template rendering correctness beyond HTTP status codes

## Decisions

### SQLite in-memory for test DB
The production settings hard-code PostgreSQL via `DATABASE_URL`. Rather than shipping a separate `settings_test.py`, the `django_db_setup` fixture in `conftest.py` overrides `DATABASES` to `sqlite3 :memory:` before `setup_databases` runs. This keeps one settings file and avoids any environment variable juggling in CI.

*Alternative considered*: a `settings_test.py` that inherits from `settings.py`. Rejected — extra file, same outcome, adds an indirection.

### Mock `launch_all` at the call site in view tests
The configure view (`runs/views.py`) calls `launch_all(experiments)` which spawns real subprocesses. View smoke tests patch `runs.views.launch_all` with `unittest.mock.patch` so the HTTP flow (form validation → batch creation → redirect) can be verified without spawning processes.

*Alternative considered*: Let the subprocess spawn but point it at a no-op script. Rejected — fragile, slow, and couples tests to filesystem layout.

### Dict-based params for algorithm fixtures
Both Greedy and HGA support two param paths: NumPy arrays and plain dicts. The dict path is activated by passing `data_source=None` and building `params` manually. This avoids importing NumPy and building index mappings in test setup, keeping the fixture short and readable.

### Test layout: top-level `tests/` directory
Per-app `tests.py` files are Django convention for `manage.py test`. Since we're using `pytest` exclusively, a single top-level `tests/` directory with one file per concern is cleaner and keeps fixture sharing straightforward via `conftest.py`.

## Risks / Trade-offs

- **`RunsConfig.ready()` warning**: On startup, `RunsConfig.ready()` calls `mark_stale_experiments()`. The existing guard checks `sys.argv[1] in _SKIP_COMMANDS` which catches `manage.py test` but not pytest. The function is already wrapped in `try/except`, so it fails silently — the warning is benign. No production code change needed.

- **SQLite vs PostgreSQL dialect gaps**: A small number of ORM queries may behave differently on SQLite (e.g., JSON field operations, `__icontains` on JSON). If a test fails due to dialect mismatch rather than real logic, the fix is to adjust the query or mark the test `@pytest.mark.skipif`. This is unlikely given the queries used.

- **DEAP global state**: `MDVRPHGA._setup_deap()` registers classes on the `deap.creator` module globally. Running multiple HGA tests in the same process will trigger `hasattr(creator, "FitnessMin")` guards — the code already handles this, so it's not a problem.

## Migration Plan

1. Install `pytest-django` (`pip install pytest-django` — already done)
2. `pytest.ini` and `tests/conftest.py` already exist
3. Add test modules one by one — each is independently runnable
4. `pytest` from the project root to verify green

No rollback needed — test files are additive and don't touch production code.
