## Context

The MDVRP codebase is a mature CLI solver with clean separation: algorithms take Python dicts in and return dicts out, never touching the DB directly. The data access layer (`src/`) and the experiment entry points (`individual_runs/`) are the only parts that interact with storage. This clean boundary means the web layer can wrap the existing code with minimal modification.

Current DB uses PostgreSQL with a schema already designed in anticipation of webapp tables. The SQLAlchemy layer handles all DB access today. Django will replace it with its ORM while keeping PostgreSQL as the backend.

The project runs on Windows (development) and may be deployed to Linux. Solver runtimes range from seconds (Greedy) to hours (MILP on 25 nodes). The deployment must tolerate long-running background processes surviving web server restarts.

## Goals / Non-Goals

**Goals:**
- Provide a usable web interface for the full MDVRP workflow: upload → configure → run → view results → export
- Keep all existing solver algorithms completely unchanged
- Support guest (anonymous) sessions alongside registered user accounts
- Allow users to kill long-running MILP solvers from the browser
- Display live progress for all running solvers without WebSocket complexity
- Produce a clean, thesis-demo-quality UI

**Non-Goals:**
- Real-time WebSocket-based progress (polling is sufficient given typical runtimes)
- Horizontal scaling or multi-worker Celery setup
- Mobile-optimized UI
- Multi-tenancy beyond basic user account isolation
- Pause/resume solvers (Windows has no SIGSTOP; kill-only is sufficient)

## Decisions

### D1: Django ORM over SQLAlchemy

**Decision**: Replace the SQLAlchemy layer (`src/database.py`, `src/data_loader.py`, `src/experiment_tracker.py`) with Django ORM models. Django's built-in auth replaces the custom `users`/`sessions` tables.

**Rationale**: Running two ORMs against the same DB is fragile and confusing. Django ORM provides migrations, admin interface, auth, and session management for free. The solver algorithms don't use SQLAlchemy at all — only the data loading and tracking layer does, so the swap is contained.

**Alternative considered**: Dual ORM (keep SQLAlchemy for solver data, Django ORM for auth only). Rejected because it means two competing schema sources of truth and requires mapping between the two data models.

---

### D2: Subprocess execution over Celery/threading

**Decision**: Each solver run is launched as a Python subprocess (`python run_greedy.py --experiment-id=X`). PIDs are stored in the `experiments` table. The web server kills solvers via `process.terminate()`.

**Rationale**: Threads cannot be forcibly killed in Python — the MILP solver (Gurobi) can be deeply stuck in branch-and-bound and won't respond to cooperative stop signals. Subprocesses can be killed at the OS level. Celery adds Redis infrastructure and operational complexity unnecessary for a thesis project. Subprocess with PID storage survives web server restarts (the PID is in the DB, not in memory).

**Alternative considered**: Threading with `threading.Event` for stop signals. Rejected because Gurobi cannot be interrupted cooperatively; hard-kill is required.

**Alternative considered**: Celery + Redis. Rejected due to operational complexity and unnecessary infrastructure overhead for the project scope.

---

### D3: DB-based progress reporting over stdout parsing

**Decision**: Solver subprocesses write progress directly to new columns on the `experiments` table (`status`, `progress_pct`, `best_objective`, `progress_log`). Django views poll these columns on a 3-second interval via AJAX.

**Rationale**: stdout parsing from a subprocess is brittle and requires the parent process to stay alive and maintain a reader thread. DB-based progress is persistent (survives web server restarts), queryable, and keeps the polling endpoint simple. The 3-second poll interval is imperceptible for runs that take minutes to hours.

**Alternative considered**: Stdout streaming via SSE. Rejected because it requires the Django process to hold an open connection to the subprocess stdout, which is stateful and doesn't survive server restarts.

---

### D4: `run_batch` table for grouping parallel algorithm runs

**Decision**: Introduce a `run_batch` table. One user click creates one `run_batch` record and 2-3 `experiments` records (one per algorithm). All `experiments` in a batch share the same dataset and configuration context.

**Rationale**: The core user workflow is comparative — the user wants to see Greedy vs HGA vs MILP side-by-side. Without a batch concept, grouping the relevant experiments for a comparison view requires heuristics (same dataset, close timestamp). A batch FK makes this explicit and efficient.

```
run_batch (id, dataset_id, user/session, created_at, status)
    └── experiments (id, batch_id, algorithm, status, pid, progress_*, ...)
            └── routes (...)
            └── result_metrics (...)
```

