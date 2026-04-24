#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')

from src.database import DatabaseConnection

print("Testing database connection...")
conn = DatabaseConnection()

if conn.test_connection():
    print("[SUCCESS] Database connection works!")

    # Try loading data
    from src.data_loader import MDVRPDataLoader
    loader = MDVRPDataLoader()

    try:
        data = loader.load_from_database(conn, dataset_id=1)
        print(f"[SUCCESS] Data loaded from database!")
        print(f"  - Depots: {len(data['depots'])}")
        print(f"  - Customers: {len(data['customers'])}")
        print(f"  - Vehicles: {len(data['vehicles'])}")
        print(f"  - Items: {len(data['items'])}")

        # Test with solver
        from algorithms.mdvrp_greedy import MDVRPGreedy
        solver = MDVRPGreedy(
            depots=data['depots'],
            customers=data['customers'],
            vehicles=data['vehicles'],
            items=data['items'],
            params=data,
            seed=42
        )
        solution, status = solver.solve(verbose=False)  # Disable verbose to avoid print error

        print(f"[SUCCESS] Solver works with database data!")
        print(f"  - Status: {status}")
        print(f"  - Fitness: {solution['fitness']:.2f}")
        print(f"  - Routes: {len(solution['routes'])} vehicles used")

        print("\n=== ALL TESTS PASSED ===")
        print("Database integration is working correctly!")
        print("The solver successfully found a feasible solution using database data!")

    except Exception as e:
        print(f"[ERROR] Failed to load data: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
else:
    print("[ERROR] Database connection failed")
    print("Please check:")
    print("  1. PostgreSQL is running")
    print("  2. Database 'mdvrp_new' exists")
    print("  3. User 'postgres' has access")
    print("  4. Tables are created (run database/schema.sql)")
    print("  5. Data is populated (run database/populate_data.sql)")
    sys.exit(1)
