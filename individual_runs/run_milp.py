"""
Individual Run Script for Mixed Integer Linear Programming (MILP)
MDVRP Solver using Gurobi optimizer
"""

import sys
import os
import time
import json
from pathlib import Path

# Setup path
parent_dir = str(Path(__file__).parent.parent)
sys.path.insert(0, parent_dir)

from algorithms.milp import MDVRP
from src.exporter import MDVRPExporter
from src.data_loader import MDVRPDataLoader
from run_config import setup_data_source, cleanup_database_connection


def run_milp(data_dir=None, time_limit=300, mip_gap=0.01, verbose=True, return_data=False,
             db_connection=None, dataset_id=None):
    """
    Run MILP algorithm for MDVRP problem using Gurobi.

    Parameters:
    -----------
    data_dir : str
        Path to data directory (default: ../data)
    time_limit : int
        Maximum runtime in seconds (default: 300)
    mip_gap : float
        MIP gap tolerance for Gurobi (default: 0.01)
    verbose : bool
        Print progress to console (default: True)
    db_connection : DatabaseConnection
        Database connection object (alternative to data_dir)
    dataset_id : int
        Dataset ID to load from database (required if db_connection provided)

    Returns:
    --------
    solution_dict : dict
        Solution containing routes, objective, metadata
    status : str
        Solution status ('optimal', 'feasible', 'timeout', 'infeasible', etc.)
    """

    # Set data directory
    if data_dir is None and db_connection is None:
        data_dir = os.path.join(parent_dir, 'data')

    if verbose:
        print("=" * 80)
        print("INDIVIDUAL RUN: MIXED INTEGER LINEAR PROGRAMMING (MILP)")
        print("=" * 80)
        print(f"\nConfiguration:")
        if db_connection:
            print(f"  Data source: Database (dataset_id: {dataset_id})")
        else:
            print(f"  Data directory: {data_dir}")
        print(f"  Time limit: {time_limit}s")
        print(f"  MIP gap: {mip_gap}")
        print()

    try:
        # Load data from database or CSV files
        if db_connection and dataset_id:
            loader = MDVRPDataLoader()
            data = loader.load_from_database(db_connection, dataset_id)
            # Initialize solver with pre-loaded data
            solver = MDVRP(
                depots=data['depots'], customers=data['customers'],
                vehicles=data['vehicles'], items=data['items'], params=data
            )
        else:
            # Initialize MILP solver with data source
            solver = MDVRP(
                depots=None, customers=None, vehicles=None, items=None, params=None,
                data_source=data_dir
            )

        # Build the optimization model
        if verbose:
            print("Building MILP model...")
        model = solver.build_model()

        # Solve the problem
        solution, status = solver.solve(time_limit=time_limit, mip_gap=mip_gap, verbose=verbose)

        # Add depot_for_vehicle to solution for consistency
        if solution:
            solution['depot_for_vehicle'] = solver.depot_for_vehicle

        # Print detailed results if verbose
        if verbose:
            print("\n" + "=" * 80)
            print("MILP SOLUTION SUMMARY")
            print("=" * 80)
            print(f"\nStatus: {status.upper()}")

            if solution and 'objective' in solution:
                print(f"Objective value (total distance): {solution['objective']:.2f}")
                print(f"Runtime: {solution['runtime']:.2f}s")

                print("\n" + "-" * 80)
                print("DETAILED ROUTES:")
                print("-" * 80)

                for vehicle, info in solution['routes'].items():
                    depot = solution['depot_for_vehicle'][vehicle]
                    route = info['nodes']
                    print(f"\nVehicle {vehicle} (from Depot {depot}):")
                    print(f"  Route: {depot} -> {' -> '.join(map(str, route))} -> {depot}" if route else f"  Route: {depot} -> {depot} (empty)")
                    print(f"  Customers: {route}")
                    print(f"  Distance: {info['distance']:.2f}")
                    print(f"  Time: {info['time']:.2f}")
                    print(f"  Load: {info['load']:.1f}")

        return (solution, status, solver.params) if return_data else (solution, status)

    except Exception as e:
        print(f"\n[ERROR] MILP execution failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return (None, 'error', None) if return_data else (None, 'error')


def save_solution(solution, status, problem_data=None, output_dir=None, time_limit=300, mip_gap=0.01):
    """Save solution to JSON, CSV, PDF, and GeoJSON files"""
    if output_dir is None:
        output_dir = os.path.join(parent_dir, 'output')

    os.makedirs(output_dir, exist_ok=True)

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    base_name = f"milp_solution_{timestamp}"

    # Save JSON solution
    json_filepath = os.path.join(output_dir, f"{base_name}.json")
    solution_copy = solution.copy()
    solution_copy.update({'status': status, 'algorithm': 'MILP', 'timestamp': timestamp})

    with open(json_filepath, 'w') as f:
        json.dump(solution_copy, f, indent=2, default=str)

    print(f"\n[INFO] JSON solution saved to: {json_filepath}")

    # Export to CSV, PDF, and GeoJSON
    if problem_data is not None:
        try:
            exporter = MDVRPExporter()
            created_files = exporter.export_all(
                solution=solution, problem_data=problem_data, output_dir=output_dir,
                base_name=base_name, algorithm_name='Mixed-Integer Linear Programming (MILP)',
                algorithm_params={'solver': 'Gurobi', 'time_limit': time_limit, 'optimality_gap': mip_gap}
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
        'time_limit': 300,
        'mip_gap': 0.01,
        'verbose': True,
        'return_data': True,
        'db_connection': db_connection,
        'dataset_id': dataset_id
    }

    # Run MILP
    print("\nStarting MILP solver...")
    solution, status, problem_data = run_milp(**config)

    # Save solution if successful
    if solution is not None:
        save_solution(solution, status, problem_data=problem_data, time_limit=config['time_limit'], mip_gap=config['mip_gap'])
        print("\n" + "=" * 80)
        print("MILP run completed successfully!")
        print("=" * 80)
    else:
        print("\n[ERROR] MILP run failed!")

    # Cleanup
    cleanup_database_connection(db_connection)
