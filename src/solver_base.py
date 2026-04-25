"""
Shared utilities for MDVRP solver initialisation and route calculations.
"""

import os


def load_solver_data(data_source, depots, customers, vehicles, items, params):
    """
    Load problem data from a CSV directory or XLSX file.

    If data_source is None, returns inputs unchanged (passthrough for dict-based usage).
    Returns (depots, customers, vehicles, items, params).
    """
    if data_source is None:
        return depots, customers, vehicles, items, params

    from src.data_loader import MDVRPDataLoader
    from src.distance_matrix import DistanceMatrixBuilder

    loader = MDVRPDataLoader()
    if os.path.isdir(data_source):
        data = loader.load_csv(data_source)
    elif data_source.endswith('.xlsx'):
        data = loader.load_xlsx(data_source)
    else:
        raise ValueError(f"Unsupported data source format: {data_source}")

    depots = data['depots']
    customers = data['customers']
    vehicles = data['vehicles']
    items = data['items']

    builder = DistanceMatrixBuilder(data['coordinates'], data['vehicle_speed'])
    params = builder.build_all_matrices(
        depots, customers, vehicles, items,
        data['coordinates'], data['vehicle_speed'],
        data['customer_orders'], data['item_weights'],
        data['vehicle_capacity'], data['max_operational_time'],
        data['customer_deadlines'], data['depot_for_vehicle']
    )
    params.update({k: v for k, v in data.items() if k not in params})

    return depots, customers, vehicles, items, params


def calculate_route_distance(route, depot, dist, node_to_idx=None, uses_numpy=False):
    """
    Calculate total distance for a vehicle route: depot -> customers -> depot.

    Filters None values from route (safe for HGA chromosome encoding).
    Returns 0.0 for empty routes.
    """
    route = [c for c in route if c is not None]
    if not route:
        return 0.0

    if uses_numpy:
        indices = [node_to_idx[depot]]
        indices.extend(node_to_idx[c] for c in route)
        indices.append(node_to_idx[depot])
        total = 0.0
        for i in range(len(indices) - 1):
            total += dist[indices[i]][indices[i + 1]]
        return total
    else:
        total = 0.0
        prev = depot
        for customer in route:
            total += dist[prev][customer]
            prev = customer
        total += dist[prev][depot]
        return total
