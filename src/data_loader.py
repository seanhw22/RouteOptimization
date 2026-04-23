"""
Data loading module for MDVRP problem instances
Supports CSV, XLSX, and dict-based input (backward compatibility)
"""

import pandas as pd
import os
from typing import Dict, List, Tuple, Union, Optional
from sqlalchemy import text
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

    def load_from_database(self, db_connection, dataset_id: int) -> Dict:
        """
        Load MDVRP data from PostgreSQL database.

        Performs JOINs to denormalize data into same format as CSV loading.
        Returns identical dict structure as load_csv() for compatibility.

        Args:
            db_connection: DatabaseConnection object with active session
            dataset_id: ID of dataset to load

        Returns:
            Dict with same structure as load_csv()

        Raises:
            ValueError: If data validation fails
            Exception: If database query fails
        """
        # Get database session
        session = db_connection.get_session()

        try:
            # Query depots with coordinates (JOIN)
            depots_query = text("""
                SELECT d.depot_id, n.x, n.y
                FROM depots d
                JOIN nodes n ON d.node_id = n.node_id
                WHERE d.dataset_id = :dataset_id
            """)
            depots_df = pd.read_sql_query(
                depots_query,
                db_connection.engine,
                params={'dataset_id': dataset_id}
            )

            # Query customers with coordinates and deadlines (JOIN)
            customers_query = text("""
                SELECT c.customer_id, n.x, n.y, c.deadline_hours
                FROM customers c
                JOIN nodes n ON c.node_id = n.node_id
                WHERE c.dataset_id = :dataset_id
            """)
            customers_df = pd.read_sql_query(
                customers_query,
                db_connection.engine,
                params={'dataset_id': dataset_id}
            )

            # Query vehicles with depot info
            vehicles_query = text("""
                SELECT vehicle_id, depot_id, vehicle_type,
                       capacity_kg, max_operational_hrs, speed_kmh
                FROM vehicles
                WHERE dataset_id = :dataset_id
            """)
            vehicles_df = pd.read_sql_query(
                vehicles_query,
                db_connection.engine,
                params={'dataset_id': dataset_id}
            )

            # Query items
            items_query = text("""
                SELECT item_id, weight_kg, expiry_hours
                FROM items
                WHERE dataset_id = :dataset_id
            """)
            items_df = pd.read_sql_query(
                items_query,
                db_connection.engine,
                params={'dataset_id': dataset_id}
            )

            # Query orders (need to join to customers to filter by dataset)
            orders_query = text("""
                SELECT o.customer_id, o.item_id, o.quantity
                FROM orders o
                JOIN customers c ON o.customer_id = c.customer_id
                WHERE c.dataset_id = :dataset_id
            """)
            orders_df = pd.read_sql_query(
                orders_query,
                db_connection.engine,
                params={'dataset_id': dataset_id}
            )

        finally:
            session.close()

        # Process data identically to CSV loading
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

        # Build vehicle attributes
        vehicle_speed = vehicles_df.set_index('vehicle_id')['speed_kmh'].to_dict()
        depot_for_vehicle = vehicles_df.set_index('vehicle_id')['depot_id'].to_dict()
        vehicle_capacity = vehicles_df.set_index('vehicle_id')['capacity_kg'].to_dict()
        max_operational_time = vehicles_df.set_index('vehicle_id')['max_operational_hrs'].to_dict()

        # Build customer attributes
        customer_deadlines = customers_df.set_index('customer_id')['deadline_hours'].to_dict()

        # Build item attributes
        item_weights = items_df.set_index('item_id')['weight_kg'].to_dict()
        item_expiry = items_df.set_index('item_id')['expiry_hours'].to_dict()

        # Build customer orders (nested dict)
        customer_orders = {}
        for customer in self.customers:
            customer_orders[customer] = {}
            customer_orders_df = orders_df[orders_df['customer_id'] == customer]
            for _, row in customer_orders_df.iterrows():
                customer_orders[customer][row['item_id']] = row['quantity']

        # Validate using existing validation method
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
