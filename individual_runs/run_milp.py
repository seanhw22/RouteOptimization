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
from src.database import DatabaseConnection
from src.distance_cache import DistanceCache
from src.experiment_tracker import ExperimentTracker
from sqlalchemy import text
from run_config import setup_data_source, cleanup_database_connection


def run_milp(data_dir=None, time_limit=300, mip_gap=0.01, verbose=True, return_data=False,
             db_connection=None, dataset_id=None, use_cache=True, track_experiment=True):
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
        db_session = None
        experiment_id = None

        if db_connection and dataset_id:
            # Database mode
            db_session = db_connection.get_session()
            loader = MDVRPDataLoader()
            data = loader.load_from_database(db_connection, dataset_id)  # Fixed: pass db_connection, not db_session

            # Use distance cache if enabled
            if use_cache:
                cache = DistanceCache(db_session, dataset_id, data['coordinates'])
                if cache.is_valid():
                    if verbose:
                        print("[INFO] Loading distance matrix from cache...")
                    dist_matrix = cache.load()
                    # Add distance matrix to params
                    data['dist'] = dist_matrix
                else:
                    if verbose:
                        print("[INFO] Computing and caching distance matrix...")
                    # Build and cache distance matrix before solving
                    from src.distance_matrix import DistanceMatrixBuilder
                    builder = DistanceMatrixBuilder(data['coordinates'], data['vehicle_speed'])
                    nodes = data['depots'] + data['customers']
                    dist_matrix = builder.build_distance_matrix(nodes)
                    data['dist'] = dist_matrix
                    # Save to cache
                    cache.save(dist_matrix)
                    if verbose:
                        print("[INFO] Distance matrix cached for future runs")

            # Create experiment record if tracking enabled
            if track_experiment:
                tracker = ExperimentTracker(db_session)
                experiment_id = tracker.create_experiment({
                    'dataset_id': dataset_id,
                    'algorithm': 'MILP',
                    'seed': None  # MILP doesn't use seed
                })
                if verbose:
                    print(f"[INFO] Created experiment_id: {experiment_id}")

            # Initialize solver with pre-loaded data
            solver = MDVRP(
                depots=data['depots'], customers=data['customers'],
                vehicles=data['vehicles'], items=data['items'], params=data
            )
        else:
            # CSV mode
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

        # Save results to database if in database mode
        if db_connection and dataset_id and track_experiment and experiment_id and solution:
            try:
                tracker.save_result_metrics(experiment_id, {'runtime': solution['runtime']})
                if verbose:
                    print(f"[INFO] Saved result metrics to database (experiment_id: {experiment_id})")
            except Exception as e:
                print(f"[ERROR] Failed to save result metrics: {e}")
                import traceback
                traceback.print_exc()

            # Save routes properly (separate from result_metrics)
            try:
                if 'routes' in solution and solution['routes']:
                    for vehicle_id, route_info in solution['routes'].items():
                        nodes = route_info.get('nodes', [])

                        if not nodes:
                            # Empty route - depot to depot
                            depot = solution['depot_for_vehicle'][vehicle_id]
                            tracker.db_session.execute(text("""
                                INSERT INTO routes (experiment_id, vehicle_id, node_start_id, node_end_id, total_distance, travel_time)
                                VALUES (:exp_id, :vehicle, :start, :end, :dist, :time)
                            """), {
                                'exp_id': experiment_id,
                                'vehicle': vehicle_id,
                                'start': depot,
                                'end': depot,
                                'dist': 0.0,
                                'time': 0.0
                            })
                        else:
                            # Build route segments: depot → C1 → C2 → ... → depot
                            depot = solution['depot_for_vehicle'][vehicle_id]
                            all_nodes = [depot] + nodes + [depot]

                            for i in range(len(all_nodes) - 1):
                                tracker.db_session.execute(text("""
                                    INSERT INTO routes (experiment_id, vehicle_id, node_start_id, node_end_id, total_distance, travel_time)
                                    VALUES (:exp_id, :vehicle, :start, :end, :dist, :time)
                                """), {
                                    'exp_id': experiment_id,
                                    'vehicle': vehicle_id,
                                    'start': all_nodes[i],
                                    'end': all_nodes[i + 1],
                                    'dist': float(route_info.get('distance', 0.0) / (len(all_nodes) - 1) if len(all_nodes) > 1 else 0.0),
                                    'time': float(route_info.get('time', 0.0) / (len(all_nodes) - 1) if len(all_nodes) > 1 else 0.0)
                                })

                    tracker.db_session.commit()
                    if verbose:
                        print(f"[INFO] Saved routes to database (experiment_id: {experiment_id})")
            except Exception as e:
                print(f"[ERROR] Failed to save routes: {e}")
                import traceback
                traceback.print_exc()
                tracker.db_session.rollback()

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
    import argparse

    parser = argparse.ArgumentParser(
        description='Run Mixed-Integer Linear Programming (MILP) solver for MDVRP',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with CSV files (default)
  python run_milp.py

  # Run with database
  python run_milp.py --dataset 1

  # Run with custom parameters
  python run_milp.py --dataset 1 --time-limit 600 --mip-gap 0.005
        """
    )

    parser.add_argument('--dataset', '-d', type=int,
                       help='Dataset ID to load from database')
    parser.add_argument('--db-url', type=str,
                       help='Database URL (overrides DATABASE_URL)')
    parser.add_argument('--time-limit', '-t', type=int, default=300,
                       help='Time limit in seconds (default: 300)')
    parser.add_argument('--mip-gap', '-m', type=float, default=0.01,
                       help='MIP optimality gap (default: 0.01)')
    parser.add_argument('--quiet', '-q', action='store_true',
                       help='Reduce verbosity')

    args = parser.parse_args()

    # Setup data source
    if args.dataset:
        # Database mode requested
        db_url = args.db_url
        db_connection = DatabaseConnection(db_url) if db_url else DatabaseConnection()

        # Validate dataset exists
        if not db_connection.dataset_exists(args.dataset):
            print(f"[ERROR] Dataset {args.dataset} not found in database")
            print(f"        Please check the dataset_id or populate the database first")
            exit(1)

        dataset_id = args.dataset
        source_type = 'database'
        print(f"[INFO] Using database: dataset_id = {dataset_id}")
    else:
        # Use environment-based setup or CSV fallback
        db_connection, dataset_id, source_type = setup_data_source()

    # Configuration
    config = {
        'time_limit': args.time_limit,
        'mip_gap': args.mip_gap,
        'verbose': not args.quiet,
        'return_data': True,
        'db_connection': db_connection,
        'dataset_id': dataset_id,
        'use_cache': True,
        'track_experiment': True
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
