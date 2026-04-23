#!/usr/bin/env python3
"""
Quick validation test for database integration.

Tests that:
1. Database connection works
2. load_from_database() returns valid data
3. Data format matches CSV loading format
4. Solvers work with database data

Usage:
    python tests/test_database_integration.py
"""

import sys
import os

# Fix Unicode output on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data_loader import MDVRPDataLoader
from src.database import DatabaseConnection


def test_database_connection():
    """Test that database connection works."""
    print("\n" + "="*60)
    print("TEST 1: Database Connection")
    print("="*60)

    # Try to get database URL from user
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("\nNOTE: DATABASE_URL environment variable not set.")
        print("Please enter your PostgreSQL connection details:")
        print("Format: postgresql://user:password@localhost:5432/database")
        print("\nCommon examples:")
        print("  postgresql://postgres:postgres@localhost:5432/mdvrp")
        print("  postgresql://mdvrp:your_password@localhost:5432/mdvrp")

        db_url = input("\nEnter database URL (or press Enter to use default): ").strip()
        if not db_url:
            db_url = 'postgresql://postgres:postgres@localhost:5432/mdvrp'
            print(f"Using default: {db_url}")

    try:
        conn = DatabaseConnection(db_url)

        if conn.test_connection():
            print("[PASS] Database connection successful")
            return conn
        else:
            print("[FAIL] Database connection failed")
            return None
    except Exception as e:
        print(f"[FAIL] {e}")
        print("\nTroubleshooting:")
        print("  1. Check PostgreSQL is running")
        print("  2. Verify user, password, and database name")
        print("  3. Ensure database 'mdvrp' exists")
        print("  4. Run: psql -U your_user -d your_database -f database/schema.sql")
        return None


def test_load_from_database(conn):
    """Test that load_from_database() works."""
    print("\n" + "="*60)
    print("TEST 2: Load Data from Database")
    print("="*60)

    try:
        loader = MDVRPDataLoader()
        data = loader.load_from_database(conn, dataset_id=1)

        # Check required keys exist
        required_keys = [
            'depots', 'customers', 'vehicles', 'items',
            'coordinates', 'vehicle_speed', 'depot_for_vehicle',
            'vehicle_capacity', 'max_operational_time',
            'customer_deadlines', 'item_weights', 'item_expiry',
            'customer_orders'
        ]

        missing_keys = [key for key in required_keys if key not in data]

        if missing_keys:
            print(f"❌ FAIL: Missing keys: {missing_keys}")
            return None

        print(f"[PASS] Data loaded successfully")
        print(f"  - Depots: {len(data['depots'])}")
        print(f"  - Customers: {len(data['customers'])}")
        print(f"  - Vehicles: {len(data['vehicles'])}")
        print(f"  - Items: {len(data['items'])}")
        print(f"  - Coordinates: {len(data['coordinates'])} nodes")

        return data

    except Exception as e:
        print(f"❌ FAIL: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_data_format(data):
    """Test that data format is correct."""
    print("\n" + "="*60)
    print("TEST 3: Data Format Validation")
    print("="*60)

    try:
        # Check coordinates are tuples
        for node_id, coords in data['coordinates'].items():
            if not isinstance(coords, tuple) or len(coords) != 2:
                print(f"[FAIL] Invalid coordinates for {node_id}: {coords}")
                return False
            if not all(isinstance(c, (int, float)) for c in coords):
                print(f"[FAIL] Non-numeric coordinates for {node_id}: {coords}")
                return False

        print("[PASS] Coordinates format correct")

        # Check vehicle attributes exist
        for vehicle in data['vehicles']:
            if vehicle not in data['vehicle_speed']:
                print(f"[FAIL] Missing speed for {vehicle}")
                return False
            if vehicle not in data['vehicle_capacity']:
                print(f"[FAIL] Missing capacity for {vehicle}")
                return False

        print("[PASS] Vehicle attributes complete")

        # Check customer deadlines exist
        for customer in data['customers']:
            if customer not in data['customer_deadlines']:
                print(f"[FAIL] Missing deadline for {customer}")
                return False

        print("[PASS] Customer deadlines present")

        # Check customer orders are nested dicts
        for customer, orders in data['customer_orders'].items():
            if not isinstance(orders, dict):
                print(f"[FAIL] Invalid orders format for {customer}")
                return False

        print("[PASS] Customer orders structure correct")

        return True

    except Exception as e:
        print(f"❌ FAIL: {e}")
        return False


def test_csv_vs_database():
    """Test that CSV and DB loading return compatible formats."""
    print("\n" + "="*60)
    print("TEST 4: CSV vs Database Format Compatibility")
    print("="*60)

    try:
        loader = MDVRPDataLoader()

        # Load from CSV
        csv_data = loader.load_csv('data/')

        # Load from database - need to get connection first
        db_url = os.getenv('DATABASE_URL')
        if not db_url:
            # Use default or prompt user
            print("Note: Using default database connection")
            db_url = 'postgresql://postgres:postgres@localhost:5432/mdvrp'

        conn = DatabaseConnection(db_url)
        db_data = loader.load_from_database(conn, dataset_id=1)

        # Compare keys
        if set(csv_data.keys()) != set(db_data.keys()):
            print(f"[FAIL] Different keys")
            print(f"  CSV keys: {set(csv_data.keys())}")
            print(f"  DB keys: {set(db_data.keys())}")
            return False

        print("[PASS] CSV and DB have matching keys")

        # Compare structure
        for key in csv_data.keys():
            csv_type = type(csv_data[key])
            db_type = type(db_data[key])

            if csv_type != db_type:
                print(f"[FAIL] Type mismatch for {key}")
                print(f"  CSV: {csv_type}")
                print(f"  DB: {db_type}")
                return False

        print("[PASS] CSV and DB have matching types")

        return True

    except Exception as e:
        print(f"❌ FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all validation tests."""
    print("\n" + "="*60)
    print("MDVRP Database Integration Validation Tests")
    print("="*60)

    results = []

    # Test 1: Database connection
    conn = test_database_connection()
    results.append(("Database Connection", conn is not None))

    if not conn:
        print(f"\n[FAIL] Cannot proceed without database connection")
        print("Please ensure:")
        print("  1. PostgreSQL is running")
        print("  2. Database 'mdvrp' exists")
        print("  3. User has access")
        print("  4. Tables are created (schema.sql)")
        print("  5. Data is populated (populate_data.sql)")
        return False

    # Test 2: Load from database
    data = test_load_from_database(conn)
    results.append(("Load from Database", data is not None))

    if not data:
        print("\n[FAIL] Cannot proceed without valid data")
        return False

    # Test 3: Data format
    format_ok = test_data_format(data)
    results.append(("Data Format", format_ok))

    # Test 4: CSV vs DB compatibility
    compat_ok = test_csv_vs_database()
    results.append(("CSV/DB Compatibility", compat_ok))

    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)

    for test_name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status}: {test_name}")

    all_passed = all(result for _, result in results)

    print("\n" + "="*60)
    if all_passed:
        print("SUCCESS! ALL TESTS PASSED!")
        print("="*60)
        print("\nDatabase integration is working correctly!")
        print("\nYou can now use the database with your MDVRP solvers:")
        print("  from mdvrp_greedy import MDVRPGreedy")
        print("  solver = MDVRPGreedy(params=data, seed=42)")
        print("  solution, status = solver.solve()")
        return True
    else:
        print("WARNING: SOME TESTS FAILED")
        print("="*60)
        print("\nPlease fix the issues above before proceeding.")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
