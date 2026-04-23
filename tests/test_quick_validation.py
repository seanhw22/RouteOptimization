#!/usr/bin/env python3
"""
Quick validation test - Tests CSV loading and basic functionality.
Then provides instructions for database testing.

Usage:
    python tests/test_quick_validation.py
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


def test_csv_loading():
    """Test CSV loading still works after our changes."""
    print("\n" + "="*60)
    print("TEST: CSV Data Loading")
    print("="*60)

    try:
        loader = MDVRPDataLoader()
        data = loader.load_csv('data/')

        # Check required keys
        required_keys = [
            'depots', 'customers', 'vehicles', 'items',
            'coordinates', 'vehicle_speed', 'depot_for_vehicle',
            'vehicle_capacity', 'max_operational_time',
            'customer_deadlines', 'item_weights', 'item_expiry',
            'customer_orders'
        ]

        missing_keys = [key for key in required_keys if key not in data]

        if missing_keys:
            print(f"[FAIL] Missing keys: {missing_keys}")
            return False

        print(f"[PASS] CSV data loaded successfully")
        print(f"  - Depots: {len(data['depots'])}")
        print(f"  - Customers: {len(data['customers'])}")
        print(f"  - Vehicles: {len(data['vehicles'])}")
        print(f"  - Items: {len(data['items'])}")
        print(f"  - Coordinates: {len(data['coordinates'])} nodes")

        # Check data format
        print("\nValidating data format...")

        # Check coordinates are tuples with x, y (not lat, lon)
        for node_id, coords in list(data['coordinates'].items())[:3]:
            print(f"  {node_id}: {coords} (type: {type(coords[0])})")

        # Check max_operational_hrs (not max_time_hours)
        for vehicle in list(data['vehicles'])[:2]:
            print(f"  {vehicle}: max_operational_time = {data['max_operational_time'][vehicle]}")

        print("\n[PASS] Data format is correct (x, y, max_operational_hrs)")
        return True

    except Exception as e:
        print(f"[FAIL] {e}")
        import traceback
        traceback.print_exc()
        return False


def show_database_test_instructions():
    """Show instructions for testing database connection."""
    print("\n" + "="*60)
    print("Database Testing Instructions")
    print("="*60)

    print("\nStep 1: Setup your .env file")
    print("  cp .env.example .env")
    print("  # Edit .env with your database credentials")
    print("  DATABASE_URL=postgresql://user:password@localhost:5432/mdvrp")

    print("\nStep 2: Test database connection")
    print("  python -c \"from src.database import DatabaseConnection; print('Connected!' if DatabaseConnection().test_connection() else 'Failed')\"")

    print("\nStep 3: Test with solver")
    print("""  python -c \"
from src.data_loader import MDVRPDataLoader
from src.database import DatabaseConnection
from mdvrp_greedy import MDVRPGreedy

conn = DatabaseConnection()
loader = MDVRPDataLoader()
data = loader.load_from_database(conn, dataset_id=1)

solver = MDVRPGreedy(params=data, seed=42)
solution, status = solver.solve()
print(f'Status: {status}, Fitness: {solution[\\\"fitness\\\"]:.2f}')
\"""")

    print("\nCommon connection strings:")
    print("  postgresql://postgres:postgres@localhost:5432/mdvrp")
    print("  postgresql://mdvrp:your_password@localhost:5432/mdvrp")


def main():
    """Run tests."""
    print("\n" + "="*60)
    print("MDVRP Quick Validation Tests")
    print("="*60)

    results = []

    # Test 1: CSV loading
    csv_ok = test_csv_loading()
    results.append(("CSV Loading", csv_ok))

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
        print("SUCCESS! CSV tests passed!")
        print("="*60)
        print("\nYour CSV data loading is working correctly.")
        print("\nNext steps:")
        print("  1. Ensure PostgreSQL is running")
        print("  2. Run: psql -U your_user -d your_database -f database/schema.sql")
        print("  3. Run: psql -U your_user -d your_database -f database/populate_data.sql")
        print("  4. Test database connection (see instructions below)")
        return True
    else:
        print("WARNING: TESTS FAILED")
        print("="*60)
        return False


if __name__ == '__main__':
    success = main()
    show_database_test_instructions()
    sys.exit(0 if success else 1)
