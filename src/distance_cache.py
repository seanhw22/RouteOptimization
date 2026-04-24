"""
Distance matrix caching for MDVRP problems.
Caches computed node distances in database to avoid redundant calculations.
"""

import random
import numpy as np
from typing import Dict, Tuple, List, Optional, Any
from sqlalchemy import text
from sqlalchemy.orm import Session


class DistanceCache:
    """Handle distance matrix caching with validation"""

    def __init__(self, db_session: Session, dataset_id: int, coordinates: Dict[str, Tuple[float, float]]) -> None:
        """
        Initialize distance cache.

        Args:
            db_session: SQLAlchemy database session
            dataset_id: Dataset identifier for caching
            coordinates: Dictionary mapping node_id to (x, y) coordinates
        """
        self.db_session: Session = db_session
        self.dataset_id: int = dataset_id
        self.coordinates: Dict[str, Tuple[float, float]] = coordinates
        self.nodes: List[str] = list(coordinates.keys())

    def is_valid(self) -> bool:
        """
        Check if cached distances are valid via spot-check validation.

        Uses 3 random node pair samples to validate cache integrity.
        If any sampled pair differs from cached distance by > 0.01,
        considers cache invalid.

        Returns:
            True if cache exists and is valid, False otherwise
        """
        try:
            # Check if cache exists
            count_result = self.db_session.execute(text("""
                SELECT COUNT(*) FROM node_distances
                WHERE dataset_id = :dataset_id
            """), {'dataset_id': self.dataset_id}).fetchone()

            if count_result[0] == 0:
                return False

            # Spot-check validation: sample 3 random node pairs
            if len(self.nodes) < 2:
                return False

            sample_pairs = random.sample(list(self.nodes), min(3, len(self.nodes)))
            num_samples = len(sample_pairs)

            for i in range(num_samples):
                for j in range(i + 1, num_samples):
                    node1, node2 = sample_pairs[i], sample_pairs[j]

                    # Query cached distance
                    cached_result = self.db_session.execute(text("""
                        SELECT distance FROM node_distances
                        WHERE node_start_id = :node1 AND node_end_id = :node2
                        AND dataset_id = :dataset_id
                    """), {
                        'node1': node1,
                        'node2': node2,
                        'dataset_id': self.dataset_id
                    }).fetchone()

                    # Compute actual distance
                    coord1 = self.coordinates[node1]
                    coord2 = self.coordinates[node2]
                    actual_distance = np.sqrt((coord1[0] - coord2[0])**2 + (coord1[1] - coord2[1])**2) * 111

                    # Validate - convert decimal.Decimal to float if needed
                    if not cached_result or cached_result[0] is None:
                        return False

                    cached_distance = float(cached_result[0])
                    if abs(cached_distance - actual_distance) > 0.01:
                        return False

            return True

        except Exception as e:
            # If validation fails for any reason, consider cache invalid
            print(f"Cache validation error: {e}")
            return False

    def load(self) -> np.ndarray:
        """
        Load distance matrix from cache.

        Returns:
            Square NumPy array where dist_matrix[i,j] is distance from nodes[i] to nodes[j]

        Raises:
            ValueError: If cache is empty or invalid
        """
        try:
            # Check if cache exists
            count_result = self.db_session.execute(text("""
                SELECT COUNT(*) FROM node_distances
                WHERE dataset_id = :dataset_id
            """), {'dataset_id': self.dataset_id}).fetchone()

            if count_result[0] == 0:
                return False

            # Spot-check validation: sample 3 random node pairs
            if len(self.nodes) < 2:
                return False

            sample_pairs = random.sample(list(self.nodes), min(3, len(self.nodes)))
            num_samples = len(sample_pairs)

            for i in range(num_samples):
                for j in range(i + 1, num_samples):
                    node1, node2 = sample_pairs[i], sample_pairs[j]

                    # Query cached distance
                    cached_result = self.db_session.execute(text("""
                        SELECT distance FROM node_distances
                        WHERE node_start_id = :node1 AND node_end_id = :node2
                        AND dataset_id = :dataset_id
                    """), {
                        'node1': node1,
                        'node2': node2,
                        'dataset_id': self.dataset_id
                    }).fetchone()

                    # Compute actual distance
                    coord1 = self.coordinates[node1]
                    coord2 = self.coordinates[node2]
                    actual_distance = np.sqrt((coord1[0] - coord2[0])**2 + (coord1[1] - coord2[1])**2) * 111

                    # Validate - convert decimal.Decimal to float if needed
                    if not cached_result or cached_result[0] is None:
                        return False

                    cached_distance = float(cached_result[0])
                    if abs(cached_distance - actual_distance) > 0.01:
                        return False

            return True

        except Exception as e:
            # If validation fails for any reason, consider cache invalid
            print(f"Cache validation error: {e}")
            return False

    def load(self) -> np.ndarray:
        """
        Load distance matrix from cache.

        Returns:
            Square NumPy array where dist_matrix[i,j] is distance from nodes[i] to nodes[j]

        Raises:
            ValueError: If cache is empty or invalid
        """
        try:
            # Query all distances for this dataset
            result = self.db_session.execute(text("""
                SELECT node_start_id, node_end_id, distance
                FROM node_distances
                WHERE dataset_id = :dataset_id
            """), {'dataset_id': self.dataset_id}).fetchall()

            if not result:
                raise ValueError(f"No cached distances found for dataset_id={self.dataset_id}")

            # Build distance matrix
            n = len(self.nodes)
            dist_matrix = np.zeros((n, n))

            for row in result:
                node_start, node_end, distance = row
                i = self.nodes.index(node_start)
                j = self.nodes.index(node_end)
                dist_matrix[i, j] = distance

            return dist_matrix

        except Exception as e:
            raise ValueError(f"Failed to load cached distances: {e}")

    def save(self, dist_matrix: np.ndarray):
        """
        Save distance matrix to cache using batch insert.

        Args:
            dist_matrix: Square NumPy distance matrix

        Raises:
            Exception: If database insert fails
        """
        try:
            # Clear existing cache for this dataset
            self.db_session.execute(text("""
                DELETE FROM node_distances
                WHERE dataset_id = :dataset_id
            """), {'dataset_id': self.dataset_id})

            # Prepare batch insert data
            insert_data = []
            n = len(self.nodes)

            for i in range(n):
                for j in range(n):
                    if i != j:  # Skip diagonal (distance from node to itself)
                        insert_data.append({
                            'node_start_id': self.nodes[i],
                            'node_end_id': self.nodes[j],
                            'dataset_id': self.dataset_id,
                            'distance': float(dist_matrix[i, j]),  # Ensure it's a float
                            'travel_time': None  # Not used currently
                        })

            # Batch insert using executemany
            self.db_session.execute(text("""
                INSERT INTO node_distances (node_start_id, node_end_id, dataset_id, distance, travel_time)
                VALUES (:node_start_id, :node_end_id, :dataset_id, :distance, :travel_time)
            """), insert_data)

            self.db_session.commit()

        except Exception as e:
            self.db_session.rollback()
            raise Exception(f"Failed to save distances to cache: {e}")
