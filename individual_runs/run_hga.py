"""Run the Hybrid Genetic Algorithm solver, either from CSV or as a tracked subprocess."""

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
    """Subprocess entry point — load the experiment, run HGA, persist results.

    Progress is written every 5 generations to limit DB write rate.
    """
    from algorithms.mdvrp_hga import MDVRPHGA
    from src.experiment_tracker import ExperimentTracker

    setup_django()
    tracker = ExperimentTracker()
    tracker.update_progress(
        experiment_id=experiment_id,
        status='running',
        progress_pct=0,
        log_line='Starting HGA solver',
    )

    try:
        experiment, data = load_experiment_data(experiment_id)
        callback = make_progress_callback(experiment_id, every_n=5)

        solver = MDVRPHGA(
            depots=data['depots'],
            customers=data['customers'],
            vehicles=data['vehicles'],
            items=data['items'],
            params=data,
            population_size=experiment.population_size or 50,
            generations=experiment.generations or 100,
            mutation_rate=experiment.mutation_rate or 0.2,
            crossover_rate=experiment.crossover_rate or 0.8,
            seed=experiment.seed or 42,
        )
        solution, status = solver.solve(
            time_limit=experiment.time_limit,
            progress_callback=callback,
            verbose=verbose,
        )

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
    except BaseException as exc:
        mark_failed(experiment_id, exc)
        if verbose:
            import traceback
            traceback.print_exc()
        return 1


def run_csv(data_dir, generations=50, population_size=50, time_limit=300, seed=42, verbose=True):
    from algorithms.mdvrp_hga import MDVRPHGA

    solver = MDVRPHGA(
        depots=None, customers=None, vehicles=None, items=None, params=None,
        data_source=str(data_dir),
        population_size=population_size, generations=generations, seed=seed,
    )
    return solver.solve(time_limit=time_limit, verbose=verbose)


def main():
    parser = argparse.ArgumentParser(description='Run HGA MDVRP solver')
    parser.add_argument('--experiment-id', type=int, default=None)
    parser.add_argument('--data-dir', type=str, default=None)
    parser.add_argument('--generations', type=int, default=50)
    parser.add_argument('--population-size', type=int, default=50)
    parser.add_argument('--time-limit', type=int, default=300)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--quiet', action='store_true')
    args = parser.parse_args()

    if args.experiment_id is not None:
        sys.exit(run_for_experiment(args.experiment_id, verbose=not args.quiet))

    data_dir = args.data_dir or os.path.join(REPO_ROOT, 'data')
    solution, status = run_csv(
        data_dir,
        generations=args.generations,
        population_size=args.population_size,
        time_limit=args.time_limit,
        seed=args.seed,
        verbose=not args.quiet,
    )
    print(f'Status: {status}')


if __name__ == '__main__':
    main()
