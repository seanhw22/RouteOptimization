"""Run the Greedy MDVRP solver, either from CSV files or as a tracked subprocess."""

import argparse
import os
import sys
from pathlib import Path

# Ensure repo root is importable
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from individual_runs.run_config import (  # noqa: E402
    finalize_experiment,
    load_experiment_data,
    make_progress_callback,
    mark_failed,
    setup_django,
)


def run_for_experiment(experiment_id: int, verbose: bool = True) -> int:
    """Subprocess entry point — load the experiment, run Greedy, persist results."""
    from algorithms.mdvrp_greedy import MDVRPGreedy
    from src.experiment_tracker import ExperimentTracker

    setup_django()
    tracker = ExperimentTracker()
    tracker.update_progress(
        experiment_id=experiment_id,
        status='running',
        progress_pct=0,
        log_line='Starting Greedy solver',
    )

    try:
        experiment, data = load_experiment_data(experiment_id)
        callback = make_progress_callback(experiment_id, every_n=1)

        solver = MDVRPGreedy(
            depots=data['depots'],
            customers=data['customers'],
            vehicles=data['vehicles'],
            items=data['items'],
            params=data,
            seed=experiment.seed or 42,
        )
        solution, status = solver.solve(progress_callback=callback, verbose=verbose)

        finalize_experiment(
            experiment_id=experiment_id,
            solution=solution,
            status=status,
            depot_for_vehicle=data['depot_for_vehicle'],
            distance_lookup=data['dist'],
            time_lookup=data['T'],
        )
        return 0
    except SystemExit:
        raise
    except BaseException as exc:  # noqa: BLE001 — propagate after recording
        mark_failed(experiment_id, exc)
        if verbose:
            import traceback
            traceback.print_exc()
        return 1


def run_csv(data_dir, time_limit=60, seed=42, verbose=True):
    """Backward-compatible CSV mode (no DB writes)."""
    from algorithms.mdvrp_greedy import MDVRPGreedy

    solver = MDVRPGreedy(
        depots=None, customers=None, vehicles=None, items=None, params=None,
        data_source=str(data_dir), seed=seed,
    )
    solution, status = solver.solve(time_limit=time_limit, verbose=verbose)
    return solution, status


def main():
    parser = argparse.ArgumentParser(description='Run Greedy MDVRP solver')
    parser.add_argument('--experiment-id', type=int, default=None,
                        help='Run as a tracked subprocess for this Experiment record')
    parser.add_argument('--data-dir', type=str, default=None,
                        help='CSV data directory (CSV mode)')
    parser.add_argument('--time-limit', type=int, default=60)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--quiet', action='store_true')
    args = parser.parse_args()

    if args.experiment_id is not None:
        sys.exit(run_for_experiment(args.experiment_id, verbose=not args.quiet))

    data_dir = args.data_dir or os.path.join(REPO_ROOT, 'data')
    solution, status = run_csv(data_dir, args.time_limit, args.seed, verbose=not args.quiet)
    print(f'Status: {status}')
    if solution and 'fitness' in solution:
        print(f"Total distance: {solution.get('total_distance', solution['fitness']):.2f}")


if __name__ == '__main__':
    main()
