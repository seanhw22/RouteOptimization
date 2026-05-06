## Why

The existing MDVRP codebase is a CLI-only tool requiring manual script execution and direct database/file access to run solvers and view results. Wrapping it in a Django web application makes it accessible to non-technical users, enables persistent experiment history with user accounts, and provides interactive route visualization — all required for the thesis demonstration.

## What Changes

- **New**: Django project with four apps (`accounts`, `datasets`, `runs`, `results`) wrapping the existing solver code
- **New**: Django ORM models replacing the SQLAlchemy layer (`src/database.py`, `src/data_loader.py`, `src/experiment_tracker.py` rewritten); Django's built-in auth replaces custom `users`/`sessions` tables
- **New**: Dataset upload page — accepts CSV/XLSX files or manual form input, validates, and saves to DB via Django ORM
- **New**: Solver configuration and run triggering — each algorithm (Greedy, HGA, optionally MILP if ≤25 nodes) launched as a separate subprocess with PID stored in DB
- **New**: `run_batch` table grouping simultaneous algorithm runs for one-click execution and comparison
- **New**: Subprocess progress reporting — solvers write status/progress/logs to DB periodically; Django polls via AJAX
- **New**: "Skip MILP" / kill-any-solver via `process.terminate()` using stored PID (Windows-compatible)
- **New**: Live Run Viewer — polling-based progress display (status bars, current best objective, log lines per algorithm)
- **New**: Results page — interactive route map (Leaflet.js + GeoJSON), per-algorithm stats, comparison chart (Chart.js), export buttons
- **New**: Guest session flow — anonymous users get a Django session; their datasets auto-expire after 3 days; registered users get permanent storage
- **Modified**: Experiment tracking — new fields (`status`, `pid`, `progress_pct`, `progress_log`, `best_objective`, `started_at`, `completed_at`) and foreign key to `run_batch`
- Algorithms (`algorithms/*.py`), `src/exporter.py`, `src/distance_matrix.py`, `src/distance_cache.py` are **unchanged**

## Capabilities

### New Capabilities
- `web-auth`: User registration, login, logout, and guest (anonymous) session management with dataset ownership and 3-day auto-expiry for guest data
- `dataset-upload`: Web-based dataset input (CSV/XLSX upload or manual form), schema validation, preview, and persistent storage via Django ORM
- `solver-orchestration`: Subprocess-based solver execution (Greedy + HGA + optional MILP), PID tracking, kill/skip-MILP support, run-batch grouping for parallel algorithm comparison
- `live-run-viewer`: Polling-based live progress display showing per-algorithm status, progress percentage, best objective, and log lines
- `results-dashboard`: Interactive results page with Leaflet route map, per-route stats table, algorithm comparison chart, and export buttons (CSV/PDF/GeoJSON)

### Modified Capabilities
- `experiment-tracking`: Add `status`, `pid`, `progress_pct`, `progress_log`, `best_objective`, `started_at`, `completed_at` fields; add FK to `run_batch`

## Impact

- **New dependencies**: `django>=4.2`, `django-crispy-forms` (optional, for form styling)
- **Removed dependencies**: `sqlalchemy`, `psycopg2-binary` (replaced by `psycopg2` via Django's database backend)
- **DB schema**: Existing tables preserved; `users`/`sessions` tables replaced by Django's `auth_user`/`django_session`; `experiments` table gains new columns; new `run_batch` table added; schema managed via Django migrations going forward
- **File layout**: New top-level `mdvrp_web/` Django project directory; `individual_runs/` scripts repurposed as subprocess entry points (minor modifications to accept `--experiment-id` and write progress to DB)
- **Deployment**: Standard Django deployment (gunicorn + nginx or similar); no Redis/Celery required; subprocess approach works on Windows and Linux
