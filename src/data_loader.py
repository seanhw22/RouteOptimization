"""
Data loading module for MDVRP problem instances
Supports CSV, XLSX, and dict-based input (backward compatibility)
"""

import pandas as pd
import os
from typing import Dict, List, Tuple, Union, Optional
import numpy as np


class MDVRPDataLoader:
    """Load MDVRP problem data from various sources"""

    def __init__(self):
        """Initialize data loader"""
        self.data = None
        self.depots = None
        self.customers = None
        self.vehicles = None
        self.items = None

    def load_csv(self, data_dir: str) -> Dict:
        """
        Load MDVRP data from CSV files.

        Expected files:
        - depots.csv: depot_id, x, y
        - customers.csv: customer_id, x, y, deadline_hours
        - vehicles.csv: vehicle_id, depot_id, vehicle_type, capacity_kg, max_operational_hrs, speed_kmh
        - orders.csv: customer_id, item_id, quantity
        - items.csv: item_id, weight_kg, expiry_hours

        Args:
            data_dir: Path to directory containing CSV files

        Returns:
            Dict with depots, customers, vehicles, items, coordinates,
                   customer_orders, item_weights, item_expiry, etc.

        Raises:
            FileNotFoundError: If required CSV files are missing
            ValueError: If data validation fails
        """
        # Validate directory exists
        if not os.path.isdir(data_dir):
            raise FileNotFoundError(f"Directory not found: {data_dir}")

        # Load depots
        depots_path = os.path.join(data_dir, 'depots.csv')
        if not os.path.exists(depots_path):
            raise FileNotFoundError(f"Required file not found: {depots_path}")
        depots_df = pd.read_csv(depots_path)

        # Load customers
        customers_path = os.path.join(data_dir, 'customers.csv')
        if not os.path.exists(customers_path):
            raise FileNotFoundError(f"Required file not found: {customers_path}")
        customers_df = pd.read_csv(customers_path)

        # Load vehicles
        vehicles_path = os.path.join(data_dir, 'vehicles.csv')
        if not os.path.exists(vehicles_path):
            raise FileNotFoundError(f"Required file not found: {vehicles_path}")
        vehicles_df = pd.read_csv(vehicles_path)

        # Load orders
        orders_path = os.path.join(data_dir, 'orders.csv')
        if not os.path.exists(orders_path):
            raise FileNotFoundError(f"Required file not found: {orders_path}")
        orders_df = pd.read_csv(orders_path)

        # Load items
        items_path = os.path.join(data_dir, 'items.csv')
        if not os.path.exists(items_path):
            raise FileNotFoundError(f"Required file not found: {items_path}")
        items_df = pd.read_csv(items_path)

        # Extract data
        self.depots = depots_df['depot_id'].tolist()
        self.customers = customers_df['customer_id'].tolist()
        self.vehicles = vehicles_df['vehicle_id'].tolist()
        self.items = items_df['item_id'].tolist()

        # Build coordinates
        coordinates = {}

        # Add depot coordinates
        for _, row in depots_df.iterrows():
            coordinates[row['depot_id']] = (row['x'], row['y'])

        # Add customer coordinates
        for _, row in customers_df.iterrows():
            coordinates[row['customer_id']] = (row['x'], row['y'])

        # Build vehicle speed dict
        vehicle_speed = vehicles_df.set_index('vehicle_id')['speed_kmh'].to_dict()

        # Build depot assignment
        depot_for_vehicle = vehicles_df.set_index('vehicle_id')['depot_id'].to_dict()

        # Build vehicle capacities
        vehicle_capacity = vehicles_df.set_index('vehicle_id')['capacity_kg'].to_dict()

        # Build max operational times
        max_operational_time = vehicles_df.set_index('vehicle_id')['max_operational_hrs'].to_dict()

        # Build customer deadlines
        customer_deadlines = customers_df.set_index('customer_id')['deadline_hours'].to_dict()

        # Build item weights
        item_weights = items_df.set_index('item_id')['weight_kg'].to_dict()

        # Build item expiry
        item_expiry = items_df.set_index('item_id')['expiry_hours'].to_dict()

        # Build customer orders (nested dict)
        customer_orders = {}
        for customer in self.customers:
            customer_orders[customer] = {}
            customer_orders_df = orders_df[orders_df['customer_id'] == customer]
            for _, row in customer_orders_df.iterrows():
                customer_orders[customer][row['item_id']] = row['quantity']

        # Validate data
        self._validate_data(
            coordinates, vehicle_speed, depot_for_vehicle,
            vehicle_capacity, max_operational_time, customer_deadlines,
            item_weights, item_expiry, customer_orders
        )

        # Package data
        self.data = {
            'depots': self.depots,
            'customers': self.customers,
            'vehicles': self.vehicles,
            'items': self.items,
            'coordinates': coordinates,
            'vehicle_speed': vehicle_speed,
            'depot_for_vehicle': depot_for_vehicle,
            'vehicle_capacity': vehicle_capacity,
            'max_operational_time': max_operational_time,
            'customer_deadlines': customer_deadlines,
            'item_weights': item_weights,
            'item_expiry': item_expiry,
            'customer_orders': customer_orders
        }

        return self.data

    def load_xlsx(self, file_path: str) -> Dict:
        """
        Load MDVRP data from single Excel file with multiple sheets.

        Expected sheets:
        - depots: depot_id, x, y
        - customers: customer_id, x, y, deadline_hours
        - vehicles: vehicle_id, depot_id, vehicle_type, capacity_kg, max_operational_hrs, speed_kmh
        - orders: customer_id, item_id, quantity
        - items: item_id, weight_kg, expiry_hours

        Args:
            file_path: Path to Excel file

        Returns:
            Dict with same structure as load_csv()

        Raises:
            FileNotFoundError: If file not found
            ValueError: If data validation fails or sheets missing
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        # Read all sheets
        try:
            depots_df = pd.read_excel(file_path, sheet_name='depots')
            customers_df = pd.read_excel(file_path, sheet_name='customers')
            vehicles_df = pd.read_excel(file_path, sheet_name='vehicles')
            orders_df = pd.read_excel(file_path, sheet_name='orders')
            items_df = pd.read_excel(file_path, sheet_name='items')
        except ValueError as e:
            raise ValueError(f"Missing required sheet in Excel file: {e}")

        # Process same as CSV (reuse logic)
        self.depots = depots_df['depot_id'].tolist()
        self.customers = customers_df['customer_id'].tolist()
        self.vehicles = vehicles_df['vehicle_id'].tolist()
        self.items = items_df['item_id'].tolist()

        # Build coordinates
        coordinates = {}
        for _, row in depots_df.iterrows():
            coordinates[row['depot_id']] = (row['x'], row['y'])
        for _, row in customers_df.iterrows():
            coordinates[row['customer_id']] = (row['x'], row['y'])

        # Build dicts
        vehicle_speed = vehicles_df.set_index('vehicle_id')['speed_kmh'].to_dict()
        depot_for_vehicle = vehicles_df.set_index('vehicle_id')['depot_id'].to_dict()
        vehicle_capacity = vehicles_df.set_index('vehicle_id')['capacity_kg'].to_dict()
        max_operational_time = vehicles_df.set_index('vehicle_id')['max_operational_hrs'].to_dict()
        customer_deadlines = customers_df.set_index('customer_id')['deadline_hours'].to_dict()
        item_weights = items_df.set_index('item_id')['weight_kg'].to_dict()
        item_expiry = items_df.set_index('item_id')['expiry_hours'].to_dict()

        # Build customer orders
        customer_orders = {}
        for customer in self.customers:
            customer_orders[customer] = {}
            customer_orders_df = orders_df[orders_df['customer_id'] == customer]
            for _, row in customer_orders_df.iterrows():
                customer_orders[customer][row['item_id']] = row['quantity']

        # Validate
        self._validate_data(
            coordinates, vehicle_speed, depot_for_vehicle,
            vehicle_capacity, max_operational_time, customer_deadlines,
            item_weights, item_expiry, customer_orders
        )

        # Package
        self.data = {
            'depots': self.depots,
            'customers': self.customers,
            'vehicles': self.vehicles,
            'items': self.items,
            'coordinates': coordinates,
            'vehicle_speed': vehicle_speed,
            'depot_for_vehicle': depot_for_vehicle,
            'vehicle_capacity': vehicle_capacity,
            'max_operational_time': max_operational_time,
            'customer_deadlines': customer_deadlines,
            'item_weights': item_weights,
            'item_expiry': item_expiry,
            'customer_orders': customer_orders
        }

        return self.data

    def load_from_dict(self, data: Dict) -> Dict:
        """
        Load from dict (backward compatibility with mdvrp_small.py).

        Validates and standardizes the data format.

        Args:
            data: Dict with keys like depots, customers, vehicles, items,
                  coordinates, vehicle_speed, depot_for_vehicle, etc.

        Returns:
            Validated and standardized dict

        Raises:
            ValueError: If data validation fails
        """
        # Validate required keys
        required_keys = [
            'depots', 'customers', 'vehicles', 'items',
            'coordinates', 'vehicle_speed', 'depot_for_vehicle'
        ]
        for key in required_keys:
            if key not in data:
                raise ValueError(f"Missing required key in data dict: {key}")

        self.depots = data['depots']
        self.customers = data['customers']
        self.vehicles = data['vehicles']
        self.items = data['items']

        # Extract with defaults for optional keys
        coordinates = data['coordinates']
        vehicle_speed = data['vehicle_speed']
        depot_for_vehicle = data['depot_for_vehicle']
        vehicle_capacity = data.get('vehicle_capacity', {})
        max_operational_time = data.get('max_operational_time', {})
        customer_deadlines = data.get('customer_deadlines', {})
        item_weights = data.get('item_weights', {})
        item_expiry = data.get('item_expiry', {})
        customer_orders = data.get('customer_orders', {})

        # Validate
        self._validate_data(
            coordinates, vehicle_speed, depot_for_vehicle,
            vehicle_capacity, max_operational_time, customer_deadlines,
            item_weights, item_expiry, customer_orders
        )

        # Package
        self.data = {
            'depots': self.depots,
            'customers': self.customers,
            'vehicles': self.vehicles,
            'items': self.items,
            'coordinates': coordinates,
            'vehicle_speed': vehicle_speed,
            'depot_for_vehicle': depot_for_vehicle,
            'vehicle_capacity': vehicle_capacity,
            'max_operational_time': max_operational_time,
            'customer_deadlines': customer_deadlines,
            'item_weights': item_weights,
            'item_expiry': item_expiry,
            'customer_orders': customer_orders
        }

        return self.data

    def _validate_data(self, coordinates: Dict, vehicle_speed: Dict,
                       depot_for_vehicle: Dict, vehicle_capacity: Dict,
                       max_operational_time: Dict, customer_deadlines: Dict,
                       item_weights: Dict, item_expiry: Dict,
                       customer_orders: Dict) -> None:
        """
        Validate data completeness and consistency.

        Args:
            coordinates: Node coordinates
            vehicle_speed: Vehicle speeds
            depot_for_vehicle: Depot assignments
            vehicle_capacity: Vehicle capacities
            max_operational_time: Max operational times
            customer_deadlines: Customer deadlines
            item_weights: Item weights
            item_expiry: Item expiry times
            customer_orders: Customer orders

        Raises:
            ValueError: If validation fails
        """
        # Check all nodes have coordinates
        all_nodes = self.depots + self.customers
        for node in all_nodes:
            if node not in coordinates:
                raise ValueError(f"Missing coordinates for node: {node}")

        # Validate coordinates are within valid ranges
        for node, (lat, lon) in coordinates.items():
            if not (-90 <= lat <= 90):
                raise ValueError(f"Invalid latitude for {node}: {lat}")
            if not (-180 <= lon <= 180):
                raise ValueError(f"Invalid longitude for {node}: {lon}")

        # Check all vehicles have required attributes
        for vehicle in self.vehicles:
            if vehicle not in vehicle_speed:
                raise ValueError(f"Missing speed for vehicle: {vehicle}")
            if vehicle not in depot_for_vehicle:
                raise ValueError(f"Missing depot assignment for vehicle: {vehicle}")
            if vehicle not in vehicle_capacity:
                raise ValueError(f"Missing capacity for vehicle: {vehicle}")
            if vehicle not in max_operational_time:
                raise ValueError(f"Missing max time for vehicle: {vehicle}")

            # Check depot exists
            depot = depot_for_vehicle[vehicle]
            if depot not in self.depots:
                raise ValueError(f"Invalid depot {depot} for vehicle {vehicle}")

        # Check all customers have deadlines
        for customer in self.customers:
            if customer not in customer_deadlines:
                raise ValueError(f"Missing deadline for customer: {customer}")

        # Check all items have weights
        for item in self.items:
            if item not in item_weights:
                raise ValueError(f"Missing weight for item: {item}")
            if item not in item_expiry:
                raise ValueError(f"Missing expiry for item: {item}")

        # Check customer orders are valid
        for customer, orders in customer_orders.items():
            if customer not in self.customers:
                raise ValueError(f"Invalid customer in orders: {customer}")
            for item in orders.keys():
                if item not in self.items:
                    raise ValueError(f"Invalid item {item} in order for {customer}")

    def load_from_database(self, dataset_id: int, db_connection=None) -> Dict:
        """
        Load MDVRP data from PostgreSQL database via Django ORM.

        Returns the same dict structure as load_csv() for solver compatibility.

        Args:
            dataset_id: ID of dataset to load
            db_connection: Unused (kept for backward compatibility with old callers)

        Returns:
            Dict with same structure as load_csv()

        Raises:
            ValueError: If data validation fails or dataset not found
        """
        # Lazy import — Django must be set up by caller before this is invoked
        from datasets.models import Customer, Depot, Item, Order, Vehicle

        depot_qs = Depot.objects.select_related('node').filter(dataset_id=dataset_id)
        customer_qs = Customer.objects.select_related('node').filter(dataset_id=dataset_id)
        vehicle_qs = Vehicle.objects.filter(dataset_id=dataset_id)
        item_qs = Item.objects.filter(dataset_id=dataset_id)
        order_qs = Order.objects.filter(dataset_id=dataset_id)

        self.depots = [d.depot_id for d in depot_qs]
        self.customers = [c.customer_id for c in customer_qs]
        self.vehicles = [v.vehicle_id for v in vehicle_qs]
        self.items = [it.item_id for it in item_qs]

        if not self.depots:
            raise ValueError(f"Dataset {dataset_id} has no depots (or does not exist)")

        coordinates = {}
        for d in depot_qs:
            coordinates[d.depot_id] = (d.node.x, d.node.y)
        for c in customer_qs:
            coordinates[c.customer_id] = (c.node.x, c.node.y)

        vehicle_speed = {v.vehicle_id: float(v.speed_kmh) for v in vehicle_qs}
        depot_for_vehicle = {v.vehicle_id: v.depot_id for v in vehicle_qs}
        vehicle_capacity = {v.vehicle_id: float(v.capacity_kg) for v in vehicle_qs}
        max_operational_time = {v.vehicle_id: float(v.max_operational_hrs) for v in vehicle_qs}
        customer_deadlines = {c.customer_id: c.deadline_hours for c in customer_qs}
        item_weights = {it.item_id: float(it.weight_kg) for it in item_qs}
        item_expiry = {it.item_id: it.expiry_hours for it in item_qs}

        customer_orders: Dict[str, Dict[str, int]] = {c: {} for c in self.customers}
        for o in order_qs:
            customer_orders[o.customer_id][o.item_id] = o.quantity

        self._validate_data(
            coordinates, vehicle_speed, depot_for_vehicle,
            vehicle_capacity, max_operational_time, customer_deadlines,
            item_weights, item_expiry, customer_orders
        )

        # Build all required matrices using DistanceMatrixBuilder (same as CSV loading)
        from src.distance_matrix import DistanceMatrixBuilder

        builder = DistanceMatrixBuilder(coordinates, vehicle_speed)
        params = builder.build_all_matrices(
            self.depots, self.customers, self.vehicles, self.items,
            coordinates, vehicle_speed,
            customer_orders, item_weights,
            vehicle_capacity, max_operational_time,
            customer_deadlines, depot_for_vehicle
        )

        # Convert NumPy matrices to dictionary format for solver compatibility
        # Solvers expect dist as {node_i: {node_j: distance}} not as NumPy array
        # Solvers expect T as {vehicle_id: {node_i: {node_j: time}}} not as NumPy arrays
        nodes = self.depots + self.customers

        # Convert distance matrix
        dist_dict = {}
        for i, node_i in enumerate(nodes):
            dist_dict[node_i] = {}
            for j, node_j in enumerate(nodes):
                dist_dict[node_i][node_j] = float(params['dist'][i][j])

        # Convert time matrices (one per vehicle)
        T_dict = {}
        for vehicle in self.vehicles:
            T_dict[vehicle] = {}
            time_matrix = params['T'][vehicle]  # NumPy array
            for i, node_i in enumerate(nodes):
                T_dict[vehicle][node_i] = {}
                for j, node_j in enumerate(nodes):
                    T_dict[vehicle][node_i][node_j] = float(time_matrix[i][j])

        # Replace NumPy arrays with dictionaries
        params['dist'] = dist_dict
        params['T'] = T_dict

        # Package data (identical to CSV format)
        # Include raw data plus computed matrices
        self.data = {
            # Raw data
            'depots': self.depots,
            'customers': self.customers,
            'vehicles': self.vehicles,
            'items': self.items,
            'coordinates': coordinates,
            'vehicle_speed': vehicle_speed,
            'depot_for_vehicle': depot_for_vehicle,
            'vehicle_capacity': vehicle_capacity,
            'max_operational_time': max_operational_time,
            'customer_deadlines': customer_deadlines,
            'item_weights': item_weights,
            'item_expiry': item_expiry,
            'customer_orders': customer_orders,
            # Computed matrices (from DistanceMatrixBuilder)
            **params  # This includes dist (now as dict), T, Q, T_max, L, w, r, expiry, depot_for_vehicle
        }

        return self.data

    def validate_data(self, data: Dict) -> bool:
        """
        Validate data completeness and consistency.

        Args:
            data: Data dict to validate

        Returns:
            True if valid

        Raises:
            ValueError: If validation fails
        """
        # Temporarily load and validate
        original_data = self.data
        self.load_from_dict(data)
        self.data = original_data
        return True
