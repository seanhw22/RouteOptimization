#!/usr/bin/env python3
"""
Populate PostgreSQL database with data from CSV files.

This script reads CSV files and inserts data into the MDVRP database tables.
It handles the normalized schema with separate nodes table.

Usage:
    python scripts/populate_database.py <dataset_id> <dataset_name> <database_url>

Example:
    python scripts/populate_database.py 1 "Test Dataset" "postgresql://mdvrp:mdvrp@localhost:5432/mdvrp"
"""

import sys
import os
import pandas as pd
from sqlalchemy import text
from src.database import DatabaseConnection


def populate_dataset(dataset_id: int, dataset_name: str, db_url: str, data_dir: str = 'data'):
    """
    Populate database with data from CSV files.

    Args:
        dataset_id: ID for this dataset
        dataset_name: Name for this dataset
        db_url: PostgreSQL database URL
        data_dir: Directory containing CSV files (default: 'data')

    Raises:
        FileNotFoundError: If CSV files not found
        Exception: If database insertion fails
    """
    print(f"Populating dataset {dataset_id}: {dataset_name}")
    print(f"Data directory: {data_dir}")
    print(f"Database: {db_url}")
    print("-" * 50)

    # Connect to database
    conn = DatabaseConnection(db_url)

    if not conn.test_connection():
        raise Exception("Cannot connect to database!")

    session = conn.get_session()

    try:
        # Read CSV files
        print("\n📂 Reading CSV files...")
        depots_df = pd.read_csv(os.path.join(data_dir, 'depots.csv'))
        customers_df = pd.read_csv(os.path.join(data_dir, 'customers.csv'))
        vehicles_df = pd.read_csv(os.path.join(data_dir, 'vehicles.csv'))
        items_df = pd.read_csv(os.path.join(data_dir, 'items.csv'))
        orders_df = pd.read_csv(os.path.join(data_dir, 'orders.csv'))

        print(f"  ✓ Loaded {len(depots_df)} depots")
        print(f"  ✓ Loaded {len(customers_df)} customers")
        print(f"  ✓ Loaded {len(vehicles_df)} vehicles")
        print(f"  ✓ Loaded {len(items_df)} items")
        print(f"  ✓ Loaded {len(orders_df)} orders")

        # Begin transaction
        with session.begin():
            # 1. Insert dataset
            print(f"\n📝 Inserting dataset...")
            result = session.execute(text("""
                INSERT INTO datasets (dataset_id, user_id, name)
                VALUES (:dataset_id, 1, :name)
                ON CONFLICT (dataset_id) DO UPDATE SET name = :name
            """), {'dataset_id': dataset_id, 'name': dataset_name})
            print(f"  ✓ Dataset {dataset_id}: {dataset_name}")

            # 2. Insert nodes (depots + customers coordinates)
            print(f"\n📍 Inserting nodes...")
            node_count = 0

            # Insert depot nodes
            for _, row in depots_df.iterrows():
                session.execute(text("""
                    INSERT INTO nodes (node_id, dataset_id, x, y)
                    VALUES (:node_id, :dataset_id, :x, :y)
                    ON CONFLICT (node_id) DO UPDATE SET x = :x, y = :y
                """), {
                    'node_id': row['depot_id'],
                    'dataset_id': dataset_id,
                    'x': float(row['x']),
                    'y': float(row['y'])
                })
                node_count += 1

            # Insert customer nodes
            for _, row in customers_df.iterrows():
                session.execute(text("""
                    INSERT INTO nodes (node_id, dataset_id, x, y)
                    VALUES (:node_id, :dataset_id, :x, :y)
                    ON CONFLICT (node_id) DO UPDATE SET x = :x, y = :y
                """), {
                    'node_id': row['customer_id'],
                    'dataset_id': dataset_id,
                    'x': float(row['x']),
                    'y': float(row['y'])
                })
                node_count += 1

            print(f"  ✓ Inserted {node_count} nodes")

            # 3. Insert depots
            print(f"\n🏭 Inserting depots...")
            for _, row in depots_df.iterrows():
                session.execute(text("""
                    INSERT INTO depots (depot_id, node_id, dataset_id)
                    VALUES (:depot_id, :node_id, :dataset_id)
                    ON CONFLICT (depot_id) DO UPDATE SET node_id = :node_id
                """), {
                    'depot_id': row['depot_id'],
                    'node_id': row['depot_id'],
                    'dataset_id': dataset_id
                })
            print(f"  ✓ Inserted {len(depots_df)} depots")

            # 4. Insert customers
            print(f"\n👥 Inserting customers...")
            for _, row in customers_df.iterrows():
                session.execute(text("""
                    INSERT INTO customers (customer_id, node_id, dataset_id, deadline_hours)
                    VALUES (:customer_id, :node_id, :dataset_id, :deadline_hours)
                    ON CONFLICT (customer_id) DO UPDATE SET deadline_hours = :deadline_hours
                """), {
                    'customer_id': row['customer_id'],
                    'node_id': row['customer_id'],
                    'dataset_id': dataset_id,
                    'deadline_hours': int(row['deadline_hours'])
                })
            print(f"  ✓ Inserted {len(customers_df)} customers")

            # 5. Insert vehicles
            print(f"\n🚚 Inserting vehicles...")
            for _, row in vehicles_df.iterrows():
                session.execute(text("""
                    INSERT INTO vehicles (vehicle_id, depot_id, dataset_id, vehicle_type, capacity_kg, max_operational_hrs, speed_kmh)
                    VALUES (:vehicle_id, :depot_id, :dataset_id, :vehicle_type, :capacity_kg, :max_operational_hrs, :speed_kmh)
                    ON CONFLICT (vehicle_id) DO UPDATE SET
                        depot_id = :depot_id,
                        vehicle_type = :vehicle_type,
                        capacity_kg = :capacity_kg,
                        max_operational_hrs = :max_operational_hrs,
                        speed_kmh = :speed_kmh
                """), {
                    'vehicle_id': row['vehicle_id'],
                    'depot_id': row['depot_id'],
                    'dataset_id': dataset_id,
                    'vehicle_type': row['vehicle_type'],
                    'capacity_kg': float(row['capacity_kg']),
                    'max_operational_hrs': float(row['max_operational_hrs']),
                    'speed_kmh': float(row['speed_kmh'])
                })
            print(f"  ✓ Inserted {len(vehicles_df)} vehicles")

            # 6. Insert items
            print(f"\n📦 Inserting items...")
            for _, row in items_df.iterrows():
                session.execute(text("""
                    INSERT INTO items (item_id, dataset_id, weight_kg, expiry_hours)
                    VALUES (:item_id, :dataset_id, :weight_kg, :expiry_hours)
                    ON CONFLICT (item_id) DO UPDATE SET
                        weight_kg = :weight_kg,
                        expiry_hours = :expiry_hours
                """), {
                    'item_id': row['item_id'],
                    'dataset_id': dataset_id,
                    'weight_kg': float(row['weight_kg']),
                    'expiry_hours': int(row['expiry_hours'])
                })
            print(f"  ✓ Inserted {len(items_df)} items")

            # 7. Insert orders
            print(f"\n📋 Inserting orders...")
            order_count = 0
            for _, row in orders_df.iterrows():
                session.execute(text("""
                    INSERT INTO orders (customer_id, item_id, dataset_id, quantity)
                    VALUES (:customer_id, :item_id, :dataset_id, :quantity)
                """), {
                    'customer_id': row['customer_id'],
                    'item_id': row['item_id'],
                    'dataset_id': dataset_id,
                    'quantity': int(row['quantity'])
                })
                order_count += 1
            print(f"  ✓ Inserted {order_count} orders")

        print("\n" + "=" * 50)
        print("✅ SUCCESS! Database populated successfully!")
        print("=" * 50)
        print(f"\nDataset {dataset_id} '{dataset_name}' is ready to use!")
        print(f"\nYou can now load it with:")
        print(f"  from src.data_loader import MDVRPDataLoader")
        print(f"  from src.database import DatabaseConnection")
        print(f"  conn = DatabaseConnection('{db_url}')")
        print(f"  loader = MDVRPDataLoader()")
        print(f"  data = loader.load_from_database(conn, dataset_id={dataset_id})")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        raise
    finally:
        session.close()


def main():
    """Main entry point."""
    if len(sys.argv) < 4:
        print("Usage: python populate_database.py <dataset_id> <dataset_name> <database_url> [data_dir]")
        print("\nExample:")
        print('  python populate_database.py 1 "Test Dataset" "postgresql://mdvrp:mdvrp@localhost:5432/mdvrp"')
        print("\nOptional data_dir argument:")
        print('  python populate_database.py 1 "Test Dataset" "postgresql://mdvrp:mdvrp@localhost:5432/mdvrp" "data"')
        sys.exit(1)

    dataset_id = int(sys.argv[1])
    dataset_name = sys.argv[2]
    db_url = sys.argv[3]
    data_dir = sys.argv[4] if len(sys.argv) > 4 else 'data'

    try:
        populate_dataset(dataset_id, dataset_name, db_url, data_dir)
    except Exception as e:
        print(f"\nFailed to populate database: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
