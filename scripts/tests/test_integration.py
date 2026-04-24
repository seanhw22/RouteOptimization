"""
Integration test script for MDVRP solvers
Tests all three solvers with CSV data loading
"""

import time
from algorithms.mdvrp_greedy import MDVRPGreedy
from algorithms.mdvrp_hga import MDVRPHGA
from algorithms.milp import MDVRP


def test_all_solvers_with_csv():
    """Test all three solvers with CSV data loading"""
    print("=" * 70)
    print("INTEGRATION TEST: All Solvers with CSV Data")
    print("=" * 70)

    results = {}

    # Test Greedy Solver
    print("\n1. Testing Greedy Solver with CSV...")
    try:
        greedy = MDVRPGreedy(
            depots=None, customers=None, vehicles=None, items=None,
            params=None, seed=42, data_source='data'
        )
        solution, status = greedy.solve(verbose=False)

        results['greedy'] = {
            'status': status,
            'fitness': solution['fitness'],
            'runtime': solution['runtime'],
            'routes': solution['routes']
        }
        print(f"   [OK] Status: {status}")
        print(f"   [OK] Fitness: {solution['fitness']:.2f}")
        print(f"   [OK] Runtime: {solution['runtime']:.2f}s")
    except Exception as e:
        print(f"   [ERROR] Error: {e}")
        results['greedy'] = {'error': str(e)}

    # Test HGA Solver
    print("\n2. Testing HGA Solver with CSV...")
    try:
        hga = MDVRPHGA(
            depots=None, customers=None, vehicles=None, items=None,
            params=None, seed=42, data_source='data',
            population_size=10, generations=5
        )
        solution, status = hga.solve(verbose=False)

        results['hga'] = {
            'status': status,
            'fitness': solution['fitness'],
            'runtime': solution['runtime'],
            'routes': solution['routes']
        }
        print(f"   [OK] Status: {status}")
        print(f"   [OK] Fitness: {solution['fitness']:.2f}")
        print(f"   [OK] Runtime: {solution['runtime']:.2f}s")
    except Exception as e:
        print(f"   [ERROR] Error: {e}")
        results['hga'] = {'error': str(e)}

    # Test MILP Solver
    print("\n3. Testing MILP Solver with CSV...")
    try:
        milp = MDVRP(
            depots=None, customers=None, vehicles=None, items=None,
            params=None, data_source='data'
        )
        milp.build_model()
        solution, status = milp.solve(verbose=False, time_limit=10)

        results['milp'] = {
            'status': status,
            'fitness': solution['fitness'],
            'runtime': solution['runtime'],
            'routes': solution['routes']
        }
        print(f"   [OK] Status: {status}")
        print(f"   [OK] Fitness: {solution['fitness']:.2f}")
        print(f"   [OK] Runtime: {solution['runtime']:.2f}s")
    except Exception as e:
        print(f"   [ERROR] Error: {e}")
        results['milp'] = {'error': str(e)}

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    for solver, result in results.items():
        if 'error' in result:
            print(f"{solver.upper()}: FAILED - {result['error']}")
        else:
            print(f"{solver.upper()}: SUCCESS")
            print(f"  Status: {result['status']}")
            print(f"  Fitness: {result['fitness']:.2f}")
            print(f"  Runtime: {result['runtime']:.2f}s")
            print(f"  Routes: {list(result['routes'].keys())}")

    return results


if __name__ == "__main__":
    test_all_solvers_with_csv()
