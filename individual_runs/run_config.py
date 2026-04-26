"""Shared setup helpers for the individual MDVRP run scripts."""

import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def setup_path() -> str:
    """Ensure the repo root is on sys.path so algorithms/* and src/* import cleanly."""
    root = str(REPO_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)
    return root


def load_env_config() -> dict:
    """Load configuration from the .env file (DATABASE_URL, USE_DATABASE, DATASET_ID)."""
    env_file = REPO_ROOT / '.env'
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ.setdefault(key.strip(), value.strip())

    use_database = os.getenv('USE_DATABASE', 'false').lower() in ('true', '1', 'yes')
    dataset_id = int(os.getenv('DATASET_ID', '1'))
    return {'use_database': use_database, 'dataset_id': dataset_id}


def setup_django(settings_module: str = 'mdvrp_web.settings') -> None:
    """Initialise Django so the ORM is usable from this subprocess.

    Idempotent — safe to call multiple times.
    """
    setup_path()
    load_env_config()
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', settings_module)
    import django  # local import: only needed when database mode is active
    from django.apps import apps as _apps
    if not _apps.ready:
        django.setup()


def setup_data_source(dataset_id=None):
    """Decide whether the run should use the database or fall back to CSV.

    Returns ``(dataset_id_or_None, source_type)``. ``source_type`` is one of
    ``'database'`` or ``'csv'``. If neither is available the process exits.
    """
    config = load_env_config()
    dataset_id = dataset_id or config['dataset_id']

    if config['use_database']:
        try:
            setup_django()
            from datasets.models import Dataset
            if Dataset.objects.filter(pk=dataset_id).exists():
                print(f"[INFO] Using database: dataset_id = {dataset_id}")
                return dataset_id, 'database'
            print(f"[WARNING] dataset_id {dataset_id} not found in database; will try CSV fallback")
        except Exception as e:
            print(f"[WARNING] Django setup or DB lookup failed: {e}")
            print("         Will attempt CSV fallback")

    data_dir = REPO_ROOT / 'data'
    if data_dir.exists() and (data_dir / 'depots.csv').exists():
        print("[INFO] Using CSV files from data/ directory")
        return None, 'csv'

    print("[ERROR] No data source available!")
    print("        Check DATABASE_URL/USE_DATABASE in .env, or provide CSV files in data/.")
    sys.exit(1)


def cleanup_database_connection(_db_connection=None) -> None:
    """No-op kept for backward compatibility with older callers."""
    return None


# ---------------------------------------------------------------------------
# Subprocess-mode helpers — used when a run script is launched with
# `--experiment-id <id>` from the Django web layer.
# ---------------------------------------------------------------------------

def load_experiment_data(experiment_id: int):
    """Return ``(experiment, data)`` for a given experiment id.

    ``data`` is the dict produced by :class:`MDVRPDataLoader.load_from_database`,
    plus the precomputed distance/time matrices needed by the solvers.
    """
    setup_django()
    from src.data_loader import MDVRPDataLoader
    from src.distance_matrix import DistanceMatrixBuilder
    from runs.models import Experiment

    experiment = Experiment.objects.select_related('dataset').get(pk=experiment_id)

    loader = MDVRPDataLoader()
    data = loader.load_from_database(dataset_id=experiment.dataset_id)

    nodes = data['depots'] + data['customers']
    builder = DistanceMatrixBuilder(data['coordinates'], data['vehicle_speed'])
    full = builder.build_all_matrices(
        data['depots'], data['customers'], data['vehicles'], data['items'],
        data['coordinates'], data['vehicle_speed'],
        data['customer_orders'], data['item_weights'],
        data['vehicle_capacity'], data['max_operational_time'],
        data['customer_deadlines'], data['depot_for_vehicle']
    )
    # Convert NumPy matrices to dicts (solvers expect dict-style lookups)
    dist_arr = full['dist']
    dist_dict = {a: {b: float(dist_arr[i, j]) for j, b in enumerate(nodes)} for i, a in enumerate(nodes)}

    T_dict = {}
    for vehicle in data['vehicles']:
        time_arr = full['T'][vehicle]
        T_dict[vehicle] = {a: {b: float(time_arr[i, j]) for j, b in enumerate(nodes)} for i, a in enumerate(nodes)}

    full['dist'] = dist_dict
    full['T'] = T_dict
    data.update(full)
    return experiment, data


def make_progress_callback(experiment_id: int, every_n: int = 1):
    """Return a callback(current, total, message) that writes progress to the DB.

    ``every_n`` throttles writes to roughly once per N invocations to avoid
    hammering the DB on tight inner loops.
    """
    from src.experiment_tracker import ExperimentTracker

    tracker = ExperimentTracker()
    state = {'count': 0}

    def _callback(current, total, message=''):
        state['count'] += 1
        if every_n > 1 and state['count'] % every_n != 0 and current != total:
            return
        try:
            pct = int(round((current / total) * 100)) if total else 0
        except Exception:
            pct = 0

        best = None
        # Crude scrape: solver messages typically contain "Best: 123.45" or "best=123.45"
        for prefix in ('Best:', 'best:', 'best=', 'fitness='):
            if prefix in message:
                tail = message.split(prefix, 1)[1].strip()
                token = tail.split()[0].rstrip(',;')
                try:
                    best = float(token)
                except ValueError:
                    pass
                break

        tracker.update_progress(
            experiment_id=experiment_id,
            progress_pct=pct,
            best_objective=best,
            log_line=message or None,
        )

    return _callback


def finalize_experiment(
    experiment_id: int,
    solution: dict,
    status: str,
    depot_for_vehicle: dict,
    distance_lookup=None,
    time_lookup=None,
) -> None:
    """Persist the final routes and metrics for an experiment, then mark complete."""
    from src.experiment_tracker import ExperimentTracker

    tracker = ExperimentTracker()
    runtime = float(solution.get('runtime') or 0.0)
    tracker.save_result_metrics(experiment_id, {'runtime': runtime})

    routes = solution.get('routes') or {}
    tracker.save_routes(
        experiment_id,
        routes,
        depot_for_vehicle=depot_for_vehicle,
        distance_lookup=distance_lookup,
        time_lookup=time_lookup,
    )

    best_obj = solution.get('total_distance')
    if best_obj is None:
        best_obj = solution.get('fitness')
    if best_obj is None:
        best_obj = solution.get('objective')

    tracker.update_progress(
        experiment_id=experiment_id,
        status='completed',
        progress_pct=100,
        best_objective=best_obj,
        log_line=f'Solver finished with status={status}',
    )


def mark_failed(experiment_id: int, exc: BaseException) -> None:
    """Mark an experiment as failed with the exception summary appended to its log."""
    try:
        from src.experiment_tracker import ExperimentTracker
        ExperimentTracker().update_progress(
            experiment_id=experiment_id,
            status='failed',
            log_line=f'ERROR: {type(exc).__name__}: {exc}',
        )
    except Exception:
        pass
