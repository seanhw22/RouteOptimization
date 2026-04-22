"""
Individual Run Script for Hybrid Genetic Algorithm (HGA)
MDVRP Solver using DEAP framework with NumPy optimization
"""

import sys
import os
import time
import json
from pathlib import Path

# Add parent directory to path to import modules
parent_dir = str(Path(__file__).parent.parent)
sys.path.insert(0, parent_dir)

from algorithms.mdvrp_hga import MDVRPHGA
from src.exporter import MDVRPExporter

def run_hga(data_dir=None, generations=50, population_size=50,
           time_limit=300, seed=42, verbose=True, return_data=False):
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

    Returns:
    --------
    solution_dict : dict
        Solution containing routes, fitness, metadata
    status : str
        Solution status ('feasible', 'timeout', etc.)
    """

    # Set data directory
    if data_dir is None:
        data_dir = os.path.join(parent_dir, 'data')

    if verbose:
        print("=" * 80)
        print("INDIVIDUAL RUN: HYBRID GENETIC ALGORITHM (HGA)")
        print("=" * 80)
        print(f"\nConfiguration:")
        print(f"  Data directory: {data_dir}")
        print(f"  Generations: {generations}")
        print(f"  Population size: {population_size}")
        print(f"  Time limit: {time_limit}s")
        print(f"  Random seed: {seed}")
        print()

    try:
        # Initialize HGA solver with data source
        solver = MDVRPHGA(
            depots=None,  # Will be loaded from data
            customers=None,  # Will be loaded from data
            vehicles=None,  # Will be loaded from data
            items=None,  # Will be loaded from data
            params=None,  # Will be loaded from data
            data_source=data_dir,
            population_size=population_size,
            generations=generations,
            elite_size=3,
            mutation_rate=0.2,
            crossover_rate=0.8,
            tournament_size=3,
            seed=seed
        )

        # Solve the problem
        solution, status = solver.solve(
            time_limit=time_limit,
            verbose=verbose
        )

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
                # Filter out None values from route for display
                clean_route = [c for c in route if c is not None]
                print(f"\nVehicle {vehicle} (from Depot {depot}):")
                print(f"  Route: {depot} -> {' -> '.join(clean_route) if clean_route else depot} -> {depot}" if clean_route else f"  Route: {depot} -> {depot} (empty)")
                print(f"  Customers: {clean_route}")
                print(f"  Distance: {info['distance']:.2f}")
                print(f"  Time: {info['time']:.2f}")
                print(f"  Load: {info['load']:.1f}")

        if return_data:
            return solution, status, solver.params
        else:
            return solution, status

    except Exception as e:
        print(f"\n[ERROR] HGA execution failed: {str(e)}")
        import traceback
        traceback.print_exc()
        if return_data:
            return None, 'error', None
        else:
            return None, 'error'

def save_solution(solution, status, problem_data=None, output_dir=None):
    """Save solution to JSON, CSV, PDF, and GeoJSON files"""
    if output_dir is None:
        output_dir = os.path.join(parent_dir, 'output')

    os.makedirs(output_dir, exist_ok=True)

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    base_name = f"hga_solution_{timestamp}"

    # Save JSON solution
    json_filename = f"{base_name}.json"
    json_filepath = os.path.join(output_dir, json_filename)

    # Convert solution to JSON-serializable format
    solution_copy = solution.copy()
    solution_copy['status'] = status
    solution_copy['algorithm'] = 'HGA'
    solution_copy['timestamp'] = timestamp

    with open(json_filepath, 'w') as f:
        json.dump(solution_copy, f, indent=2, default=str)

    print(f"\n[INFO] JSON solution saved to: {json_filepath}")

    # Export to CSV, PDF, and GeoJSON if problem_data is available
    if problem_data is not None:
        try:
            exporter = MDVRPExporter()

            # Export to all formats
            created_files = exporter.export_all(
                solution=solution,
                problem_data=problem_data,
                output_dir=output_dir,
                base_name=base_name,
                algorithm_name='Hybrid Genetic Algorithm',
                algorithm_params={
                    'population_size': solver.population_size if hasattr(solver, 'population_size') else 50,
                    'generations': solver.generations if hasattr(solver, 'generations') else 50,
                    'random_seed': solver.seed if hasattr(solver, 'seed') else 42
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
    # Configuration
    config = {
        'data_dir': os.path.join(parent_dir, 'data'),
        'generations': 50,
        'population_size': 50,
        'time_limit': 300,
        'seed': 42,
        'verbose': True,
        'return_data': True  # Return problem data for export
    }

    # Run HGA
    print("\nStarting HGA solver...")
    solution, status, problem_data = run_hga(**config)

    # Save solution if successful
    if solution is not None:
        save_solution(solution, status, problem_data=problem_data)
        print("\n" + "=" * 80)
        print("HGA run completed successfully!")
        print("=" * 80)
    else:
        print("\n[ERROR] HGA run failed!")