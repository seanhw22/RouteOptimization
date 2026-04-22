"""
Multi-Depot Vehicle Routing Problem (MDVRP) Implementation
Based on the mathematical model from the PDF reference
Refactored to support Pandas I/O and tqdm progress tracking
"""

import gurobipy as gp
from gurobipy import GRB
import os
from typing import Dict, List, Tuple, Optional, Callable
import time


class MDVRP:
    def __init__(self, depots, customers, vehicles, items, params, data_source=None):
        """
        Initialize MDVRP model

        Parameters:
        -----------
        depots : list
            List of depot indices (can be None if data_source provided)
        customers : list
            List of customer indices (can be None if data_source provided)
        vehicles : list
            List of vehicle indices (can be None if data_source provided)
        items : list
            List of item indices (can be None if data_source provided)
        params : dict
            Dictionary containing all parameters (can be None if data_source provided)
        data_source : str, optional
            Path to CSV directory or XLSX file for loading data
        """
        # Load data from CSV/XLSX if provided
        if data_source is not None:
            from src.data_loader import MDVRPDataLoader
            from src.distance_matrix import DistanceMatrixBuilder

            loader = MDVRPDataLoader()
            if os.path.isdir(data_source):
                data = loader.load_csv(data_source)
            elif data_source.endswith('.xlsx'):
                data = loader.load_xlsx(data_source)
            else:
                raise ValueError(f"Unsupported data source format: {data_source}")

            # Extract data
            depots = data['depots']
            customers = data['customers']
            vehicles = data['vehicles']
            items = data['items']

            # Build matrices using NumPy
            builder = DistanceMatrixBuilder(
                data['coordinates'],
                data['vehicle_speed']
            )
            params = builder.build_all_matrices(
                depots, customers, vehicles, items,
                data['coordinates'], data['vehicle_speed'],
                data['customer_orders'], data['item_weights'],
                data['vehicle_capacity'], data['max_operational_time'],
                data['customer_deadlines'], data['depot_for_vehicle']
            )
            # Merge with original params
            params.update({k: v for k, v in data.items() if k not in params})

        self.depots = depots
        self.customers = customers
        self.vehicles = vehicles
        self.items = items
        self.nodes = depots + customers

        # Store params for later access
        self.params = params

        # Unpack parameters
        self.dist = params['dist']
        self.T = params['T']
        self.Q = params['Q']
        self.T_max = params['T_max']
        self.L = params['L']
        self.w = params['w']
        self.r = params['r']
        self.expiry = params['expiry']
        self.depot_for_vehicle = params['depot_for_vehicle']
        self.M = params['M']

        # Detect if params use NumPy arrays and convert to dicts if needed
        # MILP solver uses dict-based indexing, so convert NumPy to dict
        import numpy as np
        if isinstance(self.dist, np.ndarray):
            # Convert NumPy distance matrix to dict
            dist_dict = {}
            for i, node_i in enumerate(self.nodes):
                dist_dict[node_i] = {}
                for j, node_j in enumerate(self.nodes):
                    dist_dict[node_i][node_j] = self.dist[i][j]
            self.dist = dist_dict

        if isinstance(self.T, dict):
            # Check if values are NumPy arrays
            for k in self.vehicles:
                if isinstance(self.T[k], np.ndarray):
                    # Convert NumPy time matrix to dict
                    time_dict = {}
                    for i, node_i in enumerate(self.nodes):
                        time_dict[node_i] = {}
                        for j, node_j in enumerate(self.nodes):
                            time_dict[node_i][node_j] = self.T[k][i][j]
                    self.T[k] = time_dict

        # Calculate demand for each customer
        self.d = {}
        for j in customers:
            self.d[j] = sum(self.w[m] * self.r[j].get(m, 0) for m in items)

        # Calculate effective deadline for each customer
        self.L_eff = {}
        for j in customers:
            item_expiry_times = [self.expiry[m] for m in items if self.r[j].get(m, 0) == 1]
            if item_expiry_times:
                self.L_eff[j] = min(self.L[j], min(item_expiry_times))
            else:
                self.L_eff[j] = self.L[j]

        self.n = len(customers)

    def build_model(self):
        """Build and solve the MDVRP model"""
        model = gp.Model("MDVRP")
        model.Params.OutputFlag = 1

        # Decision variables
        # x_ijk: 1 if vehicle k moves from node i to node j
        x = {}
        for k in self.vehicles:
            for i in self.nodes:
                for j in self.nodes:
                    if i != j:
                        x[i, j, k] = model.addVar(vtype=GRB.BINARY, name=f"x_{i}_{j}_{k}")

        # u_i: auxiliary variable for subtour elimination (MTZ)
        u = {}
        for i in self.customers:
            u[i] = model.addVar(vtype=GRB.CONTINUOUS, lb=0, name=f"u_{i}")

        # t_jk: arrival time of vehicle k at node j
        t = {}
        for j in self.nodes:
            for k in self.vehicles:
                t[j, k] = model.addVar(vtype=GRB.CONTINUOUS, lb=0, name=f"t_{j}_{k}")

        model.update()

        # Objective function (1): Minimize total distance
        obj = gp.quicksum(
            self.dist[i][j] * x[i, j, k]
            for k in self.vehicles
            for i in self.nodes
            for j in self.nodes
            if i != j
        )
        model.setObjective(obj, GRB.MINIMIZE)

        # Constraint (2): Each customer visited exactly once
        for j in self.customers:
            model.addConstr(
                gp.quicksum(
                    x[i, j, k]
                    for k in self.vehicles
                    for i in self.nodes
                    if i != j
                ) == 1,
                name=f"visit_once_{j}"
            )

        # Constraint (3): Route continuity (flow conservation)
        # Applied to customers AND depots (including vehicle's assigned depot)
        for j in self.customers + self.depots:
            for k in self.vehicles:
                model.addConstr(
                    gp.quicksum(x[i, j, k] for i in self.nodes if i != j) ==
                    gp.quicksum(x[j, h, k] for h in self.nodes if h != j),
                    name=f"flow_{j}_{k}"
                )

        # Constraint (4): Each vehicle leaves its assigned depot at most once
        for k in self.vehicles:
            depot_k = self.depot_for_vehicle[k]
            model.addConstr(
                gp.quicksum(x[depot_k, j, k] for j in self.nodes if j != depot_k) <= 1,
                name=f"depot_out_{k}"
            )

        # Constraint (5): Each vehicle returns to its assigned depot at most once
        for k in self.vehicles:
            depot_k = self.depot_for_vehicle[k]
            model.addConstr(
                gp.quicksum(x[i, depot_k, k] for i in self.nodes if i != depot_k) <= 1,
                name=f"depot_in_{k}"
            )

        # Additional: Prevent vehicles from using depots other than their assigned one
        # This is NECESSARY because PDF constraints (4) and (5) don't explicitly prevent cross-depot routes
        for k in self.vehicles:
            depot_k = self.depot_for_vehicle[k]
            other_depots = [d for d in self.depots if d != depot_k]
            for other_depot in other_depots:
                model.addConstr(
                    gp.quicksum(x[other_depot, j, k] for j in self.nodes if j != other_depot) == 0,
                    name=f"no_from_{k}_{other_depot}"
                )
                model.addConstr(
                    gp.quicksum(x[i, other_depot, k] for i in self.nodes if i != other_depot) == 0,
                    name=f"no_to_{k}_{other_depot}"
                )

        # Constraint (6): MTZ subtour elimination
        for i in self.customers:
            for j in self.customers:
                if i != j:
                    for k in self.vehicles:
                        model.addConstr(
                            u[i] - u[j] + self.n * x[i, j, k] <= self.n - 1,
                            name=f"mtz_{i}_{j}_{k}"
                        )

        # Constraint (7): Vehicle capacity constraint
        for k in self.vehicles:
            model.addConstr(
                gp.quicksum(
                    self.d[j] * gp.quicksum(x[i, j, k] for i in self.nodes if i != j)
                    for j in self.customers
                ) <= self.Q[k],
                name=f"capacity_{k}"
            )

        # Constraint (8): Time starts at 0 from depot
        for k in self.vehicles:
            depot_k = self.depot_for_vehicle[k]
            model.addConstr(
                t[depot_k, k] == 0,
                name=f"time_depot_{k}"
            )

        # Constraint (9): Time flow consistency
        # Applied to customer arrivals (depot time is implicitly 0 at start)
        # Support both T[i][j] (same for all vehicles) and T[k][i][j] (vehicle-specific)
        # Detect structure: check if first value is dict of dicts (3D) or dict of numbers (2D)
        first_key = list(self.T.keys())[0]
        first_value = self.T[first_key]
        # Check if first_value contains dicts (3D) or numbers (2D)
        is_3d_travel_time = isinstance(list(first_value.values())[0], dict)

        for k in self.vehicles:
            for i in self.nodes:
                for j in self.customers:  # Only track time when arriving at customers
                    if i != j:
                        # Get travel time based on structure
                        if is_3d_travel_time:
                            travel_time = self.T[k][i][j]  # Vehicle-specific: T[k][i][j]
                        else:
                            travel_time = self.T[i][j]  # Common: T[i][j]
                        model.addConstr(
                            t[j, k] >= t[i, k] + travel_time - self.M * (1 - x[i, j, k]),
                            name=f"time_flow_{i}_{j}_{k}"
                        )

        # Constraint (10): Time window upper bound (customer deadline & item expiry)
        # Customer must be served before effective deadline (min of customer deadline and item expiry times)
        for j in self.customers:
            for k in self.vehicles:
                model.addConstr(
                    t[j, k] <= self.L_eff[j] + self.M * (1 - gp.quicksum(x[i, j, k] for i in self.nodes if i != j)),
                    name=f"time_window_{j}_{k}"
                )

        # Constraint (11): Maximum operational time per vehicle
        # Vehicle cannot travel longer than T_max[k] (from customer deadline & item expiry perspective)
        for j in self.customers:
            for k in self.vehicles:
                model.addConstr(
                    t[j, k] <= self.T_max[k] + self.M * (1 - gp.quicksum(x[i, j, k] for i in self.nodes if i != j)),
                    name=f"max_time_{j}_{k}"
                )

        self.model = model
        self.x = x
        self.u = u
        self.t = t

        return model

    def solve(self, time_limit=None, mip_gap=None, progress_callback=None,
              verbose=True):
        """
        Solve the MDVRP model using Gurobi MILP solver.

        Args:
            time_limit: Maximum runtime in seconds (None = no limit)
            mip_gap: MIP gap tolerance (None = use default)
            progress_callback: Optional function for progress updates
            verbose: Show progress to console

        Returns:
            (solution_dict, status_string) where:
                solution_dict: Contains routes, objective, metadata
                status_string: 'optimal', 'feasible', 'timeout', or 'infeasible'
        """
        start_time = time.time()

        # Set Gurobi parameters
        if time_limit:
            self.model.Params.TimeLimit = time_limit
        if mip_gap:
            self.model.Params.MIPGap = mip_gap

        # Disable Gurobi output if verbose=False
        if not verbose:
            self.model.Params.OutputFlag = 0

        if verbose:
            print("=" * 70)
            print("SOLVING MDVRP WITH GUROBI MILP SOLVER")
            print("=" * 70)
            print("\nBuilding model...")
            print(f"Variables: {self.model.NumVars}")
            print(f"Constraints: {self.model.NumConstrs}")
            print("\nOptimizing...")

        # Optimize
        self.model.optimize()

        runtime = time.time() - start_time

        # Determine status
        if self.model.status == GRB.OPTIMAL:
            status_str = 'optimal'
        elif self.model.status == GRB.TIME_LIMIT:
            status_str = 'timeout'
        elif self.model.status == GRB.INFEASIBLE:
            status_str = 'infeasible'
        elif self.model.status == GRB.UNBOUNDED:
            status_str = 'unbounded'
        else:
            status_str = 'unknown'

        if verbose:
            print(f"\nSolver Status: {status_str}")
            print(f"Objective Value: {self.model.objVal:.2f}")
            print(f"Runtime: {runtime:.2f}s")

        # Extract solution
        solution = self._extract_solution(runtime)

        return solution, status_str

    def _extract_solution(self, runtime: float) -> Dict:
        """
        Extract solution from Gurobi model.

        Args:
            runtime: Time taken to solve

        Returns:
            Solution dict with routes and metadata
        """
        if self.model.status != GRB.OPTIMAL and self.model.status != GRB.TIME_LIMIT:
            return {
                'objective': None,
                'routes': {},
                'vehicle_distances': {},
                'vehicle_times': {},
                'vehicle_weights': {},
                'runtime': runtime,
                'status': self.model.status
            }

        routes = {}
        vehicle_distances = {}
        vehicle_times = {}
        vehicle_weights = {}

        for k in self.vehicles:
            routes[k] = []
            depot_k = self.depot_for_vehicle[k]

            # Find the route for vehicle k
            current = depot_k
            visited = set()
            total_distance = 0
            max_time = 0
            total_weight = 0

            while True:
                found_next = False
                for j in self.nodes:
                    if j != current and j not in visited:
                        if self.x[current, j, k].X > 0.5:  # Binary variable
                            routes[k].append((current, j))

                            # Accumulate distance
                            total_distance += self.dist[current][j]

                            # Track maximum arrival time
                            if j in self.customers:
                                arrival_time = self.t[j, k].X
                                if arrival_time > max_time:
                                    max_time = arrival_time

                                # Accumulate weight (demand) for each customer visited
                                total_weight += self.d[j]

                            visited.add(j)
                            current = j
                            found_next = True
                            break

                if not found_next or current == depot_k:
                    break

            vehicle_distances[k] = total_distance
            vehicle_times[k] = max_time
            vehicle_weights[k] = total_weight

        # Build routes dict in unified format
        routes_dict = {}
        for k in self.vehicles:
            # Convert edge list to node list (only customers, not depots)
            nodes_list = []
            for edge in routes[k]:
                destination = edge[1]
                # Only add customers to the node list, not depots
                if destination in self.customers:
                    nodes_list.append(destination)
            routes_dict[k] = {
                'nodes': nodes_list,
                'distance': vehicle_distances[k],
                'time': vehicle_times[k],
                'load': vehicle_weights[k]
            }

        solution = {
            'fitness': self.model.objVal,
            'routes': routes_dict,
            'objective': self.model.objVal,
            'vehicle_distances': vehicle_distances,
            'vehicle_times': vehicle_times,
            'vehicle_weights': vehicle_weights,
            'runtime': runtime,
            'status': self.model.status,
            'depot_for_vehicle': self.depot_for_vehicle,
            'vehicle_speed': self.params.get('vehicle_speed', {})
        }

        return solution

    def get_solution(self):
        """Extract and return the solution"""
        if self.model.status != GRB.OPTIMAL and self.model.status != GRB.TIME_LIMIT:
            print("No solution found!")
            return None

        routes = {}
        vehicle_distances = {}
        vehicle_times = {}
        vehicle_weights = {}

        for k in self.vehicles:
            routes[k] = []
            depot_k = self.depot_for_vehicle[k]

            # Find the route for vehicle k
            current = depot_k
            visited = set()
            total_distance = 0
            max_time = 0
            total_weight = 0

            while True:
                found_next = False
                for j in self.nodes:
                    if j != current and j not in visited:
                        if self.x[current, j, k].X > 0.5:  # Binary variable
                            routes[k].append((current, j))

                            # Accumulate distance
                            total_distance += self.dist[current][j]

                            # Track maximum arrival time
                            if j in self.customers:
                                arrival_time = self.t[j, k].X
                                if arrival_time > max_time:
                                    max_time = arrival_time

                                # Accumulate weight (demand) for each customer visited
                                total_weight += self.d[j]

                            visited.add(j)
                            current = j
                            found_next = True
                            break

                if not found_next or current == depot_k:
                    break

            vehicle_distances[k] = total_distance
            vehicle_times[k] = max_time
            vehicle_weights[k] = total_weight

        solution = {
            'objective': self.model.objVal,
            'routes': routes,
            'vehicle_distances': vehicle_distances,
            'vehicle_times': vehicle_times,
            'vehicle_weights': vehicle_weights,
            'status': self.model.status
        }

        return solution

    def print_solution(self):
        """Print the solution in a readable format"""
        sol = self.get_solution()
        if sol is None:
            return

        print(f"\n{'='*60}")
        print(f"Total Distance: {sol['objective']:.2f}")
        print(f"{'='*60}\n")

        for k, route in sol['routes'].items():
            if route:
                # Use string identifiers directly instead of adding 1
                depot_name = self.depot_for_vehicle[k]
                print(f"Vehicle {k} (from depot {depot_name}):")
                print(f"  Capacity: {self.Q[k]}")
                print(f"  Travel Distance: {sol['vehicle_distances'][k]:.2f}")
                print(f"  Travel Time: {sol['vehicle_times'][k]:.2f}")
                print(f"  Total Weight: {sol['vehicle_weights'][k]:.2f}")
                print(f"  Route: ", end="")

                current_depot = self.depot_for_vehicle[k]
                path = [current_depot]

                for i, j in route:
                    path.append(j)

                print(" -> ".join(map(str, path)))
                print()
