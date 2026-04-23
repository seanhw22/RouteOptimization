"""
Individual Run Script for Hybrid Genetic Algorithm (HGA)
MDVRP Solver using DEAP framework with NumPy optimization
"""

import sys
import os
import time
import json
from pathlib import Path

# Setup path
parent_dir = str(Path(__file__).parent.parent)
sys.path.insert(0, parent_dir)

from algorithms.mdvrp_hga import MDVRPHGA
from src.exporter import MDVRPExporter
from src.data_loader import MDVRPDataLoader
from run_config import setup_data_source, cleanup_database_connection


def run_hga(data_dir=None, generations=50, population_size=50, time_limit=300,
            seed=42, verbose=True, return_data=False, db_connection=None, dataset_id=None):
    """
    Run HGA algorithm for MDVRP problem.

    Parameters:
    -----------
    data_dir : str
        Path to data directory (default: ../data)
    generations : int
        Number of generations (default: 50)
    population_size : int
        GA population size (default: 50)
    time_limit : int
        Maximum runtime in seconds (default: 300)
    seed : int
        Random seed for reproducibility (default: 42)
    verbose : bool
        Print progress to console (default: True)
    db_connection : DatabaseConnection
        Database connection object (alternative to data_dir)
    dataset_id : int
        Dataset ID to load from database (required if db_connection provided)

    Returns:
    --------
    solution_dict : dict
        Solution containing routes, fitness, metadata
    status : str
        Solution status ('feasible', 'timeout', etc.)
    """

    # Set data directory
    if data_dir is None and db_connection is None:
        data_dir = os.path.join(parent_dir, 'data')

    if verbose:
        print("=" * 80)
        print("INDIVIDUAL RUN: HYBRID GENETIC ALGORITHM (HGA)")
        print("=" * 80)
        print(f"\nConfiguration:")
        if db_connection:
            print(f"  Data source: Database (dataset_id: {dataset_id})")
        else:
            print(f"  Data directory: {data_dir}")
        print(f"  Generations: {generations}")
        print(f"  Population size: {population_size}")
        print(f"  Time limit: {time_limit}s")
        print(f"  Random seed: {seed}")
        print()

    try:
        # Load data from database or CSV files
        if db_connection and dataset_id:
            loader = MDVRPDataLoader()
            data = loader.load_from_database(db_connection, dataset_id)
            # Initialize solver with pre-loaded data
            solver = MDVRPHGA(
                depots=data['depots'], customers=data['customers'],
                vehicles=data['vehicles'], items=data['items'], params=data,
                population_size=population_size, generations=generations,
                elite_size=3, mutation_rate=0.2, crossover_rate=0.8,
                tournament_size=3, seed=seed
            )
        else:
            # Initialize HGA solver with data source
            solver = MDVRPHGA(
                depots=None, customers=None, vehicles=None, items=None, params=None,
                data_source=data_dir, population_size=population_size,
                generations=generations, elite_size=3, mutation_rate=0.2,
                crossover_rate=0.8, tournament_size=3, seed=seed
            )

        # Solve the problem
        solution, status = solver.solve(time_limit=time_limit, verbose=verbose)

        # Print detailed results if verbose
        if verbose:
            print("\n" + "=" * 80)
            print("HGA SOLUTION SUMMARY")
            print("=" * 80)
            print(f"\nStatus: {status.upper()}")
            print(f"Fitness (distance + penalty): {solution['fitness']:.2f}")
            print(f"Total distance: {solution['total_distance']:.2f}")
            print(f"Total penalty: {solution['penalty']:.2f}")
            print(f"Runtime: {solution['runtime']:.2f}s")
            print(f"Generations completed: {solution['generations']}")

            print("\n" + "-" * 80)
            print("DETAILED ROUTES:")
            print("-" * 80)

            for vehicle, info in solution['routes'].items():
                depot = solution['depot_for_vehicle'][vehicle]
                route = info['nodes']
                clean_route = [c for c in route if c is not None]
                print(f"\nVehicle {vehicle} (from Depot {depot}):")
                route_str = ' -> '.join(map(str, clean_route)) if clean_route else str(depot)
                print(f"  Route: {depot} -> {route_str} -> {depot}")
                print(f"  Customers: {clean_route}")
                print(f"  Distance: {info['distance']:.2f}")
                print(f"  Time: {info['time']:.2f}")
                print(f"  Load: {info['load']:.1f}")

        return (solution, status, solver) if return_data else (solution, status, None)

    except Exception as e:
        print(f"\n[ERROR] HGA execution failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return (None, 'error', None) if return_data else (None, 'error', None)


def save_solution(solution, status, problem_data=None, output_dir=None, solver=None):
    """Save solution to JSON, CSV, PDF, and GeoJSON files"""
    if output_dir is None:
        output_dir = os.path.join(parent_dir, 'output')

    os.makedirs(output_dir, exist_ok=True)

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    base_name = f"hga_solution_{timestamp}"

    # Save JSON solution
    json_filepath = os.path.join(output_dir, f"{base_name}.json")
    solution_copy = solution.copy()
    solution_copy.update({'status': status, 'algorithm': 'HGA', 'timestamp': timestamp})

    with open(json_filepath, 'w') as f:
        json.dump(solution_copy, f, indent=2, default=str)

    print(f"\n[INFO] JSON solution saved to: {json_filepath}")

    # Export to CSV, PDF, and GeoJSON
    if problem_data is not None:
        try:
            exporter = MDVRPExporter()
            created_files = exporter.export_all(
                solution=solution, problem_data=problem_data, output_dir=output_dir,
                base_name=base_name, algorithm_name='Hybrid Genetic Algorithm',
                algorithm_params={
                    'population_size': solver.population_size if solver and hasattr(solver, 'population_size') else 50,
                    'generations': solver.generations if solver and hasattr(solver, 'generations') else 50,
                    'random_seed': solver.seed if solver and hasattr(solver, 'seed') else 42
                }
            )
            print(f"[INFO] Exported files:")
            for file_path in created_files:
                print(f"  - {file_path}")
        except Exception as e:
            print(f"[WARNING] Failed to export to CSV/PDF/GeoJSON: {str(e)}")
    else:
        print("[WARNING] No problem data provided, skipping CSV/PDF/GeoJSON export")

    return json_filepath


if __name__ == "__main__":
    # Setup data source (database → CSV fallback)
    db_connection, dataset_id, source_type = setup_data_source()

    # Configuration
    config = {
        'generations': 50,
        'population_size': 50,
        'time_limit': 300,
        'seed': 42,
        'verbose': True,
        'return_data': True,
        'db_connection': db_connection,
        'dataset_id': dataset_id
    }

    # Run HGA
    print("\nStarting HGA solver...")
    solution, status, solver = run_hga(**config)

    # Save solution if successful
    if solution is not None:
        problem_data = solver.params if solver else None
        save_solution(solution, status, problem_data=problem_data, solver=solver)
        print("\n" + "=" * 80)
        print("HGA run completed successfully!")
        print("=" * 80)
    else:
        print("\n[ERROR] HGA run failed!")

    # Cleanup
    cleanup_database_connection(db_connection)
