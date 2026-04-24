"""
Master Script to Run Individual MDVRP Algorithms
Run all algorithms or specific ones with unified interface
"""

import sys
import os
import time
import argparse
from pathlib import Path

# Setup path
parent_dir = str(Path(__file__).parent.parent)
sys.path.insert(0, parent_dir)

# Import individual run scripts
from individual_runs.run_hga import run_hga, save_solution as save_hga_solution
from individual_runs.run_greedy import run_greedy, save_solution as save_greedy_solution
from individual_runs.run_milp import run_milp, save_solution as save_milp_solution
from run_config import setup_data_source, cleanup_database_connection


def run_all_algorithms(data_dir=None, verbose=True, db_connection=None, dataset_id=None):
    """Run all three algorithms sequentially"""

    if data_dir is None and db_connection is None:
        data_dir = os.path.join(parent_dir, 'data')

    print("\n" + "=" * 80)
    print("RUNNING ALL MDVRP ALGORITHMS")
    print("=" * 80)
    if db_connection:
        print(f"\nData source: Database (dataset_id: {dataset_id})")
    else:
        print(f"\nData directory: {data_dir}")
    print(f"Algorithms: Greedy, HGA, MILP")
    print()

    results = {}
    common_kwargs = {'data_dir': data_dir, 'verbose': verbose, 'return_data': True,
                     'db_connection': db_connection, 'dataset_id': dataset_id}

    # 1. Run Greedy (fastest first)
    print("\n" + "-" * 80)
    print("1. RUNNING GREEDY ALGORITHM")
    print("-" * 80)
    try:
        start_time = time.time()
        greedy_solution, greedy_status, greedy_data = run_greedy(
            time_limit=60, seed=42, **common_kwargs
        )
        elapsed = time.time() - start_time
        results['greedy'] = {'solution': greedy_solution, 'status': greedy_status,
                             'runtime': elapsed, 'problem_data': greedy_data}
        print(f"\n[OK] Greedy completed in {elapsed:.2f}s")
    except Exception as e:
        print(f"\n[ERROR] Greedy failed: {str(e)}")
        results['greedy'] = {'error': str(e)}

    # 2. Run HGA
    print("\n" + "-" * 80)
    print("2. RUNNING HGA ALGORITHM")
    print("-" * 80)
    try:
        start_time = time.time()
        hga_solution, hga_status, hga_data = run_hga(
            generations=50, population_size=50, time_limit=300, seed=42, **common_kwargs
        )
        elapsed = time.time() - start_time
        results['hga'] = {'solution': hga_solution, 'status': hga_status,
                          'runtime': elapsed, 'problem_data': hga_data.params if hga_data else None,
                          'solver': hga_data}
        print(f"\n[OK] HGA completed in {elapsed:.2f}s")
    except Exception as e:
        print(f"\n[ERROR] HGA failed: {str(e)}")
        results['hga'] = {'error': str(e)}

    # 3. Run MILP
    print("\n" + "-" * 80)
    print("3. RUNNING MILP ALGORITHM")
    print("-" * 80)
    try:
        start_time = time.time()
        milp_solution, milp_status, milp_data = run_milp(
            time_limit=300, mip_gap=0.01, **common_kwargs
        )
        elapsed = time.time() - start_time
        results['milp'] = {'solution': milp_solution, 'status': milp_status,
                           'runtime': elapsed, 'problem_data': milp_data}
        print(f"\n[OK] MILP completed in {elapsed:.2f}s")
    except Exception as e:
        print(f"\n[ERROR] MILP failed: {str(e)}")
        results['milp'] = {'error': str(e)}

    # Print comparison summary
    print_comparison_summary(results)

    # Export all solutions
    export_all_solutions(results)

    return results


def print_comparison_summary(results):
    """Print comparison summary of all algorithms"""
    print("\n" + "=" * 80)
    print("ALGORITHM COMPARISON SUMMARY")
    print("=" * 80)

    for alg, result in results.items():
        if 'error' in result:
            print(f"\n{alg.upper()}: FAILED")
            print(f"  Error: {result['error']}")
        elif result['solution']:
            sol = result['solution']
            print(f"\n{alg.upper()}: {result['status'].upper()}")
            print(f"  Runtime: {result['runtime']:.2f}s")

            if 'fitness' in sol:
                print(f"  Fitness: {sol['fitness']:.2f}")
            elif 'objective' in sol:
                print(f"  Objective: {sol['objective']:.2f}")

            if 'total_distance' in sol:
                print(f"  Total Distance: {sol['total_distance']:.2f}")

    print("\n" + "=" * 80)


