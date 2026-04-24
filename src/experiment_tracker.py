"""
Experiment tracking for MDVRP solver runs.
Tracks solver experiments, results, and routes in database.
"""

from typing import Dict, List, Optional, Any
from sqlalchemy import text
from sqlalchemy.orm import Session


class ExperimentTracker:
    """Handle experiment, results, and routes storage"""

    def __init__(self, db_session: Session) -> None:
        """
        Initialize experiment tracker.

        Args:
            db_session: SQLAlchemy database session
        """
        self.db_session: Session = db_session

    def create_experiment(self, metadata: Dict[str, Any]) -> int:
        """
        Create experiment record and return experiment_id.

        Args:
            metadata: Dictionary containing:
                - dataset_id: int (required)
                - algorithm: str (required) - 'Greedy', 'HGA', or 'MILP'
                - population_size: int (optional, for HGA)
                - mutation_rate: float (optional, for HGA)
                - crossover_rate: float (optional, for HGA)
                - seed: int (optional)

        Returns:
            experiment_id: Primary key of created experiment record

        Raises:
            ValueError: If required fields missing
            Exception: If database insert fails
        """
        try:
            # Validate required fields
            if 'dataset_id' not in metadata or 'algorithm' not in metadata:
                raise ValueError("metadata must contain 'dataset_id' and 'algorithm'")

            # Insert experiment record
            result = self.db_session.execute(text("""
                INSERT INTO experiments (dataset_id, algorithm, population_size, mutation_rate, crossover_rate, seed)
                VALUES (:dataset_id, :algorithm, :population_size, :mutation_rate, :crossover_rate, :seed)
                RETURNING experiment_id
            """), {
                'dataset_id': metadata['dataset_id'],
                'algorithm': metadata['algorithm'],
                'population_size': metadata.get('population_size'),
                'mutation_rate': metadata.get('mutation_rate'),
                'crossover_rate': metadata.get('crossover_rate'),
                'seed': metadata.get('seed')
            })

            self.db_session.commit()

            experiment_id = result.fetchone()[0]
            return experiment_id

        except Exception as e:
            self.db_session.rollback()
            raise Exception(f"Failed to create experiment: {e}")

    def save_result_metrics(self, experiment_id: int, metrics: Dict):
        """
        Save runtime metrics for an experiment.

        Args:
            experiment_id: Experiment identifier
            metrics: Dictionary containing:
                - runtime: float (required) - Solver runtime in seconds

        Raises:
            ValueError: If required fields missing
            Exception: If database insert fails
        """
        try:
            if 'runtime' not in metrics:
                raise ValueError("metrics must contain 'runtime'")

            self.db_session.execute(text("""
                INSERT INTO result_metrics (experiment_id, runtime_id)
                VALUES (:experiment_id, :runtime)
            """), {
                'experiment_id': experiment_id,
                'runtime': metrics['runtime']
            })

            self.db_session.commit()

        except Exception as e:
            self.db_session.rollback()
            raise Exception(f"Failed to save result metrics: {e}")

    def save_routes(self, experiment_id: int, routes: Dict):
        """
        Save route segments for an experiment.

        Args:
            experiment_id: Experiment identifier
            routes: Dictionary mapping vehicle_id to route info:
                {
                    'V1': {
                        'nodes': [C1, C2, C3],
                        'distance': 123.45,
                        ...
                    },
                    ...
                }

        Raises:
            Exception: If database insert fails
        """
        try:
            # Prepare batch insert data
            insert_data = []

            for vehicle_id, route_info in routes.items():
                nodes = route_info.get('nodes', [])

                if not nodes:
                    # Empty route: depot to depot
                    insert_data.append({
                        'experiment_id': experiment_id,
                        'vehicle_id': vehicle_id,
                        'node_start_id': None,  # Will be filled by caller
                        'node_end_id': None,
                        'total_distance': 0.0
                    })
                else:
                    # Create segments for route: depot -> C1 -> C2 -> ... -> depot
                    # Note: Caller must provide depot_id, we just segment what's given
                    for i in range(len(nodes) - 1):
                        insert_data.append({
                            'experiment_id': experiment_id,
                            'vehicle_id': vehicle_id,
                            'node_start_id': nodes[i],
                            'node_end_id': nodes[i + 1],
                            'total_distance': None  # Would need distance matrix
                        })

                    # Add return to depot (if caller provides depot info)
                    # This is simplified - actual implementation needs depot info

            # Batch insert
            if insert_data:
                self.db_session.execute(text("""
                    INSERT INTO routes (experiment_id, vehicle_id, node_start_id, node_end_id, total_distance)
                    VALUES (:experiment_id, :vehicle_id, :node_start_id, :node_end_id, :total_distance)
                """), insert_data)

            self.db_session.commit()

        except Exception as e:
            self.db_session.rollback()
            raise Exception(f"Failed to save routes: {e}")

    def load_routes(self, experiment_id: int) -> Dict:
        """
        Load and reconstruct routes from database.

        Args:
            experiment_id: Experiment identifier

        Returns:
            Dictionary mapping vehicle_id to route info

        Raises:
            Exception: If database query fails
        """
        try:
            # Query all route segments for this experiment
            result = self.db_session.execute(text("""
                SELECT vehicle_id, node_start_id, node_end_id, total_distance
                FROM routes
                WHERE experiment_id = :experiment_id
                ORDER BY vehicle_id, route_id
            """), {'experiment_id': experiment_id}).fetchall()

            # Reconstruct routes by following segments
            routes = {}
            current_vehicle = None
            current_nodes = []

            for row in result:
                vehicle_id, node_start, node_end, distance = row

                if vehicle_id != current_vehicle:
                    # New vehicle
                    if current_vehicle:
                        routes[current_vehicle] = {
                            'nodes': current_nodes,
                            'distance': sum(r.get('distance', 0) for r in routes.get(current_vehicle, {'segments': []}).get('segments', []))
                        }
                    current_vehicle = vehicle_id
                    current_nodes = []

                if node_start not in current_nodes:
                    current_nodes.append(node_start)
                if node_end not in current_nodes:
                    current_nodes.append(node_end)

            # Add last vehicle
            if current_vehicle and current_vehicle not in routes:
                routes[current_vehicle] = {'nodes': current_nodes}

            return routes

        except Exception as e:
            raise Exception(f"Failed to load routes: {e}")
