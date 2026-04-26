"""
Distance matrix caching for MDVRP problems (Django ORM).

Caches computed node distances in the ``node_distances`` table to avoid
recomputing the matrix for repeated solver runs against the same dataset.
"""

import random
from typing import Dict, List, Tuple

import numpy as np


class DistanceCache:
    """Handle distance matrix caching with spot-check validation."""

    def __init__(self, dataset_id: int, coordinates: Dict[str, Tuple[float, float]], db_session=None) -> None:
        """``db_session`` is accepted for backward compatibility but ignored."""
        self.dataset_id = dataset_id
        self.coordinates = coordinates
        self.nodes: List[str] = list(coordinates.keys())
        self.db_session = db_session  # unused, kept for older callers

    def is_valid(self) -> bool:
        """Return True if a usable cache exists for this dataset."""
        from datasets.models import NodeDistance

        qs = NodeDistance.objects.filter(dataset_id=self.dataset_id)
        if not qs.exists():
            return False
        if len(self.nodes) < 2:
            return False

        sample = random.sample(self.nodes, min(3, len(self.nodes)))
        for i in range(len(sample)):
            for j in range(i + 1, len(sample)):
                a, b = sample[i], sample[j]
                row = qs.filter(node_start_id=a, node_end_id=b).first()
                if row is None or row.distance is None:
                    return False
                actual = self._haversine_proxy(self.coordinates[a], self.coordinates[b])
                if abs(float(row.distance) - actual) > 0.01:
                    return False
        return True

    def load(self) -> np.ndarray:
        """Load the cached distance matrix as a square NumPy array."""
        from datasets.models import NodeDistance

        rows = NodeDistance.objects.filter(dataset_id=self.dataset_id).values_list(
            'node_start_id', 'node_end_id', 'distance'
        )
        if not rows:
            raise ValueError(f"No cached distances for dataset_id={self.dataset_id}")

        n = len(self.nodes)
        index = {node: i for i, node in enumerate(self.nodes)}
        matrix = np.zeros((n, n))
        for start, end, dist in rows:
            if start in index and end in index and dist is not None:
                matrix[index[start], index[end]] = float(dist)
        return matrix

    def save(self, dist_matrix: np.ndarray) -> None:
        """Replace any existing cache and persist the new distance matrix."""
        from datasets.models import NodeDistance
        from django.db import transaction

        with transaction.atomic():
            NodeDistance.objects.filter(dataset_id=self.dataset_id).delete()
            objs = []
            for i, a in enumerate(self.nodes):
                for j, b in enumerate(self.nodes):
                    if i == j:
                        continue
                    objs.append(NodeDistance(
                        dataset_id=self.dataset_id,
                        node_start_id=a,
                        node_end_id=b,
                        distance=float(dist_matrix[i, j]),
                        travel_time=None,
                    ))
            NodeDistance.objects.bulk_create(objs, batch_size=500)

    @staticmethod
    def _haversine_proxy(p1, p2):
        # The original cache used Euclidean * 111 (km/deg) as a quick proxy
        return float(np.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2) * 111)