---

### D5: Django project alongside existing code (no restructure)

**Decision**: Create a `mdvrp_web/` Django project directory at the repo root. Existing `algorithms/`, `src/`, `individual_runs/` directories stay in place. Django is added on top, not as a replacement structure.

**Rationale**: Minimizes risk — the working CLI tools remain functional throughout development. Django imports solver code via Python path (`sys.path` includes the repo root). The `individual_runs/` scripts become subprocess targets with minor additions (`--experiment-id` argument, progress DB writes).

---

### D6: Frontend with Django templates + Leaflet + Chart.js

**Decision**: Server-rendered Django templates with Leaflet.js for route maps and Chart.js for comparison charts. No separate SPA frontend.

**Rationale**: The data is not highly dynamic — most views are query-then-render. The only interactive parts are the live run viewer (AJAX polling) and the map. Leaflet.js renders the existing GeoJSON output from `src/exporter.py` directly. A full React/Vue SPA would double the codebase surface area for no benefit to the thesis demonstration.

---

### D7: Guest sessions via Django's anonymous session framework

**Decision**: Anonymous users get Django's built-in anonymous session. Dataset IDs created in that session are stored in `request.session['guest_datasets']`. Datasets have an `expires_at` field set to `now() + 3 days` for guest users (NULL for authenticated users). A management command `cleanup_expired_datasets` handles deletion.

**Rationale**: Django already manages anonymous sessions transparently. The pattern of storing user-owned resource IDs in the session is standard Django practice. The 3-day expiry matches the thesis spec requirement and avoids unbounded DB growth.

## Risks / Trade-offs

**[Risk] Subprocess PID stale on server restart** → If the Django server restarts mid-run, the in-memory subprocess handle is lost but the PID is in the DB. On startup, mark any `status='running'` experiments as `status='interrupted'`. The user can re-run.

**[Risk] Subprocess zombie processes on Windows** → Use `process.wait()` in a cleanup thread after `terminate()`, or accept that Django's process table cleans up on exit. For a thesis scope, this is acceptable.

**[Risk] Long-running MILP (10+ hours) and server restarts** → The PID is stored in DB; killing still works if the process is still alive. If the server restarted, the experiment is marked interrupted — acceptable behavior.

**[Risk] Django ORM migration to existing populated DB** → The existing schema has data. Django migrations must be written carefully to match the existing table structure rather than recreating it (use `--fake-initial` or `managed = False` initially, then migrate incrementally). See Migration Plan.

**[Risk] `progress_log` TEXT column growing unbounded** → Cap stored log lines at the last 100 entries; solver subprocess truncates before appending. This prevents unbounded growth for long MILP runs.

**[Trade-off] Polling vs WebSocket** → 3-second polling adds latency but avoids Django Channels setup. For runs measured in minutes to hours, this is imperceptible and acceptable.

## Migration Plan

1. **Schema bootstrap**: Run Django migrations against the existing PostgreSQL DB using `--fake-initial` for tables that already exist in the schema. New tables (`run_batch`, new columns on `experiments`) are applied normally.
2. **Parallel operation**: Django project and CLI tools coexist; no CLI functionality is removed. CLI still works throughout development.
3. **Data migration**: Existing `datasets`/`experiments`/`routes` rows remain valid. The new `run_batch` FK on experiments is nullable initially; backfilled if needed.
4. **Auth cutover**: The custom `users` and `sessions` tables in `schema.sql` are dropped (they have no data beyond what was seeded for testing). Django creates its own `auth_user` and `django_session` tables.
5. **Deployment**: `gunicorn mdvrp_web.wsgi` behind nginx or standalone. `python manage.py cleanup_expired_datasets` runs as a daily cron job.

## Open Questions

- **Solver script modification scope**: The `individual_runs/run_greedy.py`, `run_hga.py`, `run_milp.py` scripts need `--experiment-id` argument support and DB progress writes. How much of the existing script logic stays vs gets refactored into a new `individual_runs/run_solver.py` dispatcher? Recommend: thin dispatcher that imports and calls existing `run_*` functions, keeping current scripts as-is.
- **MILP best-found solution on kill**: When Gurobi is killed mid-run, the current best solution is lost. Should we save Gurobi's incumbent solution periodically? For thesis scope, probably not — just mark as killed. Worth confirming.
- **HGA progress granularity**: HGA currently reports per-generation via tqdm. Should progress writes happen every generation or every N generations? Recommend every 5 generations to reduce DB write overhead.