def export_all_solutions(results):
    """Export all solutions to CSV, PDF, and GeoJSON"""
    print("\n" + "=" * 80)
    print("EXPORTING SOLUTIONS TO MULTIPLE FORMATS")
    print("=" * 80)

    output_dir = os.path.join(parent_dir, 'output')
    os.makedirs(output_dir, exist_ok=True)

    for alg, result in results.items():
        if 'error' not in result and result['solution']:
            solution = result['solution']
            status = result['status']
            problem_data = result['problem_data']

            print(f"\nExporting {alg.upper()} solution...")

            if alg == 'greedy':
                save_greedy_solution(solution, status, problem_data=problem_data, output_dir=output_dir)
            elif alg == 'hga':
                save_hga_solution(solution, status, problem_data=problem_data, output_dir=output_dir, solver=result.get('solver'))
            elif alg == 'milp':
                save_milp_solution(solution, status, problem_data=problem_data, output_dir=output_dir)


def main():
    parser = argparse.ArgumentParser(
        description='Run MDVRP algorithms individually or all together',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all algorithms
  python run_all.py --all

  # Run specific algorithm
  python run_all.py --algorithm greedy
  python run_all.py --algorithm hga
  python run_all.py --algorithm milp

  # Run with custom data directory
  python run_all.py --all --data-dir /path/to/data

  # Run with database
  python run_all.py --all --dataset 1

  # Run with custom database URL
  python run_all.py --all --dataset 1 --db-url postgresql://user:pass@localhost:5432/mdvrp

  # Run specific algorithm with database
  python run_all.py --algorithm hga --dataset 2

  # Run without verbose output
  python run_all.py --all --quiet
        """
    )

    parser.add_argument('--algorithm', '-a', choices=['greedy', 'hga', 'milp'],
                       help='Run specific algorithm (default: run all)')
    parser.add_argument('--all', action='store_true', help='Run all algorithms')
    parser.add_argument('--data-dir', '-d', default=None, help='Path to data directory (default: ../data)')
    parser.add_argument('--dataset', '-ds', type=int, help='Dataset ID to load from database')
    parser.add_argument('--db-url', type=str, help='Database URL (overrides DATABASE_URL)')
    parser.add_argument('--quiet', '-q', action='store_true', help='Reduce verbosity')

    args = parser.parse_args()

    # Set verbosity
    verbose = not args.quiet

    # Setup data source
    from src.database import DatabaseConnection
    from run_config import load_env_config, setup_data_source
    db_connection, dataset_id, data_dir = None, None, None

    if args.dataset:
        # Explicit database mode from command line
        db_url = args.db_url
        db_connection = DatabaseConnection(db_url) if db_url else DatabaseConnection()

        # Validate dataset exists
        if not db_connection.dataset_exists(args.dataset):
            print(f"[ERROR] Dataset {args.dataset} not found in database")
            print(f"        Please check the dataset_id or populate the database first")
            exit(1)

        dataset_id = args.dataset
        print(f"[INFO] Using database: dataset_id = {dataset_id}")
    elif args.data_dir:
        # Explicit CSV mode from command line
        data_dir = args.data_dir
    else:
        # Auto-detect with fallback (database → CSV)
        db_connection, dataset_id, source_type = setup_data_source()
        if source_type == 'csv':
            data_dir = os.path.join(parent_dir, 'data')

    # Run algorithms
    if args.algorithm:
        # Run single algorithm
        algorithm = args.algorithm.lower()

        if algorithm == 'greedy':
            print("\nRunning Greedy algorithm...")
            solution, status, problem_data = run_greedy(
                data_dir=data_dir, time_limit=60, seed=42, verbose=verbose,
                return_data=True, db_connection=db_connection, dataset_id=dataset_id
            )
            if solution:
                output_dir = os.path.join(parent_dir, 'output')
                save_greedy_solution(solution, status, problem_data=problem_data, output_dir=output_dir)
        elif algorithm == 'hga':
            print("\nRunning HGA algorithm...")
            solution, status, problem_data = run_hga(
                data_dir=data_dir, generations=50, population_size=50, time_limit=300,
                seed=42, verbose=verbose, return_data=True, db_connection=db_connection, dataset_id=dataset_id
            )
            if solution:
                output_dir = os.path.join(parent_dir, 'output')
                save_hga_solution(solution, status, problem_data=problem_data, output_dir=output_dir)
        elif algorithm == 'milp':
            print("\nRunning MILP algorithm...")
            solution, status, problem_data = run_milp(
                data_dir=data_dir, time_limit=300, mip_gap=0.01, verbose=verbose,
                return_data=True, db_connection=db_connection, dataset_id=dataset_id
            )
            if solution:
                output_dir = os.path.join(parent_dir, 'output')
                save_milp_solution(solution, status, problem_data=problem_data, output_dir=output_dir)

        if solution:
            print(f"\n[OK] {algorithm.upper()} completed successfully!")
        else:
            print(f"\n[ERROR] {algorithm.upper()} failed!")

    elif args.all:
        # Run all algorithms
        run_all_algorithms(data_dir=data_dir, verbose=verbose, db_connection=db_connection, dataset_id=dataset_id)
    else:
        # Default: run all
        parser.print_help()
        print("\nNo algorithm specified. Running all algorithms...")
        run_all_algorithms(data_dir=data_dir, verbose=verbose, db_connection=db_connection, dataset_id=dataset_id)

    # Cleanup
    cleanup_database_connection(db_connection)


if __name__ == "__main__":
    main()
