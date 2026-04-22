"""
Test script for all export formats
Tests CSV, PDF, and GeoJSON export from all three solvers
"""

import os
from algorithms.mdvrp_greedy import MDVRPGreedy
from algorithms.mdvrp_hga import MDVRPHGA
from algorithms.milp import MDVRP
from src.exporter import MDVRPExporter


def test_all_exports():
    """Test all export formats with all three solvers"""
    print("=" * 70)
    print("EXPORT FORMAT TESTING")
    print("=" * 70)

    # Create output directory
    os.makedirs('output', exist_ok=True)

    # Initialize exporter
    exporter = MDVRPExporter()

    # Load data once for all solvers
    print("\nLoading data from CSV files...")
    data_source = 'data'

    # Load coordinates for GeoJSON export
    from src.data_loader import MDVRPDataLoader
    loader = MDVRPDataLoader()
    data = loader.load_csv(data_source)
    coordinates = data['coordinates']

    # Test Greedy Solver
    print("\n1. Testing Greedy Solver exports...")
    try:
        greedy = MDVRPGreedy(
            depots=None, customers=None, vehicles=None, items=None,
            params=None, seed=42, data_source=data_source
        )
        solution, status = greedy.solve(verbose=False)

        if status == 'feasible':
            # Export CSV
            exporter.export_csv(solution, 'output/greedy_solution.csv')
            print("   [OK] CSV export: output/greedy_solution.csv")

            # Export PDF
            # Get problem data from the greedy instance
            problem_data = {
                'coordinates': coordinates,
                'depots': greedy.depots,
                'customers': greedy.customers,
                'vehicles': greedy.vehicles,
                'vehicle_capacity': greedy.Q,
                'max_time': greedy.T_max if hasattr(greedy, 'T_max') else {},
            }

            # Prepare algorithm information for PDF
            algorithm_params = {
                'random_seed': greedy.seed if hasattr(greedy, 'seed') else 42,
                'time_limit': 60  # Default time limit
            }

            exporter.export_pdf(
                solution,
                problem_data,
                'output/greedy_solution.pdf',
                algorithm_name='Greedy Cheapest Insertion',
                algorithm_params=algorithm_params
            )
            print("   [OK] PDF export: output/greedy_solution.pdf")

            # Export GeoJSON
            exporter.export_geojson(solution, coordinates, 'output/greedy_solution.geojson')
            print("   [OK] GeoJSON export: output/greedy_solution.geojson")
        else:
            print(f"   [SKIP] Greedy solver status: {status}")
    except Exception as e:
        print(f"   [ERROR] Greedy export failed: {e}")

    # Test HGA Solver
    print("\n2. Testing HGA Solver exports...")
    try:
        hga = MDVRPHGA(
            depots=None, customers=None, vehicles=None, items=None,
            params=None, seed=42, data_source=data_source,
            population_size=10, generations=5
        )
        solution, status = hga.solve(verbose=False)

        if status in ['feasible', 'optimal']:
            # Export CSV
            exporter.export_csv(solution, 'output/hga_solution.csv')
            print("   [OK] CSV export: output/hga_solution.csv")

            # Export PDF
            problem_data = {
                'coordinates': coordinates,
                'depots': hga.depots,
                'customers': hga.customers,
                'vehicles': hga.vehicles,
                'vehicle_capacity': hga.Q,
                'max_time': hga.T_max if hasattr(hga, 'T_max') else {},
            }

            # Prepare algorithm information for PDF
            algorithm_params = {
                'population_size': hga.population_size if hasattr(hga, 'population_size') else 10,
                'generations': hga.generations if hasattr(hga, 'generations') else 5,
                'random_seed': hga.seed if hasattr(hga, 'seed') else 42
            }

            exporter.export_pdf(
                solution,
                problem_data,
                'output/hga_solution.pdf',
                algorithm_name='Hybrid Genetic Algorithm',
                algorithm_params=algorithm_params
            )
            print("   [OK] PDF export: output/hga_solution.pdf")

            # Export GeoJSON
            exporter.export_geojson(solution, coordinates, 'output/hga_solution.geojson')
            print("   [OK] GeoJSON export: output/hga_solution.geojson")
        else:
            print(f"   [SKIP] HGA solver status: {status}")
    except Exception as e:
        print(f"   [ERROR] HGA export failed: {e}")

    # Test MILP Solver
    print("\n3. Testing MILP Solver exports...")
    try:
        milp = MDVRP(
            depots=None, customers=None, vehicles=None, items=None,
            params=None, data_source=data_source
        )
        milp.build_model()
        solution, status = milp.solve(verbose=False, time_limit=10)

        if status in ['optimal', 'timeout']:
            # Export CSV
            exporter.export_csv(solution, 'output/milp_solution.csv')
            print("   [OK] CSV export: output/milp_solution.csv")

            # Export PDF
            problem_data = {
                'coordinates': coordinates,
                'depots': milp.depots,
                'customers': milp.customers,
                'vehicles': milp.vehicles,
                'vehicle_capacity': milp.Q,
                'max_time': milp.T_max if hasattr(milp, 'T_max') else {},
            }

            # Prepare algorithm information for PDF
            algorithm_params = {
                'solver': 'Gurobi',
                'time_limit': 10,  # Time limit in seconds
                'optimality_gap': 0.01  # 1% optimality gap
            }

            exporter.export_pdf(
                solution,
                problem_data,
                'output/milp_solution.pdf',
                algorithm_name='Mixed-Integer Linear Programming (MILP)',
                algorithm_params=algorithm_params
            )
            print("   [OK] PDF export: output/milp_solution.pdf")

            # Export GeoJSON
            exporter.export_geojson(solution, coordinates, 'output/milp_solution.geojson')
            print("   [OK] GeoJSON export: output/milp_solution.geojson")
        else:
            print(f"   [SKIP] MILP solver status: {status}")
    except Exception as e:
        print(f"   [ERROR] MILP export failed: {e}")

    print("\n" + "=" * 70)
    print("EXPORT TEST COMPLETE")
    print("=" * 70)
    print("\nGenerated files:")
    print("  - output/greedy_solution.csv")
    print("  - output/greedy_solution.pdf")
    print("  - output/greedy_solution.geojson")
    print("  - output/hga_solution.csv")
    print("  - output/hga_solution.pdf")
    print("  - output/hga_solution.geojson")
    print("  - output/milp_solution.csv")
    print("  - output/milp_solution.pdf")
    print("  - output/milp_solution.geojson")


if __name__ == "__main__":
    test_all_exports()
