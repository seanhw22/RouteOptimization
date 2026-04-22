"""
MDVRP Hybrid Genetic Algorithm with DEAP framework
Refactored to use DEAP, NumPy, Pandas, and tqdm
"""

import random
import copy
import math
import os
import numpy as np
import time
from typing import Dict, List, Tuple, Optional, Callable

# DEAP imports
from deap import base, creator, tools, algorithms


# Define Individual class for DEAP (before MDVRPHGA)
class Individual(list):
    """Individual represented as list - DEAP will inherit from this"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.routes = {}
        self.fitness = None
        self.total_distance = 0
        self.total_time = 0
        self.penalty = 0


class MDVRPHGA:
    """Hybrid Genetic Algorithm for MDVRP with DEAP framework"""

    def __init__(self, depots, customers, vehicles, items, params,
                 population_size=20, generations=20, elite_size=3,
                 mutation_rate=0.2, crossover_rate=0.8, tournament_size=3,
                 seed=None, data_source=None):
        """
        Initialize HGA solver with DEAP framework.

        Args:
            depots: List of depot IDs
            customers: List of customer IDs
            vehicles: List of vehicle IDs
            items: List of item IDs
            params: Parameters dict (can contain NumPy arrays or dicts)
            population_size: GA population size
            generations: Number of generations
            elite_size: Number of elite individuals to preserve
            mutation_rate: Probability of mutation
            crossover_rate: Probability of crossover
            tournament_size: Tournament selection size
            seed: Random seed for reproducibility
            data_source: Optional path to CSV/XLSX data file
        """
        # Set random seed for reproducibility
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)

        self.seed = seed
        self.data_source = data_source

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
        self.params = params
        self.nodes = depots + customers

        # GA parameters
        self.population_size = population_size
        self.generations = generations
        self.elite_size = elite_size
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.tournament_size = tournament_size

        # Detect if params use NumPy arrays or dicts
        self.uses_numpy = isinstance(params.get('dist'), np.ndarray)

        # Extract parameters
        self.dist = params['dist']
        self.T = params['T']
        self.Q = params['Q']
        self.T_max = params['T_max']
        self.L = params['L']
        self.w = params['w']
        self.r = params['r']
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

        # Setup DEAP framework
        self._setup_deap()

    def _setup_deap(self):
        """Configure DEAP creator and toolbox"""

        # Create fitness and individual classes if not already created
        if not hasattr(creator, "FitnessMin"):
            creator.create("FitnessMin", base.Fitness, weights=(-1.0,))
        if not hasattr(creator, "Individual"):
            creator.create("Individual", list, fitness=creator.FitnessMin)

        # Initialize toolbox
        self.toolbox = base.Toolbox()

        # Register individual generator FIRST
        self.toolbox.register("individual", self._generate_individual)

        # Register genetic operators
        self.toolbox.register("mate", self._ox_crossover)
        self.toolbox.register("mutate", self._mutation_pipeline)
        self.toolbox.register("select", self._tournament_selection,
                              tournament_size=self.tournament_size)
        self.toolbox.register("evaluate", self._calculate_fitness)

        # Register population initializer (uses individual)
        self.toolbox.register("population", tools.initRepeat,
                              list, self.toolbox.individual)

    def _generate_individual(self):
        """Generate a random individual for initial population"""
        # Shuffle customers randomly
        unallocated = list(self.customers)
        random.shuffle(unallocated)

        # Initialize routes
        routes = {k: [] for k in self.vehicles}

        # Random assignment for each customer
        for customer in unallocated:
            # Find all valid (vehicle, position) pairs
            valid_assignments = []

            for vehicle in self.vehicles:
                if not self._check_capacity(vehicle, customer, routes):
                    continue

                route = routes[vehicle]
                for pos in range(len(route) + 1):
                    if self._check_time(vehicle, customer, pos, routes):
                        valid_assignments.append((vehicle, pos))

            if not valid_assignments:
                # No feasible position - force to least loaded (will get penalty)
                vehicle = min(self.vehicles,
                              key=lambda v: sum(self.demand[c] for c in routes[v]))
                route = routes[vehicle]
                position = random.randint(0, len(route))
                route.insert(position, customer)
            else:
                # Randomly choose from feasible assignments
                vehicle, position = random.choice(valid_assignments)
                routes[vehicle].insert(position, customer)

        # Encode routes to chromosome
        chromosome = self._encode_from_routes(routes)

        # Create Individual object with the chromosome
        ind = creator.Individual(chromosome)
        ind.routes = routes

        return ind

    def _encode_from_routes(self, routes_dict: Dict) -> List:
        """Encode routes dictionary to linear chromosome"""
        chromosome = []

        # Find ordering of depots in chromosome
        # Start with first depot
        first_depot = self.depot_for_vehicle[self.vehicles[0]]
        chromosome.append(first_depot)

        # Add customers for first vehicle
        for customer in routes_dict[self.vehicles[0]]:
            chromosome.append(customer)

        # Add other depots and their customers
        for vehicle in self.vehicles[1:]:
            depot = self.depot_for_vehicle[vehicle]
            chromosome.append(depot)
            for customer in routes_dict[vehicle]:
                chromosome.append(customer)

        # Close the chromosome with starting depot
        chromosome.append(first_depot)

        return chromosome

    def _decode_chromosome(self, chromosome: List) -> Dict:
        """Decode linear chromosome to routes dictionary"""
        routes = {k: [] for k in self.vehicles}

        if not chromosome:
            return routes

        # Find start depot (first element)
        current_depot = chromosome[0]

        # Build routes by parsing chromosome
        current_route = []
        for gene in chromosome[1:]:
            if gene in self.depots:
                # This is a depot, save current route and start new one
                if current_route:
                    # Find which vehicle owns this depot
                    for v in self.vehicles:
                        if self.depot_for_vehicle[v] == current_depot:
                            routes[v] = list(current_route)
                            break
                current_depot = gene
                current_route = []
            else:
                # This is a customer
                current_route.append(gene)

        # Don't forget the last route
        if current_route:
            for v in self.vehicles:
                if self.depot_for_vehicle[v] == current_depot:
                    routes[v] = list(current_route)
                    break

        return routes

    def _calculate_fitness(self, individual: List) -> Tuple:
        """
        Calculate fitness using NumPy vectorization.

        Returns tuple (fitness,) for DEAP.
        """
        # Decode chromosome to routes
        routes = self._decode_chromosome(individual)

        # CRITICAL: Ensure all customers are in routes
        served_customers = set()
        for vehicle in self.vehicles:
            route = routes[vehicle]
            if route:
                served_customers.update(c for c in route if c is not None)

        # If any customers are missing, add them to the least-loaded vehicle
        missing_customers = set(self.customers) - served_customers
        if missing_customers:
            # Find least-loaded vehicle
            least_loaded_vehicle = min(
                self.vehicles,
                key=lambda v: sum(self.demand[c] for c in routes[v])
            )
            # Add missing customers to this vehicle
            routes[least_loaded_vehicle].extend(list(missing_customers))

        # Calculate total distance and penalty
        total_distance = 0
        total_penalty = 0

        # Penalty weights
        alpha_cap = 50   # Penalty per 1 kg excess load (reduced from 50)
        alpha_time = 100  # Penalty per 1 hour delay (reduced from 100)

        for vehicle in self.vehicles:
            route = routes[vehicle]
            depot = self.depot_for_vehicle[vehicle]

            if not route:
                continue

            # Filter out None values from route (defensive programming)
            route = [c for c in route if c is not None]

            # Calculate route distance, time, and load
            route_dist = 0
            route_time = 0
            route_load = sum(self.demand[c] for c in route)

            if self.uses_numpy:
                # Use NumPy arrays
                time_matrix = self.T[vehicle]
                indices = [self.node_to_idx[depot]]
                indices.extend(self.node_to_idx[c] for c in route)
                indices.append(self.node_to_idx[depot])

                for i in range(len(indices) - 1):
                    route_dist += self.dist[indices[i]][indices[i+1]]
                    route_time += time_matrix[indices[i]][indices[i+1]]
            else:
                # Use dict-based matrices
                prev = depot
                for customer in route:
                    route_dist += self.dist[prev][customer]
                    route_time += self.T[vehicle][prev][customer]
                    prev = customer
                route_dist += self.dist[prev][depot]
                route_time += self.T[vehicle][prev][depot]

            total_distance += route_dist

            # Check capacity violations
            if route_load > self.Q[vehicle]:
                excess_load = route_load - self.Q[vehicle]
                total_penalty += (excess_load * alpha_cap)

            # Check time violations
            if route_time > self.T_max[vehicle]:
                excess_time = route_time - self.T_max[vehicle]
                total_penalty += (excess_time * alpha_time)

        fitness = total_distance + total_penalty

        # Store for display (if individual has these attributes)
        if hasattr(individual, 'routes'):
            individual.routes = routes
            individual.total_distance = total_distance
            individual.penalty = total_penalty

        return (fitness,)

    def _ox_crossover(self, parent1: List, parent2: List) -> Tuple[List, List]:
        """
        Vehicle-scoped Order Crossover (OX) operator for MDVRP.

        Applies OX independently to each vehicle's customer segment,
        preserving depot positions and vehicle-depot assignments.
        """
        # Decode parents to routes dict
        routes1 = self._decode_chromosome(parent1)
        routes2 = self._decode_chromosome(parent2)

        # Apply OX to each vehicle's route independently
        offspring_routes1 = {}
        offspring_routes2 = {}

        for vehicle in self.vehicles:
            route1 = routes1[vehicle]
            route2 = routes2[vehicle]

            # Apply OX to customer lists
            offspring1_route, offspring2_route = self._ox_on_list(route1, route2)

            offspring_routes1[vehicle] = offspring1_route
            offspring_routes2[vehicle] = offspring2_route

        # Re-encode to chromosomes
        offspring1 = self._encode_from_routes(offspring_routes1)
        offspring2 = self._encode_from_routes(offspring_routes2)

        return offspring1, offspring2

    def _ox_on_list(self, list1: List, list2: List) -> Tuple[List, List]:
        """
        Apply Order Crossover (OX) to two lists independently.
        Handles different-sized routes by applying OX separately.

        Args:
            list1: First parent list (customers only, no depots)
            list2: Second parent list (customers only, no depots)

        Returns:
            Tuple of two offspring lists
        """
        # Handle empty routes
        if not list1 or not list2:
            return list(list1), list(list2)

        size1 = len(list1)
        size2 = len(list2)

        # If routes are too short, just return copies
        if size1 < 2 or size2 < 2:
            return list(list1), list(list2)

        # Apply OX to offspring1 (from list1, using list2)
        offspring1 = self._ox_single(list1, list2)

        # Apply OX to offspring2 (from list2, using list1)
        offspring2 = self._ox_single(list2, list1)

        return offspring1, offspring2

    def _ox_single(self, primary: List, secondary: List) -> List:
        """
        Apply Order Crossover to create one offspring.
        Takes a segment from primary and fills from secondary.

        Args:
            primary: Parent list to take segment from
            secondary: Parent list to fill remaining positions from

        Returns:
            Offspring list
        """
        size = len(primary)

        if size < 2:
            return list(primary)

        # Choose two random crossover points
        a, b = random.sample(range(size), 2)
        if a > b:
            a, b = b, a

        # Initialize offspring
        offspring = [None] * size

        # Copy segment from primary
        offspring[a:b+1] = primary[a:b+1]

        # Fill remaining positions from secondary, maintaining order
        current_pos = (b + 1) % size
        for gene in secondary[b+1:] + secondary[:b+1]:
            if gene not in offspring:
                offspring[current_pos] = gene
                current_pos = (current_pos + 1) % size

        return offspring

    def _swap_mutation(self, individual: List) -> Tuple:
        """Swap mutation operator - swap two random customer genes only (not depots)"""
        if len(individual) < 2:
            return (individual,)

        # Filter out None values
        individual = [gene for gene in individual if gene is not None]

        # Find all customer positions (not depots)
        customer_positions = [i for i, gene in enumerate(individual) if gene.startswith('C')]

        if len(customer_positions) < 2:
            return (individual,)

        # Choose two random customer positions
        idx1, idx2 = random.sample(customer_positions, 2)

        # Swap
        individual[idx1], individual[idx2] = individual[idx2], individual[idx1]

        return (individual,)

    def _two_opt_local_search(self, individual: List, routes: Dict) -> List:
        """Apply 2-opt local search to improve routes"""
        # Decode current routes
        improved_routes = {}

        for vehicle in self.vehicles:
            route = routes[vehicle]
            # Filter out None values
            route = [c for c in route if c is not None]

            if len(route) < 3:
                improved_routes[vehicle] = route
                continue

            # Apply 2-opt
            best_route = route[:]
            best_distance = self._calculate_route_distance(vehicle, best_route)

            improved = True
            iterations = 0
            max_iterations = 10  # Limit iterations to avoid excessive computation

            while improved and iterations < max_iterations:
                improved = False
                iterations += 1

                for i in range(len(route) - 1):
                    for j in range(i + 2, len(route)):
                        # Try 2-opt swap
                        new_route = route[:i+1] + route[i+1:j+1][::-1] + route[j+1:]
                        new_distance = self._calculate_route_distance(vehicle, new_route)

                        if new_distance < best_distance:
                            best_route = new_route
                            best_distance = new_distance
                            improved = True

                route = best_route[:]

            improved_routes[vehicle] = best_route

        # Re-encode to chromosome
        return self._encode_from_routes(improved_routes)

    def _relocation_local_search(self, individual: List, routes: Dict) -> List:
        """
        Apply relocation local search to improve routes.

        Two-phase approach:
        1. Intra-route: Move customer to different position in same route
        2. Inter-route: Move customer to different route (only if intra doesn't improve)

        Returns:
            Improved chromosome
        """
        improved = False

        # Phase 1: Intra-route relocation
        for vehicle in self.vehicles:
            route = routes[vehicle]
            # Filter None values
            route = [c for c in route if c is not None]

            if len(route) < 2:
                continue

            # Find best intra-route move
            best_move = self._find_best_intra_relocation(vehicle, route)

            if best_move:
                position, new_position = best_move
                # Apply the move
                customer = route[position]
                route.pop(position)
                route.insert(new_position, customer)
                # Update routes dict
                routes[vehicle] = route
                improved = True

        # Phase 2: Inter-route relocation (only if intra didn't help)
        if not improved:
            best_inter_move = self._find_best_inter_relocation(routes)
            if best_inter_move:
                vehicle, customer, target_vehicle, position = best_inter_move
                # Move customer from current route to target route
                routes[vehicle].remove(customer)
                routes[target_vehicle].insert(position, customer)
                improved = True

        # Re-encode to chromosome
        return self._encode_from_routes(routes)

    def _find_best_intra_relocation(self, vehicle: str, route: List) -> Optional[Tuple]:
        """
        Find best intra-route relocation move.

        Returns:
            Tuple of (position_to_remove, new_position, new_distance) or None
        """
        best_improvement = 0
        best_move = None

        current_distance = self._calculate_route_distance(vehicle, route)

        for position in range(len(route)):
            customer = route[position]

            # Try moving to each other position
            for new_position in range(len(route)):
                if new_position == position:
                    continue

                # Create test route
                test_route = route[:]
                test_route.pop(position)
                test_route.insert(new_position, customer)

                # Calculate new distance
                new_distance = self._calculate_route_distance(vehicle, test_route)
                improvement = current_distance - new_distance

                if improvement > best_improvement:
                    best_improvement = improvement
                    best_move = (position, new_position)

        if best_improvement > 0:
            return best_move
        return None

    def _find_best_inter_relocation(self, routes: Dict) -> Optional[Tuple]:
        """
        Find best inter-route relocation move.

        Returns:
            Tuple of (source_vehicle, customer, target_vehicle, position) or None
        """
        best_improvement = 0
        best_move = None

        for source_vehicle in self.vehicles:
            source_route = routes[source_vehicle]
            source_route = [c for c in source_route if c is not None]

            for customer in source_route[:]:  # Copy to safely modify during iteration
                # Try moving to each other vehicle
                for target_vehicle in self.vehicles:
                    if target_vehicle == source_vehicle:
                        continue

                    target_route = routes[target_vehicle]
                    target_route = [c for c in target_route if c is not None]

                    # Try each position in target route
                    for position in range(len(target_route) + 1):
                        # Check capacity constraint
                        current_load = sum(self.demand[c] for c in source_route if c is not None)
                        customer_demand = self.demand[customer]
                        target_load = sum(self.demand[c] for c in target_route if c is not None)

                        if target_load + customer_demand > self.Q[target_vehicle]:
                            continue  # Would exceed capacity

                        # Calculate improvement
                        old_dist = (self._calculate_route_distance(source_vehicle, source_route) +
                                   self._calculate_route_distance(target_vehicle, target_route))

                        # Create test routes
                        test_source = [c for c in source_route if c != customer]
                        test_target = target_route[:]
                        test_target.insert(position, customer)

                        new_dist = (self._calculate_route_distance(source_vehicle, test_source) +
                                   self._calculate_route_distance(target_vehicle, test_target))

                        improvement = old_dist - new_dist

                        if improvement > best_improvement:
                            best_improvement = improvement
                            best_move = (source_vehicle, customer, target_vehicle, position)

        if best_improvement > 0:
            return best_move
        return None

    def _calculate_route_distance(self, vehicle: str, route: List) -> float:
        """Calculate total distance for a route"""
        if not route:
            return 0.0

        # Filter out None values from route
        route = [c for c in route if c is not None]

        if not route:
            return 0.0

        depot = self.depot_for_vehicle[vehicle]

        if self.uses_numpy:
            # Use NumPy arrays
            indices = [self.node_to_idx[depot]]
            indices.extend(self.node_to_idx[c] for c in route)
            indices.append(self.node_to_idx[depot])

            total_dist = 0.0
            for i in range(len(indices) - 1):
                total_dist += self.dist[indices[i]][indices[i+1]]
            return total_dist
        else:
            # Use dict-based
            total_dist = 0.0
            prev = depot
            for customer in route:
                total_dist += self.dist[prev][customer]
                prev = customer
            total_dist += self.dist[prev][depot]
            return total_dist

    def _calculate_route_time(self, vehicle: str, route: List) -> float:
        """Calculate total travel time for a vehicle's route"""
        if not route:
            return 0.0

        # Filter out None values from route
        route = [c for c in route if c is not None]

        if not route:
            return 0.0

        depot = self.depot_for_vehicle[vehicle]

        if self.uses_numpy:
            # Use NumPy arrays
            time_matrix = self.T[vehicle]
            indices = [self.node_to_idx[depot]]
            indices.extend(self.node_to_idx[c] for c in route)
            indices.append(self.node_to_idx[depot])

            total_time = 0.0
            for i in range(len(indices) - 1):
                total_time += time_matrix[indices[i]][indices[i+1]]
            return total_time
        else:
            # Use dict-based
            total_time = 0.0
            prev = depot
            for customer in route:
                total_time += self.T[vehicle][prev][customer]
                prev = customer
            total_time += self.T[vehicle][prev][depot]
            return total_time

    def _mutation_pipeline(self, individual: List) -> Tuple:
        """Apply mutation pipeline: swap + 2-opt + relocation"""
        # Convert to list if it's an Individual object
        if hasattr(individual, 'fitness'):
            individual_list = list(individual)
        else:
            individual_list = individual

        # Apply swap mutation
        individual_list = list(self._swap_mutation(individual_list)[0])

        # Apply 2-opt local search (always run)
        routes = self._decode_chromosome(individual_list)
        individual_list = self._two_opt_local_search(individual_list, routes)

        # Apply relocation local search
        routes = self._decode_chromosome(individual_list)
        individual_list = self._relocation_local_search(individual_list, routes)

        # Return as tuple (required by DEAP)
        return (individual_list,)

    def _tournament_selection(self, individuals: List, k: int,
                             tournament_size: int) -> List:
        """Tournament selection for DEAP"""
        chosen = []
        for _ in range(k):
            aspirants = tools.selRandom(individuals, tournament_size)
            chosen.append(max(aspirants, key=lambda ind: ind.fitness))
        return chosen

    def _check_capacity(self, vehicle: str, customer: str, routes: Dict) -> bool:
        """Check capacity constraint"""
        current_load = sum(self.demand[c] for c in routes[vehicle])
        return (current_load + self.demand[customer]) <= self.Q[vehicle]

    def _check_time(self, vehicle: str, customer: str, position: int, routes: Dict) -> bool:
        """Check time constraint"""
        route = routes[vehicle]
        depot = self.depot_for_vehicle[vehicle]

        # Calculate current time
        current_time = 0
        prev = depot
        for c in route:
            if self.uses_numpy:
                time_matrix = self.T[vehicle]
                p = self.node_to_idx[prev]
                curr = self.node_to_idx[c]
                current_time += time_matrix[p][curr]
            else:
                current_time += self.T[vehicle][prev][c]
            prev = c

        if route:
            if self.uses_numpy:
                time_matrix = self.T[vehicle]
                p = self.node_to_idx[prev]
                d = self.node_to_idx[depot]
                current_time += time_matrix[p][d]
            else:
                current_time += self.T[vehicle][prev][depot]

        # Calculate time increase
        if len(route) == 0:
            if self.uses_numpy:
                time_matrix = self.T[vehicle]
                i = self.node_to_idx[depot]
                j = self.node_to_idx[customer]
                time_increase = time_matrix[i][j] + time_matrix[j][i]
            else:
                time_increase = self.T[vehicle][depot][customer] + self.T[vehicle][customer][depot]
        elif position == 0:
            if self.uses_numpy:
                time_matrix = self.T[vehicle]
                i = self.node_to_idx[depot]
                j = self.node_to_idx[customer]
                k = self.node_to_idx[route[0]]
                time_increase = (time_matrix[i][j] + time_matrix[j][k] - time_matrix[i][k])
            else:
                time_increase = (self.T[vehicle][depot][customer] +
                               self.T[vehicle][customer][route[0]] -
                               self.T[vehicle][depot][route[0]])
        elif position >= len(route):
            if self.uses_numpy:
                time_matrix = self.T[vehicle]
                i = self.node_to_idx[route[-1]]
                j = self.node_to_idx[customer]
                d = self.node_to_idx[depot]
                time_increase = (time_matrix[i][j] + time_matrix[j][d] - time_matrix[i][d])
            else:
                time_increase = (self.T[vehicle][route[-1]][customer] +
                               self.T[vehicle][customer][depot] -
                               self.T[vehicle][route[-1]][depot])
        else:
            if self.uses_numpy:
                time_matrix = self.T[vehicle]
                i = self.node_to_idx[route[position-1]]
                j = self.node_to_idx[customer]
                k = self.node_to_idx[route[position]]
                time_increase = (time_matrix[i][j] + time_matrix[j][k] -
                               time_matrix[i][k])
            else:
                time_increase = (self.T[vehicle][route[position-1]][customer] +
                               self.T[vehicle][customer][route[position]] -
                               self.T[vehicle][route[position-1]][route[position]])

        new_time = current_time + time_increase
        return new_time <= self.T_max[vehicle] and new_time <= self.L[customer]

    def solve(self, time_limit=None, max_iterations=None,
              progress_callback=None, verbose=True):
        """
        Solve MDVRP using hybrid genetic algorithm with DEAP.

        Args:
            time_limit: Maximum runtime in seconds
            max_iterations: Maximum generations (overrides self.generations)
            progress_callback: Function for progress updates
            verbose: Print progress to console

        Returns:
            (solution_dict, status_string)
        """
        start_time = time.time()

        if verbose:
            print("=" * 70)
            print("ALGORITMA HYBRID GENETIC ALGORITHM (HGA) - MDVRP")
            print("Dengan DEAP Framework, NumPy, dan 2-opt Local Search")
            print("=" * 70)
            print(f"\nParameter HGA:")
            print(f"  - Population size: {self.population_size}")
            print(f"  - Generations: {self.generations}")
            print(f"  - Crossover rate: {self.crossover_rate}")
            print(f"  - Mutation rate: {self.mutation_rate}")
            print(f"  - Tournament size: {self.tournament_size}")
            print(f"  - Elite size: {self.elite_size}")

        # Initialize population
        population = self.toolbox.population(n=self.population_size)

        # Evaluate initial population
        fitnesses = self.toolbox.map(self.toolbox.evaluate, population)
        for ind, fit in zip(population, fitnesses):
            ind.fitness.values = fit

        # Track best solution
        hof = tools.HallOfFame(1)

        # Statistics
        stats = tools.Statistics(lambda ind: ind.fitness.values)
        stats.register("avg", np.mean)
        stats.register("min", np.min)
        stats.register("max", np.max)

        # Import tqdm for progress bar
        from tqdm import tqdm

        generations = self.generations if max_iterations is None else max_iterations

        # Use tqdm if verbose and no time limit
        use_tqdm = verbose and time_limit is None

        if use_tqdm:
            pbar = tqdm(total=generations, desc="HGA Generations")
        else:
            pbar = None

        # Evolution loop
        for gen in range(generations):
            # Check time limit
            if time_limit is not None:
                elapsed = time.time() - start_time
                if elapsed >= time_limit:
                    if verbose:
                        print(f"\n[TIMEOUT] Time limit reached: {elapsed:.2f}s")
                    if pbar:
                        pbar.close()
                    best = hof[0] if len(hof) > 0 else population[0]
                    # _format_solution now ensures all customers are included
                    return self._format_solution(best, start_time, gen), 'timeout'

            # ELITISM: Preserve best individuals from current generation
            # Sort population by fitness (ascending - lower is better)
            population.sort(key=lambda ind: ind.fitness.values[0])
            elites = population[:self.elite_size]

            # Select and clone offspring (only for remaining spots)
            num_offspring = len(population) - self.elite_size
            offspring = self.toolbox.select(population, num_offspring)
            offspring = [self.toolbox.clone(ind) for ind in offspring]

            # Apply crossover
            for i in range(1, len(offspring), 2):
                if random.random() < self.crossover_rate:
                    # Crossover returns lists - need to convert back to Individuals
                    child1_list, child2_list = self.toolbox.mate(offspring[i-1], offspring[i])

                    # Create new Individual objects from the lists
                    # New individuals created by constructor have invalid fitness by default
                    offspring[i-1] = creator.Individual(child1_list)
                    offspring[i] = creator.Individual(child2_list)

            # Apply mutation
            for i in range(len(offspring)):
                if random.random() < self.mutation_rate:
                    mutated_list, = self.toolbox.mutate(offspring[i])
                    # Create new Individual from mutated list
                    offspring[i] = creator.Individual(mutated_list)
                    # New individual has invalid fitness by default

            # Evaluate invalid individuals
            invalid_ind = [ind for ind in offspring if not ind.fitness.valid]
            fitnesses = self.toolbox.map(self.toolbox.evaluate, invalid_ind)
            for ind, fit in zip(invalid_ind, fitnesses):
                ind.fitness.values = fit

            # Replace population: elites + offspring
            population = elites + offspring

            # Update hall of fame
            hof.update(population)

            # Update progress
            if pbar:
                best_fitness = hof[0].fitness.values[0] if len(hof) > 0 else float('inf')
                pbar.update(1)
                pbar.set_description(f"HGA Gen {gen+1} (best: {best_fitness:.2f})")

            if progress_callback:
                best_fitness = hof[0].fitness.values[0] if len(hof) > 0 else float('inf')
                progress_callback(gen + 1, generations, f"Generation {gen+1}, Best: {best_fitness:.2f}")

            if verbose and not use_tqdm:
                best_fitness = hof[0].fitness.values[0] if len(hof) > 0 else float('inf')
                print(f"  Generation {gen+1}/{generations}: Best fitness = {best_fitness:.2f}")

        if pbar:
            pbar.close()

        # Extract best solution
        best = hof[0] if len(hof) > 0 else population[0]
        routes = self._decode_chromosome(best)

        # Calculate total distance and penalty for best solution
        total_distance = 0
        total_penalty = 0
        for vehicle in self.vehicles:
            route = routes[vehicle]
            total_distance += self._calculate_route_distance(vehicle, route)

        # Calculate penalty from fitness
        if hasattr(best, 'fitness') and best.fitness.valid:
            fitness = best.fitness.values[0]
            total_penalty = fitness - total_distance

        if verbose:
            print("\n" + "=" * 70)
            print("HASIL AKHIR HGA")
            print("=" * 70)
            print(f"\nFitness terbaik: {best.fitness.values[0]:.2f}")
            print(f"Total jarak: {total_distance:.2f}")
            print(f"Total penalti: {total_penalty:.2f}")

        return self._format_solution(best, start_time, generations), 'feasible'

    def _format_solution(self, best_individual: List, start_time: float,
                        generations: int) -> Dict:
        """
        Format solution as dict.

        Returns:
            Dict containing:
                - routes: Dict with vehicle routes including 'time', 'distance', 'load', 'nodes'
                - fitness: Total fitness value
                - total_distance: Total distance
                - penalty: Total penalty
                - generations: Number of generations run
                - runtime: Solver runtime
                - depot_for_vehicle: Vehicle-depot mapping
        """
        runtime = time.time() - start_time
        routes = self._decode_chromosome(best_individual)

        # CRITICAL: Ensure all customers are in routes
        served_customers = set()
        for vehicle in self.vehicles:
            route = routes[vehicle]
            if route:
                served_customers.update(c for c in route if c is not None)

        missing_customers = set(self.customers) - served_customers
        if missing_customers:
            least_loaded_vehicle = min(
                self.vehicles,
                key=lambda v: sum(self.demand[c] for c in routes[v])
            )
            routes[least_loaded_vehicle].extend(list(missing_customers))

        # Calculate total distance and penalty
        total_distance = 0
        total_penalty = 0

        # Penalty weights
        alpha_cap = 50
        alpha_time = 100

        # Build routes dict with detailed info
        routes_dict = {}
        for vehicle in self.vehicles:
            route = routes[vehicle]
            route_dist = self._calculate_route_distance(vehicle, route)
            route_time = self._calculate_route_time(vehicle, route)
            route_load = sum(self.demand[c] for c in route if c is not None)

            routes_dict[vehicle] = {
                'nodes': route,
                'distance': route_dist,
                'time': route_time,
                'load': route_load
            }
            total_distance += route_dist

            # Calculate penalties
            if route_load > self.Q[vehicle]:
                excess_load = route_load - self.Q[vehicle]
                total_penalty += (excess_load * alpha_cap)

            if route_time > self.T_max[vehicle]:
                excess_time = route_time - self.T_max[vehicle]
                total_penalty += (excess_time * alpha_time)

        # Get fitness and penalty from individual or recalculate
        if hasattr(best_individual, 'fitness') and best_individual.fitness.valid:
            fitness = best_individual.fitness.values[0]
            penalty = best_individual.penalty if hasattr(best_individual, 'penalty') else total_penalty
        else:
            fitness = total_distance + total_penalty
            penalty = total_penalty

        return {
            'routes': routes_dict,
            'fitness': fitness,
            'total_distance': total_distance,
            'penalty': penalty,
            'generations': generations,
            'runtime': runtime,
            'depot_for_vehicle': self.depot_for_vehicle,
            'unallocated': [],  # Always empty now - all customers are served
            'vehicle_speed': self.params.get('vehicle_speed', {})
        }

    def solve_legacy(self):
        """
        Legacy solve method for backward compatibility.
        Prints detailed output to console.
        """
        solution, status = self.solve(verbose=True)

        # Print routes
        print("\nRute terbaik untuk setiap kendaraan:")
        for vehicle, info in solution['routes'].items():
            depot = self.depot_for_vehicle[vehicle]
            route = info['nodes']
            print(f"\nKendaraan {vehicle} (berasal dari Depot {depot}):")
            print(f"  Rute: {depot} -> {' -> '.join(map(str, route))} -> {depot}")
            print(f"  Urutan pelanggan: {route}")
            print(f"  Total beban: {info['load']:.1f} / {self.Q[vehicle]} kg")
            print(f"  Total jarak: {info['distance']:.2f}")

        return solution
