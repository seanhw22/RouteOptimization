"""
Export Experiment Results from Database
Exports PDF, GeoJSON, and CSV files for a specific experiment
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
parent_dir = str(Path(__file__).parent.parent)
sys.path.insert(0, parent_dir)

from src.database import DatabaseConnection
from src.exporter import MDVRPExporter
from src.data_loader import MDVRPDataLoader
from sqlalchemy import text


def load_experiment_from_db(db_connection, experiment_id: int) -> dict:
    """
    Load experiment and reconstruct solution from database.

    Args:
        db_connection: DatabaseConnection object
        experiment_id: Experiment ID to export

    Returns:
        Tuple of (solution_dict, problem_data_dict)
    """
    session = db_connection.get_session()

    try:
        # Load experiment metadata
        exp_result = session.execute(text("""
            SELECT experiment_id, dataset_id, algorithm, population_size,
                   mutation_rate, crossover_rate, seed
            FROM experiments
            WHERE experiment_id = :exp_id
        """), {'exp_id': experiment_id}).fetchone()

        if not exp_result:
            raise ValueError(f"Experiment {experiment_id} not found")

        experiment_id, dataset_id, algorithm, pop_size, mut_rate, cross_rate, seed = exp_result

        print(f"[INFO] Loading experiment {experiment_id}")
        print(f"  Dataset: {dataset_id}")
        print(f"  Algorithm: {algorithm}")

        # Load dataset (problem data)
        loader = MDVRPDataLoader()
        problem_data = loader.load_from_database(db_connection, dataset_id)

        # Load result metrics
        metrics_result = session.execute(text("""
            SELECT runtime_id
            FROM result_metrics
            WHERE experiment_id = :exp_id
        """), {'exp_id': experiment_id}).fetchone()

        runtime = float(metrics_result[0]) if metrics_result else 0.0

        # Load routes and reconstruct solution
        routes_result = session.execute(text("""
            SELECT vehicle_id, node_start_id, node_end_id, total_distance, travel_time
            FROM routes
            WHERE experiment_id = :exp_id
            ORDER BY vehicle_id, route_id
        """), {'exp_id': experiment_id}).fetchall()

        # Reconstruct routes from segments
        routes = {}
        depot_for_vehicle = {}
        vehicle_distances = {}
        vehicle_times = {}
        vehicle_loads = {}
        vehicle_nodes = {}

        for row in routes_result:
            vehicle_id, node_start, node_end, distance, travel_time = row

            if vehicle_id not in routes:
                routes[vehicle_id] = []
                vehicle_distances[vehicle_id] = 0.0
                vehicle_times[vehicle_id] = 0.0
                vehicle_nodes[vehicle_id] = []

            # Track depot assignments (first node is usually depot)
            if vehicle_id not in depot_for_vehicle:
                if node_start in problem_data['depots']:
                    depot_for_vehicle[vehicle_id] = node_start

            # Accumulate distance and time
            vehicle_distances[vehicle_id] += float(distance)
            vehicle_times[vehicle_id] += float(travel_time)

            # Build node sequence (skip duplicate depots)
            if node_start not in vehicle_nodes[vehicle_id]:
                vehicle_nodes[vehicle_id].append(node_start)
            if node_end not in vehicle_nodes[vehicle_id]:
                vehicle_nodes[vehicle_id].append(node_end)

        # Build solution dict in expected format
        solution = {
            'routes': {},
            'depot_for_vehicle': {},
            'fitness': 0.0,
            'total_distance': 0.0,
            'penalty': 0.0,
            'runtime': runtime,
            'algorithm': algorithm,
            'unallocated': [],
            'vehicle_speed': problem_data['vehicle_speed']
        }

        # Process each vehicle's route
        for vehicle_id in vehicle_nodes.keys():
            nodes = vehicle_nodes[vehicle_id]

            # Remove depot duplicates from middle of route
            route_nodes = []
            for node in nodes:
                if node in problem_data['depots']:
                    if not route_nodes:  # First depot
                        route_nodes.append(node)
                    # Skip depots in middle of route (duplicates)
                else:
                    route_nodes.append(node)

            # Add end depot if not present
            if route_nodes and route_nodes[-1] not in problem_data['depots']:
                route_nodes.append(depot_for_vehicle.get(vehicle_id, route_nodes[0]))

            # Calculate route load
            route_load = 0.0
            for customer in route_nodes:
                if customer in problem_data['customers']:
                    # Get demand for this customer
                    for item_id, quantity in problem_data['customer_orders'].get(customer, {}).items():
                        route_load += problem_data['item_weights'][item_id] * quantity

            # Store route info
            solution['routes'][vehicle_id] = {
                'nodes': route_nodes,
                'distance': vehicle_distances[vehicle_id],
                'time': vehicle_times[vehicle_id],
                'load': route_load
            }

            solution['depot_for_vehicle'][vehicle_id] = depot_for_vehicle.get(vehicle_id, 'D1')
            solution['total_distance'] += vehicle_distances[vehicle_id]
            solution['fitness'] = solution['total_distance']  # Assuming no penalty for stored results

        return solution, problem_data, {
            'algorithm': algorithm,
            'population_size': pop_size,
            'mutation_rate': mut_rate,
            'crossover_rate': cross_rate,
            'seed': seed
        }

    finally:
        session.close()


def export_experiment(experiment_id: int, dataset_id: int = None, output_dir: str = None):
    """
    Export experiment results to CSV, PDF, and GeoJSON.

    Args:
        experiment_id: Experiment ID to export
        dataset_id: Dataset ID (auto-detected if None)
        output_dir: Output directory (default: ./output)
    """
    if output_dir is None:
        output_dir = os.path.join(parent_dir, 'output')

    os.makedirs(output_dir, exist_ok=True)

    # Connect to database
    db = DatabaseConnection()

    # Load experiment
    solution, problem_data, experiment_info = load_experiment_from_db(db, experiment_id)

    # Create exporter
    exporter = MDVRPExporter()

    # Export to all formats
    base_name = f"experiment_{experiment_id}"

    algorithm_params = {
        'seed': experiment_info.get('seed'),
        'dataset_id': dataset_id or 1
    }

    # Add HGA-specific parameters if applicable
    if experiment_info['algorithm'] == 'HGA':
        algorithm_params.update({
            'population_size': experiment_info.get('population_size'),
            'mutation_rate': experiment_info.get('mutation_rate'),
            'crossover_rate': experiment_info.get('crossover_rate')
        })

    created_files = exporter.export_all(
        solution=solution,
        problem_data=problem_data,
        output_dir=output_dir,
        base_name=base_name,
        algorithm_name=experiment_info['algorithm'],
        algorithm_params=algorithm_params
    )

    print(f"\n[SUCCESS] Exported {len(created_files)} files:")
    for file_path in created_files:
        print(f"  - {file_path}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description='Export experiment results from database to CSV, PDF, and GeoJSON',
        epilog="""
Examples:
  python export_experiment.py --experiment 38
  python export_experiment.py -e 38 -o ./my_exports
        """
    )
    parser.add_argument('--experiment', '-e', type=int, default=38,
                       help='Experiment ID to export (default: 38)')
    parser.add_argument('--dataset', '-d', type=int,
                       help='Dataset ID (auto-detected if not specified)')
    parser.add_argument('--output', '-o', type=str,
                       help='Output directory (default: ./output)')

    args = parser.parse_args()

    export_experiment(
        experiment_id=args.experiment,
        dataset_id=args.dataset,
        output_dir=args.output
    )
