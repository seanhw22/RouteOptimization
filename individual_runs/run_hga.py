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
from src.database import DatabaseConnection
from src.distance_cache import DistanceCache
from src.experiment_tracker import ExperimentTracker
from sqlalchemy import text
from run_config import setup_data_source, cleanup_database_connection


def run_hga(data_dir=None, generations=50, population_size=50, time_limit=300,
            seed=42, verbose=True, return_data=False, db_connection=None, dataset_id=None,
            use_cache=True, track_experiment=True):
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
                    # Convert NumPy array to dict format (solver compatibility)
                    nodes = data['depots'] + data['customers']
                    dist_dict = {}
                    for i, node_i in enumerate(nodes):
                        dist_dict[node_i] = {}
                        for j, node_j in enumerate(nodes):
                            dist_dict[node_i][node_j] = float(dist_matrix[i][j])
                    data['dist'] = dist_dict
                    # Build time matrices from cached distance matrix
                    from src.distance_matrix import DistanceMatrixBuilder
                    builder = DistanceMatrixBuilder(data['coordinates'], data['vehicle_speed'])
                    time_matrices = builder.build_time_matrices(nodes, data['vehicles'], dist_matrix)
                    # Convert time matrices to dict format
                    T_dict = {}
                    for vehicle in data['vehicles']:
                        T_dict[vehicle] = {}
                        time_matrix = time_matrices[vehicle]
                        for i, node_i in enumerate(nodes):
                            T_dict[vehicle][node_i] = {}
                            for j, node_j in enumerate(nodes):
                                T_dict[vehicle][node_i][node_j] = float(time_matrix[i][j])
                    data['T'] = T_dict
                    if verbose:
                        print("[INFO] Loaded distance and time matrices from cache")
                else:
                    if verbose:
                        print("[INFO] Computing and caching distance matrix...")
                    # Build and cache distance matrix
                    from src.distance_matrix import DistanceMatrixBuilder
                    builder = DistanceMatrixBuilder(data['coordinates'], data['vehicle_speed'])
                    nodes = data['depots'] + data['customers']
                    dist_matrix = builder.build_distance_matrix(nodes)
                    cache.save(dist_matrix)
                    if verbose:
                        print("[INFO] Distance matrix cached for future runs")

            # Create experiment record if tracking enabled
            if track_experiment:
                tracker = ExperimentTracker(db_session)
                experiment_id = tracker.create_experiment({
                    'dataset_id': dataset_id,
                    'algorithm': 'HGA',
                    'population_size': population_size,
                    'mutation_rate': 0.2,
                    'crossover_rate': 0.8,
                    'seed': seed
                })
                if verbose:
                    print(f"[INFO] Created experiment_id: {experiment_id}")

            # Initialize solver with pre-loaded data
            solver = MDVRPHGA(
                depots=data['depots'], customers=data['customers'],
                vehicles=data['vehicles'], items=data['items'], params=data,
                population_size=population_size, generations=generations,
                elite_size=3, mutation_rate=0.2, crossover_rate=0.8,
                tournament_size=3, seed=seed
            )
        else:
            # CSV mode
            solver = MDVRPHGA(
                depots=None, customers=None, vehicles=None, items=None, params=None,
                data_source=data_dir, population_size=population_size,
                generations=generations, elite_size=3, mutation_rate=0.2,
                crossover_rate=0.8, tournament_size=3, seed=seed
            )

        # Solve the problem
        solution, status = solver.solve(time_limit=time_limit, verbose=verbose)

        # Save results to database if in database mode
        if db_connection and dataset_id and track_experiment and experiment_id:
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
                        # Filter out None values
                        nodes = [n for n in nodes if n is not None]

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
    import argparse

    parser = argparse.ArgumentParser(
        description='Run Hybrid Genetic Algorithm (HGA) for MDVRP',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with CSV files (default)
  python run_hga.py

  # Run with database
  python run_hga.py --dataset 1

  # Run with custom parameters
  python run_hga.py --dataset 1 --generations 100 --population-size 100
        """
    )

    parser.add_argument('--dataset', '-d', type=int,
                       help='Dataset ID to load from database')
    parser.add_argument('--db-url', type=str,
                       help='Database URL (overrides DATABASE_URL)')
    parser.add_argument('--generations', '-g', type=int, default=50,
                       help='Number of generations (default: 50)')
    parser.add_argument('--population-size', '-p', type=int, default=50,
                       help='Population size (default: 50)')
    parser.add_argument('--time-limit', '-t', type=int, default=300,
                       help='Time limit in seconds (default: 300)')
    parser.add_argument('--seed', '-s', type=int, default=42,
                       help='Random seed (default: 42)')
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
        'generations': args.generations,
        'population_size': args.population_size,
        'time_limit': args.time_limit,
        'seed': args.seed,
        'verbose': not args.quiet,
        'return_data': True,
        'db_connection': db_connection,
        'dataset_id': dataset_id,
        'use_cache': True,
        'track_experiment': True
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
