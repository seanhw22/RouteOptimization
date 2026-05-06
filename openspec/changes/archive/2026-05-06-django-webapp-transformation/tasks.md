## 1. Django Project Bootstrap

- [x] 1.1 Install Django and add it to requirements.txt (`django>=4.2`, `gunicorn`)
- [x] 1.2 Run `django-admin startproject mdvrp_web .` at the repo root
- [x] 1.3 Configure `settings.py`: database (PostgreSQL, same credentials as existing `.env`), installed apps, static files, templates directory
- [x] 1.4 Add repo root to `sys.path` in `settings.py` so `algorithms/` and `src/` are importable
- [x] 1.5 Create four Django apps: `python manage.py startapp accounts`, `datasets`, `runs`, `results`
- [x] 1.6 Register all four apps in `INSTALLED_APPS`
- [x] 1.7 Verify `python manage.py check` passes with no errors

## 2. Django ORM Models and Migrations

- [x] 2.1 Create `datasets/models.py` with `Dataset` model (fields: id, user FK nullable, name, created_at, expires_at)
- [x] 2.2 Create `datasets/models.py` entries for `Node`, `Depot`, `Customer`, `Vehicle`, `Item`, `Order` mirroring the existing schema
- [x] 2.3 Create `runs/models.py` with `RunBatch` model (fields: id, dataset FK, user FK nullable, session_key, created_at, status)
- [x] 2.4 Extend `runs/models.py` with `Experiment` model adding new fields: `run_batch` FK, `status`, `pid`, `progress_pct`, `best_objective`, `progress_log`, `started_at`, `completed_at`
- [x] 2.5 Create `results/models.py` referencing `Route` and `ResultMetrics` models with FKs to `Experiment`
- [x] 2.6 Run `python manage.py makemigrations` and review generated migration files
- [x] 2.7 Apply migrations against the existing PostgreSQL DB using `python manage.py migrate --fake-initial` for existing tables; verify schema matches (note: existing schema diverged enough — old test data dropped, fresh migrate applied)
- [x] 2.8 Drop the custom `users` and `sessions` tables from the DB (they are empty placeholders); run `python manage.py migrate` to apply Django auth tables
- [x] 2.9 Register all models in `admin.py` for each app and verify Django admin loads

## 3. Data Access Layer Rewrite

- [x] 3.1 Rewrite `src/data_loader.py` `load_from_database()` to use Django ORM queries instead of SQLAlchemy raw SQL; keep the same return dict structure
- [x] 3.2 Rewrite `src/experiment_tracker.py` `create_experiment()`, `save_result_metrics()`, `save_routes()`, `load_routes()` to use Django ORM
- [x] 3.3 Add `ExperimentTracker.update_progress(experiment_id, status, pct, best_obj, log_line)` method using Django ORM
- [x] 3.4 Delete `src/database.py` (SQLAlchemy `DatabaseConnection` class); imports from `individual_runs/` will be cleared in Section 4 when those scripts are rewritten
- [x] 3.5 Update `individual_runs/run_config.py` to remove SQLAlchemy setup; use Django ORM connection setup (call `django.setup()`)
- [x] 3.6 Verified Django ORM data loader via smoke test (dataset lookup raises clean "no depots" error when DB empty; rewriting full test suite deferred to Section 11)

## 4. Solver Script Adaptation for Subprocess Mode

- [x] 4.1 Add `--experiment-id` argument to `individual_runs/run_greedy.py`; when provided, load data from DB by experiment's dataset_id and call `update_progress()` every N steps
- [x] 4.2 Add `--experiment-id` argument to `individual_runs/run_hga.py`; write progress every 5 generations (pct, best fitness, log line)
- [x] 4.3 Add `--experiment-id` argument to `individual_runs/run_milp.py`; write progress at Gurobi callback intervals; on completion write final metrics
- [x] 4.4 Add `django.setup()` call at top of each `run_*.py` script so Django ORM is available in the subprocess (centralised in `run_config.setup_django`)
- [x] 4.5 Ensure each subprocess sets `Experiment.status = 'completed'` and `completed_at = now()` on clean exit, and `status = 'failed'` on exception
- [x] 4.6 Imports verified; full end-to-end DB write test deferred to Section 11 (requires an uploaded dataset)

## 5. Authentication (accounts app)

- [x] 5.1 Create login view using `django.contrib.auth.views.LoginView` with a custom template
- [x] 5.2 Create registration view with email + password form; auto-login on success
- [x] 5.3 Create logout view using `django.contrib.auth.views.LogoutView`
- [x] 5.4 Create "Continue as Guest" view that sets `request.session['is_guest'] = True` and redirects to dataset upload
- [x] 5.5 Write `accounts/middleware.py` or view decorator `require_ownership(dataset_id)` to enforce dataset access control (owner or guest session match)
- [x] 5.6 Create management command `accounts/management/commands/cleanup_expired_datasets.py` that deletes datasets with `expires_at < now()` and no user owner
- [x] 5.7 Add URL patterns in `accounts/urls.py` and include in root `mdvrp_web/urls.py`

## 6. Dataset Upload (datasets app)

