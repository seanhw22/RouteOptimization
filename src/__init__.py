"""
MDVRP Solver Package

Multi-Depot Vehicle Routing Problem solvers with support for:
- Hybrid Genetic Algorithm (HGA)
- Greedy heuristic
- MILP (Gurobi)
"""

__version__ = "1.0.0"

from src.solver_base import load_solver_data, calculate_route_distance
