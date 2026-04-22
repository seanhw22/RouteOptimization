"""
Distance and time matrix computation using SciPy and NumPy
Shared pre-processing step for all MDVRP solvers
"""

import numpy as np
from scipy.spatial import distance
from typing import Dict, List, Tuple


class DistanceMatrixBuilder:
    """Build distance and time matrices for MDVRP"""

    def __init__(self, coordinates: Dict, vehicle_speeds: Dict):
        """
        Initialize distance matrix builder.

        Args:
            coordinates: {node_id: (lat, lon)} - Dictionary mapping node IDs to coordinates
            vehicle_speeds: {vehicle_id: speed_kmh} - Dictionary mapping vehicle IDs to speeds
        """
        self.coordinates = coordinates
        self.vehicle_speeds = vehicle_speeds

    def build_distance_matrix(self, nodes: List[str]) -> np.ndarray:
        """
        Compute distance matrix using SciPy.

        Uses: Euclidean distance × 111 (degree to km conversion)
              Matches current implementation but vectorized.

        Args:
            nodes: List of node IDs (depots + customers)

        Returns:
            np.ndarray: Square distance matrix where dist_matrix[i,j] is distance from nodes[i] to nodes[j]
        """
        # Extract coordinates in order
        coords = np.array([self.coordinates[node] for node in nodes])

        # Compute pairwise distances using SciPy
        dist_matrix = distance.cdist(coords, coords, metric='euclidean')

        # Convert degrees to km (1 degree ≈ 111 km at equator)
        dist_matrix = dist_matrix * 111

        return dist_matrix

    def build_time_matrices(self, nodes: List[str], vehicles: List[str],
                            dist_matrix: np.ndarray) -> Dict[str, np.ndarray]:
        """
        Build travel time matrices for each vehicle.

        Args:
            nodes: List of node IDs
            vehicles: List of vehicle IDs
            dist_matrix: Pre-computed distance matrix

        Returns:
            Dict: {vehicle_id: time_matrix} where each time_matrix is a NumPy array
        """
        time_matrices = {}

        for vehicle in vehicles:
            speed = self.vehicle_speeds[vehicle]
            # time = distance / speed
            time_matrices[vehicle] = dist_matrix / speed

        return time_matrices

    def calculate_demand(self, customers: List[str], items: List[str],
                        customer_orders: Dict, item_weights: Dict) -> np.ndarray:
        """
        Calculate customer demand using NumPy vectorization.

        Args:
            customers: List of customer IDs
            items: List of item IDs
            customer_orders: {customer_id: {item_id: quantity}}
            item_weights: {item_id: weight_kg}

        Returns:
            np.ndarray: demand per customer, indexed same as customers list
        """
        demand = np.zeros(len(customers))

        for i, customer in enumerate(customers):
            order = customer_orders.get(customer, {})
            demand[i] = sum(
                item_weights[item] * order.get(item, 0)
                for item in items
            )

        return demand

    def build_all_matrices(self,
                          depots: List[str],
                          customers: List[str],
                          vehicles: List[str],
                          items: List[str],
                          coordinates: Dict,
                          vehicle_speeds: Dict,
                          customer_orders: Dict,
                          item_weights: Dict,
                          vehicle_capacities: Dict,
                          max_operational_times: Dict,
                          customer_deadlines: Dict,
                          depot_for_vehicle: Dict,
                          M: int = 1000) -> Dict:
        """
        Build all matrices and package into params dict.

        This is the main method that orchestrates all matrix building
        and returns a params dict compatible with all solvers.

        Args:
            depots: List of depot IDs
            customers: List of customer IDs
            vehicles: List of vehicle IDs
            items: List of item IDs
            coordinates: {node_id: (lat, lon)}
            vehicle_speeds: {vehicle_id: speed_kmh}
            customer_orders: {customer_id: {item_id: quantity}}
            item_weights: {item_id: weight_kg}
            vehicle_capacities: {vehicle_id: capacity_kg}
            max_operational_times: {vehicle_id: max_time_hours}
            customer_deadlines: {customer_id: deadline_hours}
            depot_for_vehicle: {vehicle_id: depot_id}
            M: Big-M constant for constraints

        Returns:
            Dict: Compatible params dict for all solvers with keys:
                  - dist: NumPy distance matrix
                  - T: Dict of NumPy time matrices
                  - demand: NumPy demand array
                  - Q: Vehicle capacities
                  - T_max: Max operational times
                  - L: Customer deadlines
                  - w: Item weights
                  - r: Customer orders
                  - expiry: Item expiry (placeholder, set to 100)
                  - depot_for_vehicle: Depot assignments
                  - M: Big-M constant
        """
        nodes = depots + customers

        # Build distance matrix (NumPy array)
        dist_matrix = self.build_distance_matrix(nodes)

        # Build time matrices (NumPy arrays)
        time_matrices = self.build_time_matrices(nodes, vehicles, dist_matrix)

        # Calculate demand (NumPy array)
        demand = self.calculate_demand(customers, items,
                                       customer_orders, item_weights)

        # Package params (mixed: NumPy arrays + dicts for backward compatibility)
        params = {
            'dist': dist_matrix,  # NumPy array
            'T': time_matrices,   # Dict of NumPy arrays
            'demand': demand,     # NumPy array
            'Q': vehicle_capacities,
            'T_max': max_operational_times,
            'L': customer_deadlines,
            'w': item_weights,
            'r': customer_orders,
            'expiry': {item: 100 for item in items},  # Placeholder
            'depot_for_vehicle': depot_for_vehicle,
            'M': M
        }

        return params

    def get_node_index(self, node: str, nodes: List[str]) -> int:
        """
        Get index of a node in the nodes list.

        Args:
            node: Node ID
            nodes: List of node IDs

        Returns:
            Index of node in list

        Raises:
            ValueError: If node not in list
        """
        try:
            return nodes.index(node)
        except ValueError:
            raise ValueError(f"Node {node} not found in nodes list")