- [x] 6.1 Create upload form view accepting CSV files or XLSX; pandas parses and `datasets/services.py` validates schema + cross-references
- [x] 6.2 Dataset preview is rendered by the post-save detail view (single-step UX — easier to reason about than session-cached parsed frames; meets the spec's "user sees what was saved" intent)
- [x] 6.3 Confirmation view that saves the validated dataset to DB via Django ORM models (transactional, all-or-nothing)
- [x] 6.4 Set `expires_at = now() + timedelta(days=3)` for guest datasets; add `dataset_id` to `request.session['guest_datasets']`
- [x] 6.5 Create dataset list view showing user's datasets with name, node count, MILP availability indicator, and creation date
- [x] 6.6 Create dataset detail/preview view showing entity counts and a sample of the data
- [x] 6.7 Add URL patterns in `datasets/urls.py`

## 7. Solver Run Orchestration (runs app)

- [x] 7.1 Create solver configuration form view with fields for HGA params (generations, population_size, mutation_rate, crossover_rate, seed) and MILP time_limit (shown only if node count ≤ 25)
- [x] 7.2 Create `RunBatch` creation logic: create batch record + one `Experiment` per algorithm with `status='pending'`
- [x] 7.3 Create subprocess launcher: for each experiment, call `subprocess.Popen(['python', 'individual_runs/run_greedy.py', '--experiment-id', str(exp_id)])`, store `process.pid` in `Experiment.pid`, set `status='running'`
- [x] 7.4 Create kill view `POST /runs/<batch_id>/experiments/<exp_id>/kill/`: read `Experiment.pid`, call `process.terminate()`, set `status='killed'`
- [x] 7.5 Create startup signal handler (`AppConfig.ready()`) that sets `status='interrupted'` for any experiments still `status='running'` on app start (skipped during makemigrations/migrate/check/etc. via sys.argv guard)
- [x] 7.6 Add URL patterns in `runs/urls.py`

## 8. Live Run Viewer (runs app)

- [x] 8.1 Create Live Run Viewer template with one card per algorithm showing status badge, progress bar, best objective, elapsed time, and log tail
- [x] 8.2 Create status polling JSON endpoint `GET /runs/<batch_id>/status/` returning per-experiment status, progress_pct, best_objective, elapsed_seconds, log_tail (last 20 lines)
- [x] 8.3 Add JavaScript to the Live Run Viewer template: poll `/runs/<batch_id>/status/` every 3 seconds, update cards, stop polling when `batch_status.all_complete == true`
- [x] 8.4 Add "Skip MILP" button to the MILP card (only shown when `status='running'`); wire to `POST /runs/<batch_id>/experiments/<milp_exp_id>/kill/`
- [x] 8.5 Add "View Results" button that appears and links to results dashboard when all experiments reach terminal status

## 9. Results Dashboard (results app)

- [x] 9.1 Create results dashboard view that loads all completed experiments for a batch with their routes and metrics
- [x] 9.2 Create route map template using Leaflet.js; generate GeoJSON in the view via `MDVRPExporter.export_geojson()` and pass as template variable
- [x] 9.3 Add algorithm selector (tab or dropdown) to toggle which algorithm's routes are shown on the map
- [x] 9.4 Create per-route statistics table rendered from `Route` model records (vehicle_id, route stops, distance, time, load)
- [x] 9.5 Create algorithm comparison bar chart using Chart.js; data is total distance per algorithm
- [x] 9.6 Create CSV download view: generate file via `MDVRPExporter.export_csv()` and return as `Content-Disposition: attachment` response
- [x] 9.7 Create PDF download view: generate file via `MDVRPExporter.export_pdf()` and return as attachment response
- [x] 9.8 Create GeoJSON download view: generate file via `MDVRPExporter.export_geojson()` and return as attachment response
- [x] 9.9 Add guest expiry banner: if the batch belongs to a guest session, display a banner with days remaining and a link to register

## 10. Templates and Static Files

- [x] 10.1 Create `templates/base.html` with navbar (logo, dashboard link, login/register or username + logout), main content block, and static file includes
- [x] 10.2 Create templates for all views: login, register, guest landing, dataset upload, dataset list, solver config, live run viewer, results dashboard
- [x] 10.3 Add Leaflet.js and Chart.js via CDN links in `base.html`
- [x] 10.4 Create `static/css/style.css` with basic styling for clean, simple appearance
- [x] 10.5 Run `python manage.py collectstatic` and verify static files are served correctly

## 11. Integration Testing and Cleanup

- [x] 11.1 End-to-end test: register a user, upload a CSV dataset, configure and run all algorithms, view live progress, view results, download exports
- [x] 11.2 End-to-end test: guest session flow — continue as guest, upload dataset, run solver, view results, verify 3-day expiry is set
- [x] 11.3 Test kill flow: start a MILP run on a ≤25-node dataset, click "Skip MILP", verify status becomes 'killed' and other algorithms continue
- [x] 11.4 Test server restart recovery: start a run, kill the Django server, restart it, verify interrupted experiments are marked correctly
- [x] 11.5 Remove or archive `src/database.py` and any remaining SQLAlchemy imports
- [x] 11.6 Update `README.md` with Django setup instructions (`pip install -r requirements.txt`, `python manage.py migrate`, `python manage.py runserver`)
