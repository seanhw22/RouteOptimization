"""Run the MILP (Gurobi) solver, either from CSV or as a tracked subprocess."""

import argparse
import os
import sys
from pathlib import Path

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
    """Subprocess entry point — load the experiment, run MILP, persist results."""
    from algorithms.milp import MDVRP
    from src.experiment_tracker import ExperimentTracker

    setup_django()
    tracker = ExperimentTracker()
    tracker.update_progress(
        experiment_id=experiment_id,
        status='running',
        progress_pct=0,
        log_line='Starting MILP solver',
    )

    try:
        experiment, data = load_experiment_data(experiment_id)
        callback = make_progress_callback(experiment_id, every_n=1)

        solver = MDVRP(
            depots=data['depots'],
            customers=data['customers'],
            vehicles=data['vehicles'],
            items=data['items'],
            params=data,
        )
        solver.build_model()
        time_limit = experiment.time_limit or 3600
        solution, status = solver.solve(
            time_limit=time_limit,
            mip_gap=0.01,
            progress_callback=callback,
            verbose=verbose,
        )
        if solution is not None:
            solution.setdefault('depot_for_vehicle', solver.depot_for_vehicle)

        finalize_experiment(
            experiment_id=experiment_id,
            solution=solution or {'routes': {}, 'runtime': 0.0},
            status=status,
            depot_for_vehicle=data['depot_for_vehicle'],
            distance_lookup=data['dist'],
            time_lookup=data['T'],
        )
        return 0
    except SystemExit:
        raise
    except BaseException as exc:
        mark_failed(experiment_id, exc)
        if verbose:
            import traceback
            traceback.print_exc()
        return 1


def run_csv(data_dir, time_limit=300, verbose=True):
    from algorithms.milp import MDVRP

    solver = MDVRP(
        depots=None, customers=None, vehicles=None, items=None, params=None,
        data_source=str(data_dir),
    )
    solver.build_model()
    return solver.solve(time_limit=time_limit, verbose=verbose)


def main():
    parser = argparse.ArgumentParser(description='Run MILP MDVRP solver')
    parser.add_argument('--experiment-id', type=int, default=None)
    parser.add_argument('--data-dir', type=str, default=None)
    parser.add_argument('--time-limit', type=int, default=300)
    parser.add_argument('--quiet', action='store_true')
    args = parser.parse_args()

    if args.experiment_id is not None:
        sys.exit(run_for_experiment(args.experiment_id, verbose=not args.quiet))

    data_dir = args.data_dir or os.path.join(REPO_ROOT, 'data')
    solution, status = run_csv(data_dir, args.time_limit, verbose=not args.quiet)
    print(f'Status: {status}')


if __name__ == '__main__':
    main()
