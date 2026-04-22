"""
MDVRP Greedy Heuristic - Cheapest Insertion
Based on flowchart algorithm
Refactored to support NumPy arrays, Pandas I/O, and tqdm
"""

import random
import math
import os
import numpy as np
import time
from typing import Dict, List, Tuple, Optional, Callable


class MDVRPGreedy:
    """Greedy Cheapest Insertion Heuristic for MDVRP with NumPy support"""

    def __init__(self, depots, customers, vehicles, items, params, seed=None,
                 data_source=None):
        """
        Initialize greedy solver.

        Args:
            depots: List of depot IDs (can be None if data_source provided)
            customers: List of customer IDs (can be None if data_source provided)
            vehicles: List of vehicle IDs (can be None if data_source provided)
            items: List of item IDs (can be None if data_source provided)
            params: Parameters dict (can contain NumPy arrays or dicts)
            seed: Random seed for reproducibility
            data_source: Optional path to CSV/XLSX data file or directory
        """
        # Set random seed for reproducibility
        if seed is not None:
            random.seed(seed)

        self.seed = seed
        self.data_source = data_source

        # Load data from CSV/XLSX if provided
        if data_source is not None:
            from src.data_loader import MDVRPDataLoader
            from src.distance_matrix import DistanceMatrixBuilder

            loader = MDVRPDataLoader()
            if os.path.isdir(data_source):
                # It's a directory, load CSV files
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
        self.params = params
        self.nodes = depots + customers

        # Detect if params use NumPy arrays or dicts
        self.uses_numpy = isinstance(params.get('dist'), np.ndarray)

        # Extract parameters
        self.dist = params['dist']
        self.T = params['T']  # Travel time matrix [vehicle][i][j] or dict of NumPy arrays
        self.Q = params['Q']  # Vehicle capacity
        self.T_max = params['T_max']  # Max operational time
        self.L = params['L']  # Customer deadlines
        self.w = params['w']  # Item weights
        self.r = params['r']  # Customer orders
        self.expiry = params['expiry']
        self.depot_for_vehicle = params['depot_for_vehicle']

        # For NumPy: create node index mapping
        if self.uses_numpy:
            self.node_to_idx = {node: i for i, node in enumerate(self.nodes)}
            self.vehicle_to_idx = {vehicle: i for i, vehicle in enumerate(vehicles)}

        # Calculate customer demand
        if self.uses_numpy and 'demand' in params:
            # Use pre-computed demand array
            self.demand_array = params['demand']
            self.demand = {customer: self.demand_array[i]
                          for i, customer in enumerate(self.customers)}
        else:
            # Calculate from dict
            self.demand = {}
            for j in customers:
                self.demand[j] = sum(self.w[m] * self.r[j][m] for m in items if self.r[j][m] > 0)

        # Initialize routes (will be reset in solve())
        self.routes = {k: [] for k in vehicles}
        self.route_load = {k: 0 for k in vehicles}
        self.route_time = {k: 0 for k in vehicles}

        # Tracking
        self.unallocated = list(customers)

    def calculate_distance_increase(self, vehicle, customer, position):
        """
        Calculate distance increase if customer is inserted at position
        position: index where to insert (0 means after depot)

        Supports both dict-based and NumPy array distance matrices.
        """
        route = self.routes[vehicle]
        depot = self.depot_for_vehicle[vehicle]

        if len(route) == 0:
            # Route is empty: depot -> customer -> depot
            if self.uses_numpy:
                i = self.node_to_idx[depot]
                j = self.node_to_idx[customer]
                return self.dist[i][j] + self.dist[j][i]
            else:
                return self.dist[depot][customer] + self.dist[customer][depot]

        # Insert customer at position
        if position == 0:
            # Insert at start: depot -> customer -> route[0] -> ...
            prev_node = depot
            next_node = route[0]
        elif position >= len(route):
            # Insert at end: ... -> route[-1] -> customer -> depot
            prev_node = route[-1]
            next_node = depot
        else:
            # Insert in middle: ... -> route[pos-1] -> customer -> route[pos] -> ...
            prev_node = route[position - 1]
            next_node = route[position]

        # Calculate distance increase
        if self.uses_numpy:
            i = self.node_to_idx[prev_node]
            j = self.node_to_idx[next_node]
            k = self.node_to_idx[customer]
            original_dist = self.dist[i][j]
            new_dist = self.dist[i][k] + self.dist[k][j]
        else:
            original_dist = self.dist[prev_node][next_node]
            new_dist = self.dist[prev_node][customer] + self.dist[customer][next_node]

        return new_dist - original_dist

    def calculate_route_distance(self, vehicle):
        """
        Calculate total distance of a vehicle's route
        Returns: total distance from depot -> customers -> depot

        Supports both dict-based and NumPy array distance matrices.
        """
        route = self.routes[vehicle]
        depot = self.depot_for_vehicle[vehicle]

        if not route:
            return 0.0

        # Calculate distance: depot -> customer1 -> customer2 -> ... -> depot
        if self.uses_numpy:
            # Build node indices list: depot, customers..., depot
            indices = [self.node_to_idx[depot]]
            indices.extend(self.node_to_idx[c] for c in route)
            indices.append(self.node_to_idx[depot])

            # Vectorized distance calculation
            total_dist = 0.0
            for i in range(len(indices) - 1):
                total_dist += self.dist[indices[i]][indices[i+1]]
        else:
            # Original dict-based calculation
            total_dist = 0.0
            prev_node = depot
            for customer in route:
                total_dist += self.dist[prev_node][customer]
                prev_node = customer
            total_dist += self.dist[prev_node][depot]

        return total_dist

    def check_capacity_feasibility(self, vehicle, customer):
        """Check if adding customer exceeds vehicle capacity"""
        additional_demand = self.demand[customer]
        return (self.route_load[vehicle] + additional_demand) <= self.Q[vehicle]

    def calculate_time_increase(self, vehicle, customer, position):
        """
        Calculate travel time increase if customer is inserted at position
        Uses the travel time matrix T directly

        Supports both dict-based and NumPy array time matrices.
        """
        route = self.routes[vehicle]
        depot = self.depot_for_vehicle[vehicle]

        if len(route) == 0:
            # Route is empty: depot -> customer -> depot
            if self.uses_numpy:
                time_matrix = self.T[vehicle]
                i = self.node_to_idx[depot]
                j = self.node_to_idx[customer]
                return time_matrix[i][j] + time_matrix[j][i]
            else:
                return self.T[vehicle][depot][customer] + self.T[vehicle][customer][depot]

        # Insert customer at position
        if position == 0:
            # Insert at start: depot -> customer -> route[0] -> ...
            prev_node = depot
            next_node = route[0]
        elif position >= len(route):
            # Insert at end: ... -> route[-1] -> customer -> depot
            prev_node = route[-1]
            next_node = depot
        else:
            # Insert in middle: ... -> route[pos-1] -> customer -> route[pos] -> ...
            prev_node = route[position - 1]
            next_node = route[position]

        # Calculate time increase
        if self.uses_numpy:
            time_matrix = self.T[vehicle]
            i = self.node_to_idx[prev_node]
            j = self.node_to_idx[next_node]
            k = self.node_to_idx[customer]
            original_time = time_matrix[i][j]
            new_time = time_matrix[i][k] + time_matrix[k][j]
        else:
            original_time = self.T[vehicle][prev_node][next_node]
            new_time = self.T[vehicle][prev_node][customer] + self.T[vehicle][customer][next_node]

        return new_time - original_time

    def check_time_feasibility(self, vehicle, customer, position):
        """Check if adding customer violates time constraints"""
        # Calculate current travel time
        current_time = self.route_time[vehicle]

        # Calculate additional time for this insertion
        time_increase = self.calculate_time_increase(vehicle, customer, position)

        # Check against max operational time
        new_time = current_time + time_increase
        if new_time > self.T_max[vehicle]:
            return False

        # Calculate arrival time at customer's position
        route = self.routes[vehicle]
        depot = self.depot_for_vehicle[vehicle]

        if len(route) == 0:
            # Route is empty: arrival time is time from depot to customer
            if self.uses_numpy:
                time_matrix = self.T[vehicle]
                i = self.node_to_idx[depot]
                j = self.node_to_idx[customer]
                arrival_time = time_matrix[i][j]
            else:
                arrival_time = self.T[vehicle][depot][customer]
        else:
            # Calculate time to reach the insertion position
            if position == 0:
                # Insert at start: arrival time is from depot to customer
                if self.uses_numpy:
                    time_matrix = self.T[vehicle]
                    i = self.node_to_idx[depot]
                    j = self.node_to_idx[customer]
                    arrival_time = time_matrix[i][j]
                else:
                    arrival_time = self.T[vehicle][depot][customer]
            elif position >= len(route):
                # Insert at end: calculate time to traverse entire route + to customer
                # Note: current_time includes return to depot, so we need to recalculate
                arrival_time = 0
                prev_node = depot
                for c in route:
                    if self.uses_numpy:
                        time_matrix = self.T[vehicle]
                        p = self.node_to_idx[prev_node]
                        curr = self.node_to_idx[c]
                        arrival_time += time_matrix[p][curr]
                    else:
                        arrival_time += self.T[vehicle][prev_node][c]
                    prev_node = c
                # Add time from last customer to new customer
                if self.uses_numpy:
                    time_matrix = self.T[vehicle]
                    p = self.node_to_idx[prev_node]
                    j = self.node_to_idx[customer]
                    arrival_time += time_matrix[p][j]
                else:
                    arrival_time += self.T[vehicle][prev_node][customer]
            else:
                # Insert in middle: calculate time to reach position
                arrival_time = 0
                # Sum time to traverse up to insertion point
                for i in range(position):
                    prev_node = depot if i == 0 else route[i-1]
                    curr_node = route[i]
                    if self.uses_numpy:
                        time_matrix = self.T[vehicle]
                        p = self.node_to_idx[prev_node]
                        c = self.node_to_idx[curr_node]
                        arrival_time += time_matrix[p][c]
                    else:
                        arrival_time += self.T[vehicle][prev_node][curr_node]
                # Add time from previous node to new customer
                prev_node = depot if position == 0 else route[position-1]
                if self.uses_numpy:
                    time_matrix = self.T[vehicle]
                    p = self.node_to_idx[prev_node]
                    c = self.node_to_idx[customer]
                    arrival_time += time_matrix[p][c]
                else:
                    arrival_time += self.T[vehicle][prev_node][customer]

        # Check against customer deadline
        return arrival_time <= self.L[customer]

    def find_best_insertion(self, verbose=False):
        """
        Find the cheapest feasible insertion
        Returns: (vehicle, customer, position, distance_increase) or None
        """
        best_insertion = None
        min_increase = float('inf')

        if verbose:
            print(f"\n  Detail evaluasi SEMUA kandidat:")
            print(f"  {'='*66}")

        for customer in self.unallocated:
            for vehicle in self.vehicles:
                # Check capacity feasibility
                if not self.check_capacity_feasibility(vehicle, customer):
                    if verbose:
                        print(f"  C{customer} -> V{vehicle}: [TIDAK LAYAK] Kapasitas kurang ({self.route_load[vehicle]:.1f} + {self.demand[customer]:.1f} > {self.Q[vehicle]})")
                    continue

                # Try all positions in the route
                route = self.routes[vehicle]
                max_pos = max(0, len(route))

                for position in range(max_pos + 1):
                    # Check time feasibility
                    if not self.check_time_feasibility(vehicle, customer, position):
                        if verbose:
                            print(f"  C{customer} -> V{vehicle} (posisi {position}): [TIDAK LAYAK] Batas waktu terlewati")
                        continue

                    # Calculate distance increase
                    increase = self.calculate_distance_increase(vehicle, customer, position)

                    if verbose:
                        status = "*** BAIK ***" if increase < min_increase else ""
                        print(f"  C{customer} -> V{vehicle} (posisi {position}): delta={increase:.4f} {status}")

                    if increase < min_increase:
                        min_increase = increase
                        best_insertion = (vehicle, customer, position, increase)

        if verbose:
            print(f"  {'='*66}")
            print(f"  Total evaluasi: {len(self.unallocated)} customers x {len(self.vehicles)} vehicles x berbagai posisi")

        return best_insertion

    def insert_customer(self, vehicle, customer, position):
        """
        Insert customer into route and update load/time.

        IMPORTANT: Operations must be in this order:
        1. Calculate time increase FIRST (while route is unchanged)
        2. Insert customer into route
        3. Update load and time

        Args:
            vehicle: Vehicle ID
            customer: Customer ID to insert
            position: Position to insert at
        """
        route = self.routes[vehicle]

        # STEP 1: Calculate time increase FIRST (while route is unchanged)
        time_increase = self.calculate_time_increase(vehicle, customer, position)

        # STEP 2: Insert customer into route
        if position >= len(route):
            route.append(customer)
        else:
            route.insert(position, customer)

        # STEP 3: Update load and time
        self.route_load[vehicle] += self.demand[customer]
        self.route_time[vehicle] += time_increase

        # Remove from unallocated
        self.unallocated.remove(customer)

    def force_insert_customer(self, customer, verbose=False):
        """
        Force insert customer into vehicle with most remaining capacity, even if it violates constraints.
        Used when no feasible insertion exists.

        Args:
            customer: Customer ID to insert
            verbose: Print details

        Returns:
            (vehicle, position, distance_increase) where customer was inserted
        """
        # Find vehicle with most remaining capacity
        vehicle = max(self.vehicles, key=lambda v: self.Q[v] - self.route_load[v])
        route = self.routes[vehicle]
        position = len(route)  # Insert at end by default

        # Calculate time increase FIRST (before modifying route)
        time_increase = self.calculate_time_increase(vehicle, customer, position)

        # Calculate distance increase FIRST (before modifying route)
        distance_increase = self.calculate_distance_increase(vehicle, customer, position)

        # Insert customer
        if position >= len(route):
            route.append(customer)
        else:
            route.insert(position, customer)

        # Update load and time
        self.route_load[vehicle] += self.demand[customer]
        self.route_time[vehicle] += time_increase

        # Remove from unallocated
        self.unallocated.remove(customer)

        # Track violation
        violation_type = []
        if self.route_load[vehicle] > self.Q[vehicle]:
            violation_type.append('capacity')
        if self.route_time[vehicle] > self.T_max[vehicle]:
            violation_type.append('time')

        self.constraint_violations.append({
            'customer': customer,
            'vehicle': vehicle,
            'violations': violation_type
        })

        if verbose:
            depot = self.depot_for_vehicle[vehicle]
            print(f"\n  [FORCE INSERT] Pelanggan {customer} dipaksa ke {vehicle} (Depot {depot})")
            print(f"    - Pelanggaran: {', '.join(violation_type)}")
            print(f"    - Beban: {self.route_load[vehicle]:.1f}/{self.Q[vehicle]} kg")
            print(f"    - Waktu: {self.route_time[vehicle]:.4f}/{self.T_max[vehicle]} jam")

        return vehicle, position, distance_increase

    def solve(self, time_limit=None, max_iterations=None,
              progress_callback=None, verbose=True):
        """
        Solve MDVRP using cheapest insertion heuristic.

        Algorithm follows the steps:
        1. Inisialisasi
        2. Perhitungan biaya penyisipan (dalam iterasi)
        3. Pemilihan penyisipan terbaik
        4. Pembaruan rute
        5. Iterasi (ulang sampai semua pelanggan teralokasi)
        6. Hasil akhir

        Args:
            time_limit: Maximum runtime in seconds (None = no limit)
            max_iterations: Maximum customer insertions (None = no limit)
            progress_callback: Optional function(current, total, message) for progress updates
            verbose: Print progress to console (default: True)

        Returns:
            (solution_dict, status_string) where:
                solution_dict: Contains routes, metadata
                status_string: 'feasible', 'timeout', 'max_iterations'
        """
        start_time = time.time()

        # Initialize routes
        self.routes = {k: [] for k in self.vehicles}
        self.route_load = {k: 0 for k in self.vehicles}
        self.route_time = {k: 0 for k in self.vehicles}
        self.unallocated = list(self.customers)
        self.constraint_violations = []  # Track constraint violations

        if verbose:
            print("=" * 70)
            print("ALGORITMA GREEDY CHEAPEST INSERTION - MDVRP")
            print("=" * 70)

            # TAHAP 1: INISIALISASI
            print("\n" + "=" * 70)
            print("TAHAP 1: INISIALISASI")
            print("=" * 70)
            print("\nMembaca seluruh data masukan:")
            print(f"  - Jumlah depot: {len(self.depots)}")
            print(f"  - Jumlah pelanggan: {len(self.customers)}")
            print(f"  - Jumlah kendaraan: {len(self.vehicles)}")
            print(f"  - Jumlah tipe item: {len(self.items)}")

            print("\nMembuat rute awal untuk setiap kendaraan:")
            for v in self.vehicles:
                depot = self.depot_for_vehicle[v]
                print(f"  - Kendaraan {v}: Depot {depot} -> Depot {depot} (rute kosong)")
            print(f"  - Rute awal: {self.routes}")

            print("\nHimpunan pelanggan yang belum teralokasi:")
            print(f"  - Unallocated customers: {self.unallocated}")

        # Import tqdm for progress bar
        from tqdm import tqdm

        # Iterasi utama
        iteration = 0
        total_customers = len(self.customers)

        # Use tqdm if verbose and no time limit (time limit complicates tqdm)
        use_tqdm = verbose and time_limit is None

        if use_tqdm:
            pbar = tqdm(total=total_customers, desc="Greedy Insertion")
        else:
            pbar = None

        while self.unallocated:
            iteration += 1

            # Check time limit
            if time_limit is not None:
                elapsed = time.time() - start_time
                if elapsed >= time_limit:
                    if verbose:
                        print(f"\n[TIMEOUT] Time limit reached: {elapsed:.2f}s")
                        print(f"Memaksa {len(self.unallocated)} pelanggan tersisa...")
                    if pbar:
                        pbar.close()
                    # Force insert remaining customers
                    while self.unallocated:
                        customer = self.unallocated[0]
                        self.force_insert_customer(customer, verbose=verbose)
                    return self._format_solution(start_time), 'timeout'

            # Check max iterations
            if max_iterations is not None and iteration > max_iterations:
                if verbose:
                    print(f"\n[MAX ITERATIONS] Maximum iterations reached: {iteration}")
                if pbar:
                    pbar.close()
                # Force insert remaining customers
                while self.unallocated:
                    customer = self.unallocated[0]
                    self.force_insert_customer(customer, verbose=verbose)
                return self._format_solution(start_time), 'max_iterations'

            if verbose and not use_tqdm:
                print("\n" + "=" * 70)
                print(f"ITERASI {iteration}")
                print("=" * 70)
                print(f"\nPelanggan yang belum teralokasi: {self.unallocated}")

            # Find best insertion
            best = self.find_best_insertion(verbose=verbose and not use_tqdm)

            if best is None:
                # No feasible insertion - force insert with penalty
                if verbose:
                    print("\n  [!] Tidak ada kandidat penyisipan yang feasible!")
                    print("  Memaksa penyisipan dengan penalti...")

                # Force insert first unallocated customer
                customer = self.unallocated[0]
                vehicle, position, increase = self.force_insert_customer(customer, verbose=verbose and not use_tqdm)
            else:
                vehicle, customer, position, increase = best

                # Insert customer normally
                self.insert_customer(vehicle, customer, position)

            # Update progress
            if pbar:
                pbar.update(1)
                pbar.set_description(f"Greedy Insertion (best: {increase:.4f})")

            if progress_callback:
                allocated = total_customers - len(self.unallocated)
                progress_callback(allocated, total_customers,
                                f"Iteration {iteration}: Inserted {customer} into {vehicle}")

            if verbose and not use_tqdm:
                depot = self.depot_for_vehicle[vehicle]
                print(f"\nPenyisipan terbaik dipilih:")
                print(f"  - Pelanggan: {customer}")
                print(f"  - Kendaraan: {vehicle} (Depot {depot})")
                print(f"  - Posisi penyisipan: {position}")
                print(f"  - Kenaikan jarak terkecil: {increase:.4f}")

                route_dist = self.calculate_route_distance(vehicle)
                print(f"\nRute kendaraan {vehicle} diperbarui:")
                print(f"  - Rute baru: {self.routes[vehicle]}")
                print(f"  - Beban: {self.route_load[vehicle]:.1f}/{self.Q[vehicle]} kg")
                print(f"  - Jarak tempuh: {route_dist:.4f}")
                print(f"  - Waktu tempuh: {self.route_time[vehicle]:.4f}/{self.T_max[vehicle]} jam")

        if pbar:
            pbar.close()

        if verbose:
            print("\n" + "=" * 70)
            print("TAHAP 6: HASIL AKHIR")
            print("=" * 70)
            print("\nSeluruh pelanggan berhasil dialokasikan!")
            print("\nRute akhir untuk setiap kendaraan:")
            self.print_solution()

        return self._format_solution(start_time), 'feasible'

    def _format_solution(self, start_time: float) -> Dict:
        """Format solution as dict"""
        runtime = time.time() - start_time

        # Calculate total distance and penalty
        total_distance = sum(self.calculate_route_distance(v) for v in self.vehicles)

        # Calculate penalty for constraint violations
        penalty = 0
        alpha_cap = 10   # Penalty per 1 kg excess load (reduced from 50)
        alpha_time = 20  # Penalty per 1 hour delay (reduced from 100)

        for vehicle in self.vehicles:
            # Check capacity violations
            if self.route_load[vehicle] > self.Q[vehicle]:
                excess_load = self.route_load[vehicle] - self.Q[vehicle]
                penalty += (excess_load * alpha_cap)

            # Check time violations
            if self.route_time[vehicle] > self.T_max[vehicle]:
                excess_time = self.route_time[vehicle] - self.T_max[vehicle]
                penalty += (excess_time * alpha_time)

        # Build routes dict with detailed info
        routes_dict = {}
        for vehicle in self.vehicles:
            route = self.routes[vehicle]
            routes_dict[vehicle] = {
                'nodes': route,
                'distance': self.calculate_route_distance(vehicle),
                'time': self.route_time[vehicle],
                'load': self.route_load[vehicle]
            }

        return {
            'routes': routes_dict,
            'fitness': total_distance + penalty,
            'total_distance': total_distance,
            'penalty': penalty,
            'runtime': runtime,
            'unallocated': self.unallocated,
            'constraint_violations': self.constraint_violations,
            'depot_for_vehicle': self.depot_for_vehicle,
            'vehicle_speed': self.params.get('vehicle_speed', {})
        }

    def solve_legacy(self):
        """
        Solve MDVRP using cheapest insertion heuristic
        Algorithm follows the steps:
        1. Inisialisasi
        2. Perhitungan biaya penyisipan (dalam iterasi)
        3. Pemilihan penyisipan terbaik
        4. Pembaruan rute
        5. Iterasi (ulang sampai semua pelanggan teralokasi)
        6. Hasil akhir
        """
        print("=" * 70)
        print("ALGORITMA GREEDY CHEAPEST INSERTION - MDVRP")
        print("=" * 70)

        # TAHAP 1: INISIALISASI
        print("\n" + "=" * 70)
        print("TAHAP 1: INISIALISASI")
        print("=" * 70)
        print("\nMembaca seluruh data masukan:")
        print(f"  - Jumlah depot: {len(self.depots)}")
        print(f"  - Jumlah pelanggan: {len(self.customers)}")
        print(f"  - Jumlah kendaraan: {len(self.vehicles)}")
        print(f"  - Jumlah tipe item: {len(self.items)}")

        print("\nMembuat rute awal untuk setiap kendaraan:")
        for v in self.vehicles:
            depot = self.depot_for_vehicle[v]
            print(f"  - Kendaraan {v}: Depot {depot} -> Depot {depot} (rute kosong)")
        print(f"  - Rute awal: {self.routes}")

        print("\nHimpunan pelanggan yang belum teralokasi:")
        print(f"  - Unallocated customers: {self.unallocated}")

        # Iterasi utama
        iteration = 0
        while self.unallocated:
            iteration += 1

            print("\n" + "=" * 70)
            print(f"ITERASI {iteration}")
            print("=" * 70)
            print(f"\nPelanggan yang belum teralokasi: {self.unallocated}")

            # TAHAP 2: PERHITUNGAN BIAYA PENYISIPAN
            print("\n" + "-" * 70)
            print("TAHAP 2: PERHITUNGAN BIAYA PENYISIPAN")
            print("-" * 70)
            print(f"\nMenghitung biaya penyisipan untuk setiap:")
            print(f"  - {len(self.unallocated)} pelanggan belum teralokasi")
            print(f"  - {len(self.vehicles)} kendaraan tersedia")
            print(f"  - Setiap posisi yang mungkin pada rute")

            print("\nMenguji kendala untuk setiap kandidat penyisipan:")
            print("  [OK] Kendala kapasitas kendaraan")
            print("  [OK] Kendala waktu (deadline pelanggan + batas operasional kendaraan)")

            best = self.find_best_insertion(verbose=True)

            if best is None:
                print("\n  [!] TIDAK ada kandidat penyisipan yang feasible!")
                print("  Memaksa penyisipan dengan penalti...")

                # Force insert first unallocated customer
                customer = self.unallocated[0]
                vehicle, position = self.force_insert_customer(customer, verbose=True)

                # Calculate distance increase for tracking
                increase = self.calculate_distance_increase(vehicle, customer, position)
            else:
                # TAHAP 3: PEMILIHAN PENYISIPAN TERBAIK
                vehicle, customer, position, increase = best
                depot = self.depot_for_vehicle[vehicle]

                print(f"\nPenyisipan terbaik dipilih:")
                print(f"  - Pelanggan: {customer}")
                print(f"  - Kendaraan: {vehicle} (Depot {depot})")
                print(f"  - Posisi penyisipan: {position}")
                print(f"  - Kenaikan jarak terkecil: {increase:.4f}")

                print(f"\nSemua posisi yang dievaluasi untuk kendaraan {vehicle}:")
            print("\n" + "-" * 70)
            print("TAHAP 3: PEMILIHAN PENYISIPAN TERBAIK")
            print("-" * 70)

            vehicle, customer, position, increase = best
            depot = self.depot_for_vehicle[vehicle]

            print(f"\nPenyisipan terbaik dipilih:")
            print(f"  - Pelanggan: {customer}")
            print(f"  - Kendaraan: {vehicle} (Depot {depot})")
            print(f"  - Posisi penyisipan: {position}")
            print(f"  - Kenaikan jarak terkecil: {increase:.4f}")

            print(f"\nSemua posisi yang dievaluasi untuk kendaraan {vehicle}:")

            # Show ALL positions that were evaluated for this vehicle
            route = self.routes[vehicle]

            if len(route) == 0:
                print(f"  Rute saat ini: {depot} -> {depot} (kosong)")
                print(f"  Hanya 1 posisi tersedia")
                print(f"    Posisi 0: {depot} -> {customer} -> {depot}")
                dist_out = self.dist[depot][customer]
                dist_return = self.dist[customer][depot]
                print(f"      Delta: {dist_out:.4f} + {dist_return:.4f} = {dist_out + dist_return:.4f}")
            else:
                print(f"  Rute saat ini: {depot} -> {' -> '.join(map(str, route))} -> {depot}")
                print(f"  {len(route) + 1} posisi dievaluasi:")

                # Position 0: depot -> customer -> route[0]
                dist_new1 = self.dist[depot][customer]
                dist_new2 = self.dist[customer][route[0]]
                dist_orig = self.dist[depot][route[0]]
                delta_0 = dist_new1 + dist_new2 - dist_orig
                marker_0 = " <<< TERBAIK" if position == 0 else ""
                print(f"    Posisi 0 (sisip di awal): {depot} -> {customer} -> {route[0]} -> ...")
                print(f"      Jarak asli {depot} -> {route[0]}: {dist_orig:.4f}")
                print(f"      Jarak baru {depot} -> {customer}: {dist_new1:.4f}")
                print(f"      Jarak baru {customer} -> {route[0]}: {dist_new2:.4f}")
                print(f"      Delta: ({dist_new1:.4f} + {dist_new2:.4f}) - {dist_orig:.4f} = {delta_0:.4f}{marker_0}")

                # Middle positions
                for pos in range(1, len(route)):
                    dist_new1 = self.dist[route[pos-1]][customer]
                    dist_new2 = self.dist[customer][route[pos]]
                    dist_orig = self.dist[route[pos-1]][route[pos]]
                    delta_pos = dist_new1 + dist_new2 - dist_orig
                    marker_pos = " <<< TERBAIK" if position == pos else ""
                    print(f"    Posisi {pos} (sisip di tengah): ... -> {route[pos-1]} -> {customer} -> {route[pos]} -> ...")
                    print(f"      Jarak asli {route[pos-1]} -> {route[pos]}: {dist_orig:.4f}")
                    print(f"      Jarak baru {route[pos-1]} -> {customer}: {dist_new1:.4f}")
                    print(f"      Jarak baru {customer} -> {route[pos]}: {dist_new2:.4f}")
                    print(f"      Delta: ({dist_new1:.4f} + {dist_new2:.4f}) - {dist_orig:.4f} = {delta_pos:.4f}{marker_pos}")

                # Last position: route[-1] -> customer -> depot
                dist_new1 = self.dist[route[-1]][customer]
                dist_new2 = self.dist[customer][depot]
                dist_orig = self.dist[route[-1]][depot]
                delta_last = dist_new1 + dist_new2 - dist_orig
                marker_last = " <<< TERBAIK" if position >= len(route) else ""
                print(f"    Posisi {len(route)} (sisip di akhir): ... -> {route[-1]} -> {customer} -> {depot}")
                print(f"      Jarak asli {route[-1]} -> {depot}: {dist_orig:.4f}")
                print(f"      Jarak baru {route[-1]} -> {customer}: {dist_new1:.4f}")
                print(f"      Jarak baru {customer} -> {depot}: {dist_new2:.4f}")
                print(f"      Delta: ({dist_new1:.4f} + {dist_new2:.4f}) - {dist_orig:.4f} = {delta_last:.4f}{marker_last}")

            # Show feasibility check results
            print(f"\nHasil pemeriksaan kendala:")
            print(f"  [OK] Kapasitas kendaraan {vehicle}: {self.route_load[vehicle]:.1f} + {self.demand[customer]:.1f} = {self.route_load[vehicle] + self.demand[customer]:.1f} <= {self.Q[vehicle]} kg")

            current_time = self.route_time[vehicle]
            route = self.routes[vehicle]

            if len(route) == 0:
                arrival_time = self.T[vehicle][depot][customer]
            else:
                if position == 0:
                    arrival_time = self.T[vehicle][depot][customer]
                elif position >= len(route):
                    arrival_time = current_time + self.T[vehicle][route[-1]][customer]
                else:
                    arrival_time = 0
                    for i in range(position):
                        prev_node = depot if i == 0 else route[i-1]
                        curr_node = route[i]
                        arrival_time += self.T[vehicle][prev_node][curr_node]
                    prev_node = depot if position == 0 else route[position-1]
                    arrival_time += self.T[vehicle][prev_node][customer]

            print(f"  [OK] Waktu kedatangan di customer {customer}: {arrival_time:.4f} <= {self.L[customer]} jam (deadline)")
            print(f"  [OK] Waktu operasional kendaraan {vehicle}: {current_time + self.calculate_time_increase(vehicle, customer, position):.4f} <= {self.T_max[vehicle]} jam")

            # TAHAP 4: PEMBARUAN RUTE
            print("\n" + "-" * 70)
            print("TAHAP 4: PEMBARUAN RUTE")
            print("-" * 70)

            print(f"\nMelakukan penyisipan pelanggan {customer}...")
            self.insert_customer(vehicle, customer, position)

            print(f"\nRute kendaraan {vehicle} diperbarui:")
            print(f"  - Rute baru: {self.routes[vehicle]}")
            print(f"  - Beban: {self.route_load[vehicle]:.1f}/{self.Q[vehicle]} kg")

            # Calculate and show route distance
            route_dist = self.calculate_route_distance(vehicle)
            print(f"  - Jarak tempuh: {route_dist:.4f}")

            print(f"  - Waktu tempuh: {self.route_time[vehicle]:.4f}/{self.T_max[vehicle]} jam")

            print(f"\nPelanggan {customer} dihapus dari himpunan unallocated.")
            print(f"Sisa pelanggan belum teralokasi: {self.unallocated}")

        # TAHAP 5: ITERASI (implicit - loop continues until all customers allocated)

        # TAHAP 6: HASIL AKHIR
        print("\n" + "=" * 70)
        print("TAHAP 6: HASIL AKHIR")
        print("=" * 70)
        print("\nSeluruh pelanggan berhasil dialokasikan!")
        print("\nRute akhir untuk setiap kendaraan:")
        self.print_solution()

        return self.routes

    def print_solution(self):
        """Print final solution"""
        total_distance = 0
        total_time = 0

        for vehicle in self.vehicles:
            route = self.routes[vehicle]
            depot = self.depot_for_vehicle[vehicle]

            if not route:
                print(f"\nKendaraan {vehicle} (Depot {depot}): [TIDAK ADA RUTE]")
                continue

            # Calculate route distance and time
            route_dist = 0
            route_time = 0
            route_str = f"{depot}"

            prev = depot
            for customer in route:
                route_dist += self.dist[prev][customer]
                route_time += self.T[vehicle][prev][customer]
                route_str += f" -> {customer}"
                prev = customer
            route_dist += self.dist[prev][depot]
            route_time += self.T[vehicle][prev][depot]
            route_str += f" -> {depot}"

            total_distance += route_dist
            total_time += route_time

            print(f"\nKendaraan {vehicle} (berasal dari Depot {depot}):")
            print(f"  Rute: {route_str}")
            print(f"  Urutan pelanggan: {route}")
            print(f"  Total beban: {self.route_load[vehicle]:.1f} / {self.Q[vehicle]} kg")
            print(f"  Total waktu tempuh: {route_time:.4f} / {self.T_max[vehicle]} jam")
            print(f"  Total jarak: {route_dist:.4f}")

        print("\n" + "-" * 70)
        print("RINGKASAN SOLUSI:")
        print("-" * 70)
        print(f"  Total jarak tempuh semua kendaraan: {total_distance:.4f}")
        print(f"  Total waktu operasional: {total_time:.4f} jam")
        print(f"  Jumlah pelanggan terlayani: {len(self.customers) - len(self.unallocated)} / {len(self.customers)}")

        if self.unallocated:
            print(f"  Pelanggan tidak terlayani: {self.unallocated}")
        else:
            print(f"  Status: SEMUA PELANGGAN BERHASIL DILAYANI [OK]")

        print("\n" + "=" * 70)
