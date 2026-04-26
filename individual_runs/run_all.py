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

# Import CSV-mode entry points from the individual run scripts
from individual_runs.run_greedy import run_csv as run_greedy_csv
from individual_runs.run_hga import run_csv as run_hga_csv
from individual_runs.run_milp import run_csv as run_milp_csv
from run_config import setup_data_source


def run_all_algorithms(data_dir=None, verbose=True):
    """Run all three algorithms sequentially from CSV files."""
    if data_dir is None:
        data_dir = os.path.join(parent_dir, 'data')

    print("\n" + "=" * 80)
    print("RUNNING ALL MDVRP ALGORITHMS")
    print("=" * 80)
    print(f"\nData directory: {data_dir}")
    print("Algorithms: Greedy, HGA, MILP")
    print()

    results = {}

    # 1. Greedy (fastest first)
    print("\n" + "-" * 80)
    print("1. RUNNING GREEDY ALGORITHM")
    print("-" * 80)
    try:
        start_time = time.time()
        solution, status = run_greedy_csv(data_dir, time_limit=60, seed=42, verbose=verbose)
        elapsed = time.time() - start_time
        results['greedy'] = {'solution': solution, 'status': status, 'runtime': elapsed}
        print(f"\n[OK] Greedy completed in {elapsed:.2f}s")
    except Exception as e:
        print(f"\n[ERROR] Greedy failed: {e}")
        results['greedy'] = {'error': str(e)}

    # 2. HGA
    print("\n" + "-" * 80)
    print("2. RUNNING HGA ALGORITHM")
    print("-" * 80)
    try:
        start_time = time.time()
        solution, status = run_hga_csv(data_dir, generations=50, population_size=50, time_limit=300, seed=42, verbose=verbose)
        elapsed = time.time() - start_time
        results['hga'] = {'solution': solution, 'status': status, 'runtime': elapsed}
        print(f"\n[OK] HGA completed in {elapsed:.2f}s")
    except Exception as e:
        print(f"\n[ERROR] HGA failed: {e}")
        results['hga'] = {'error': str(e)}

    # 3. MILP
    print("\n" + "-" * 80)
    print("3. RUNNING MILP ALGORITHM")
    print("-" * 80)
    try:
        start_time = time.time()
        solution, status = run_milp_csv(data_dir, time_limit=300, verbose=verbose)
        elapsed = time.time() - start_time
        results['milp'] = {'solution': solution, 'status': status, 'runtime': elapsed}
        print(f"\n[OK] MILP completed in {elapsed:.2f}s")
    except Exception as e:
        print(f"\n[ERROR] MILP failed: {e}")
        results['milp'] = {'error': str(e)}

    print_comparison_summary(results)
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


def main():
    parser = argparse.ArgumentParser(
        description='Run MDVRP algorithms from CSV files (standalone / non-web mode)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_all.py --all
  python run_all.py --algorithm greedy
  python run_all.py --all --data-dir /path/to/data
  python run_all.py --all --quiet
        """
    )
    parser.add_argument('--algorithm', '-a', choices=['greedy', 'hga', 'milp'],
                        help='Run a single algorithm')
    parser.add_argument('--all', action='store_true', help='Run all algorithms')
    parser.add_argument('--data-dir', '-d', default=None,
                        help='Path to CSV data directory (default: ../data)')
    parser.add_argument('--quiet', '-q', action='store_true', help='Reduce verbosity')
    args = parser.parse_args()

    verbose = not args.quiet
    data_dir = args.data_dir or os.path.join(parent_dir, 'data')
    solution = None

    if args.algorithm:
        algorithm = args.algorithm.lower()
        print(f"\nRunning {algorithm.upper()} algorithm...")
        try:
            if algorithm == 'greedy':
                solution, status = run_greedy_csv(data_dir, verbose=verbose)
            elif algorithm == 'hga':
                solution, status = run_hga_csv(data_dir, verbose=verbose)
            elif algorithm == 'milp':
                solution, status = run_milp_csv(data_dir, verbose=verbose)
            print(f"[OK] {algorithm.upper()} completed — status: {status}")
            if solution and 'fitness' in solution:
                print(f"     fitness: {solution['fitness']:.2f}")
        except Exception as e:
            print(f"[ERROR] {algorithm.upper()} failed: {e}")
    elif args.all:
        run_all_algorithms(data_dir=data_dir, verbose=verbose)
    else:
        parser.print_help()
        print("\nNo algorithm specified. Running all algorithms...")
        run_all_algorithms(data_dir=data_dir, verbose=verbose)


if __name__ == "__main__":
    main()
