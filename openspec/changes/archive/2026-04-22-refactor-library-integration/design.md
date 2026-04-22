# Design: MDVRP Library Integration Refactoring

## System Architecture

### Current Architecture

```
Hardcoded Python dicts (mdvrp_small.py)
    ↓
build_model_data() - Manual distance calculation
    ↓
params dict (nested dicts)
    ↓
┌─────────────────────────────────────┐
│  Solver Choice:                     │
│  • MDVRPHGA (custom GA)             │
│  • MDVRPGreedy (custom heuristic)   │
│  • MDVRP (Gurobi MILP)              │
└─────────────────────────────────────┘
    ↓
Print to console
```

### Target Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  DATA INPUT LAYER                                            │
│  ─────────────────────────────────────────────────────────── │
│  • CSV files  • XLSX files  • Web frontend  • Hardcoded dict │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  DATA LOADER MODULE (data_loader.py)                        │
│  ─────────────────────────────────────────────────────────── │
│  • load_csv()      → Pandas DataFrame                        │
│  • load_xlsx()     → Pandas DataFrame                        │
│  • load_from_dict() → Backward compatibility                 │
│  • validate_data() → Quality checks                          │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  PRE-PROCESSING LAYER (distance_matrix.py)                  │
│  ─────────────────────────────────────────────────────────── │
│  • build_distance_matrix()  → SciPy cdist + NumPy arrays    │
│  • build_time_matrix()      → NumPy broadcasting             │
│  • calculate_demand()       → Vectorized calculation         │
│  • package_params()         → Unified params dict            │
│                                                             │
│  ONCE for all solvers!                                      │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  SOLVER LAYER (all receive same pre-computed params)        │
│  ─────────────────────────────────────────────────────────── │
│  • MDVRPHGA    → DEAP + NumPy + Pandas + tqdm               │
│  • MDVRPGreedy → NumPy + Pandas + tqdm                      │
│  • MDVRP       → Gurobi (unchanged) + Pandas + tqdm         │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  OUTPUT LAYER (exporter.py)                                 │
│  ─────────────────────────────────────────────────────────── │
│  • export_csv()      → Results CSV                          │
│  • export_pdf()      → Report with tables/plots             │
│  • export_geojson()  → GeoJSON for maps                     │
│  • print_results()   → Console output (backward compat)     │
└─────────────────────────────────────────────────────────────┘
```

## Module Design

### 1. Data Loader Module (`src/data_loader.py`)

```python
"""
Data loading module for MDVRP problem instances
Supports CSV, XLSX, and dict-based input (backward compatibility)
"""

import pandas as pd
from typing import Dict, Tuple, Union

class MDVRPDataLoader:
    """Load MDVRP problem data from various sources"""

    def load_csv(self, data_dir: str) -> Dict:
        """
        Load MDVRP data from CSV files

        Expected files:
        - depots.csv: depot_id, latitude, longitude
        - customers.csv: customer_id, latitude, longitude, deadline
        - vehicles.csv: vehicle_id, depot_id, capacity, max_time, speed
        - orders.csv: customer_id, item_id, quantity
        - items.csv: item_id, weight, expiry_hours

        Returns:
            Dict with depots, customers, vehicles, items, coordinates,
                   customer_orders, item_weights, item_expiry, etc.
        """

    def load_xlsx(self, file_path: str) -> Dict:
        """Load MDVRP data from single Excel file with multiple sheets"""

    def load_from_dict(self, data: Dict) -> Dict:
        """
        Load from dict (backward compatibility with mdvrp_small.py)
        Validates and standardizes the data format
        """

    def validate_data(self, data: Dict) -> bool:
        """Validate data completeness and consistency"""
```

**Key Design Decisions:**
- Returns same dict structure as current code for compatibility
- Validates data before returning
- Supports multiple input formats
- Pandas used internally for efficient data manipulation

---

### 2. Distance Matrix Module (`src/distance_matrix.py`)

```python
"""
Distance and time matrix computation using SciPy and NumPy
Shared pre-processing step for all MDVRP solvers
"""

import numpy as np
from scipy.spatial import distance
from typing import Dict, Tuple

class DistanceMatrixBuilder:
    """Build distance and time matrices for MDVRP"""

    def __init__(self, coordinates: Dict, vehicle_speeds: Dict):
        """
        Args:
            coordinates: {node_id: (lat, lon)}
            vehicle_speeds: {vehicle_id: speed_kmh}
        """
        self.coordinates = coordinates
        self.vehicle_speeds = vehicle_speeds

    def build_distance_matrix(self, nodes: list) -> np.ndarray:
        """
        Compute distance matrix using SciPy

        Uses: Euclidean distance × 111 (degree to km conversion)
              Matches current implementation but vectorized

        Args:
            nodes: List of node IDs

        Returns:
            np.ndarray: Square distance matrix
        """
        # Extract coordinates in order
        coords = np.array([self.coordinates[node] for node in nodes])

        # Compute pairwise distances using SciPy
        dist_matrix = distance.cdist(coords, coords, metric='euclidean')

        # Convert degrees to km (1 degree ≈ 111 km at equator)
        dist_matrix = dist_matrix * 111

        return dist_matrix

    def build_time_matrices(self, nodes: list, vehicles: list,
                            dist_matrix: np.ndarray) -> Dict:
        """
        Build travel time matrices for each vehicle

        Args:
            nodes: List of node IDs
            vehicles: List of vehicle IDs
            dist_matrix: Pre-computed distance matrix

        Returns:
            Dict: {vehicle_id: time_matrix}
        """
        time_matrices = {}

        for vehicle in vehicles:
            speed = self.vehicle_speeds[vehicle]
            # time = distance / speed
            time_matrices[vehicle] = dist_matrix / speed

        return time_matrices

    def calculate_demand(self, customers: list, items: list,
                        customer_orders: Dict, item_weights: Dict) -> np.ndarray:
        """
        Calculate customer demand using NumPy vectorization

        Args:
            customers: List of customer IDs
            items: List of item IDs
            customer_orders: {customer_id: {item_id: quantity}}
            item_weights: {item_id: weight_kg}

        Returns:
            np.ndarray: demand per customer
        """
        demand = np.zeros(len(customers))

        for i, customer in enumerate(customers):
            order = customer_orders.get(customer, {})
            demand[i] = sum(
                item_weights[item] * order.get(item, 0)
                for item in items
            )

        return demand

    def build_all_matrices(self, depots: list, customers: list,
                          vehicles: list, items: list,
                          coordinates: Dict, vehicle_speeds: Dict,
                          customer_orders: Dict, item_weights: Dict,
                          vehicle_capacities: Dict, max_operational_times: Dict,
                          customer_deadlines: Dict, depot_for_vehicle: Dict,
                          M: int = 1000) -> Dict:
        """
        Build all matrices and package into params dict

        Returns:
            Dict: Compatible params dict for all solvers
        """
        nodes = depots + customers

        # Build distance matrix (NumPy array)
        dist_matrix = self.build_distance_matrix(nodes)

        # Build time matrices (NumPy arrays)
        time_matrices = self.build_time_matrices(nodes, vehicles, dist_matrix)

        # Calculate demand (NumPy array)
        demand = self.calculate_demand(customers, items,
                                       customer_orders, item_weights)

        # Package params (mixed: NumPy arrays + dicts)
        params = {
            'dist': dist_matrix,  # NumPy array
            'T': time_matrices,   # Dict of NumPy arrays
            'demand': demand,     # NumPy array
            'Q': vehicle_capacities,
            'T_max': max_operational_times,
            'L': customer_deadlines,
            'w': item_weights,
            'r': customer_orders,
            'expiry': {item: 100 for item in items},  # Placeholder
            'depot_for_vehicle': depot_for_vehicle,
            'M': M
        }

        return params
```

**Key Design Decisions:**
- Single shared computation for all solvers
- Returns NumPy arrays for distance/time/demand
- Keeps backward-compatible params dict structure
- Uses SciPy's optimized `cdist()` function

---

### 3. HGA Solver with DEAP (`mdvrp_hga.py`)

```python
"""
Hybrid Genetic Algorithm for MDVRP using DEAP framework
"""

import numpy as np
import pandas as pd
from deap import base, creator, tools, algorithms
from tqdm import tqdm
import random

class MDVRPHGA:
    """MDVRP Hybrid Genetic Algorithm with DEAP"""

    def __init__(self, depots, customers, vehicles, items, params,
                 population_size=20, generations=20, elite_size=3,
                 mutation_rate=0.2, crossover_rate=0.8, tournament_size=3,
                 seed=None):

        # Store problem data
        self.depots = depots
        self.customers = customers
        self.vehicles = vehicles
        self.items = items
        self.params = params

        # Extract NumPy arrays from params
        self.dist_matrix = params['dist']  # NumPy array
        self.time_matrices = params['T']   # Dict of NumPy arrays
        self.demand = params['demand']     # NumPy array

        # GA parameters
        self.population_size = population_size
        self.generations = generations
        self.elite_size = elite_size
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.tournament_size = tournament_size
        self.seed = seed

        # Setup DEAP framework
        self._setup_deap()

    def _setup_deap(self):
        """Configure DEAP creator and toolbox"""

        # Create fitness and individual classes
        creator.create("FitnessMin", base.Fitness, weights=(-1.0,))
        creator.create("Individual", list, fitness=creator.FitnessMin)

        # Initialize toolbox
        self.toolbox = base.Toolbox()

        # Register genetic operators
        self.toolbox.register("mate", self._ox_crossover)
        self.toolbox.register("mutate", self._swap_mutation)
        self.toolbox.register("select", self._tournament_selection,
                              tournament_size=self.tournament_size)
        self.toolbox.register("evaluate", self._calculate_fitness)

        # Register population initializer
        self.toolbox.register("population", tools.initRepeat,
                              list, self.toolbox.individual)

    def solve(self, time_limit=None, max_iterations=None,
              progress_callback=None, verbose=True):
        """
        Solve MDVRP using hybrid genetic algorithm

        Args:
            time_limit: Maximum runtime in seconds
            max_iterations: Maximum generations (overrides self.generations)
            progress_callback: Function for progress updates
            verbose: Print progress to console

        Returns:
            solution: Dict with routes, fitness, metadata
            status: 'optimal', 'feasible', 'timeout', etc.
        """
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

        # Run evolution with progress tracking
        if verbose:
            pbar = tqdm(total=self.generations, desc="HGA Generations")

        population, logbook = algorithms.eaSimple(
            population, self.toolbox,
            cxpb=self.crossover_rate,
            mutpb=self.mutation_rate,
            ngen=self.generations,
            stats=stats,
            halloffame=hof,
            verbose=False
        )

        if verbose:
            pbar.close()

        # Extract best solution
        best = hof[0]
        routes = self._decode_chromosome(best)

        return {
            'routes': routes,
            'fitness': best.fitness.values[0],
            'generations': len(logbook),
            'convergence': logbook
        }, 'feasible'

    def _calculate_fitness(self, individual):
        """
        Calculate fitness using NumPy vectorization

        Returns tuple (fitness,) for DEAP
        """
        # Decode chromosome to routes
        routes = self._decode_chromosome(individual)

        # Vectorized distance calculation
        total_distance = 0.0
        penalty = 0.0

        for v_idx, vehicle in enumerate(self.vehicles):
            route = routes[vehicle]
            if not route:
                continue

            # Get indices for nodes
            depot = self.depot_for_vehicle[vehicle]
            route_indices = [self.nodes.index(c) for c in route]

            # Calculate distance using NumPy
            route_distance = self._calculate_route_distance_numpy(
                depot, route_indices, vehicle
            )

            total_distance += route_distance

            # Check constraints (capacity, time)
            penalty += self._calculate_penalty(vehicle, route)

        return (total_distance + penalty,)

    def _ox_crossover(self, parent1, parent2):
        """Order Crossover (OX) operator for DEAP"""
        # Implementation details...

    def _swap_mutation(self, individual):
        """Swap mutation operator for DEAP"""
        # Implementation details...

    def _tournament_selection(self, individuals, k, tournament_size):
        """Tournament selection for DEAP"""
        # Implementation details...

    def _decode_chromosome(self, chromosome):
        """Decode linear chromosome to routes dict"""
        # Implementation details...

    def _calculate_route_distance_numpy(self, depot, route_indices, vehicle):
        """Calculate route distance using NumPy indexing"""
        # Implementation details...
```

**Key Design Decisions:**
- DEAP's `creator.create()` for Individual and Fitness
- Custom operators registered in toolbox
- NumPy-based fitness evaluation
- Unified `solve()` interface with time_limit support
- tqdm for progress tracking
- Backward compatible with current API

---

### 4. Greedy Solver with NumPy (`mdvrp_greedy.py`)

```python
"""
Greedy Cheapest Insertion Heuristic for MDVRP with NumPy optimization
"""

import numpy as np
import pandas as pd
from tqdm import tqdm

class MDVRPGreedy:
    """Greedy Cheapest Insertion Heuristic with NumPy"""

    def __init__(self, depots, customers, vehicles, items, params, seed=None):
        # Same initialization as current, but params may contain NumPy arrays
        self.dist_matrix = params['dist']  # NumPy array
        self.time_matrices = params['T']   # Dict of NumPy arrays
        # ... rest of initialization

    def solve(self, time_limit=None, max_iterations=None,
              progress_callback=None, verbose=True):
        """
        Solve MDVRP using greedy cheapest insertion

        Args:
            time_limit: Maximum runtime in seconds
            max_iterations: Maximum customer insertions
            progress_callback: Function for progress updates
            verbose: Print progress to console

        Returns:
            solution: Dict with routes, fitness, metadata
            status: 'feasible', 'timeout'
        """
        # Use tqdm for progress
        with tqdm(total=len(self.customers), desc="Greedy Insertion",
                 disable=not verbose) as pbar:

            while self.unallocated:
                # Check time limit
                if time_limit and self._elapsed_time() > time_limit:
                    return {'routes': self.routes}, 'timeout'

                # Find best insertion
                best = self._find_best_insertion()

                # Insert customer
                self._insert_customer(**best)

                pbar.update(1)

        return {'routes': self.routes}, 'feasible'

    def _calculate_distance_increase_numpy(self, vehicle, customer, position):
        """Calculate distance increase using NumPy indexing"""
        # Implementation using NumPy array indexing instead of dict lookups
```

**Key Design Decisions:**
- NumPy array indexing for distance calculations
- Progress bar with tqdm
- Time limit support
- Backward compatible API

---

### 5. Exporter Module (`src/exporter.py`)

```python
"""
Export MDVRP solutions to various formats
"""

import pandas as pd
import json
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle

class MDVRPExporter:
    """Export MDVRP solutions to CSV, PDF, GeoJSON"""

    def export_csv(self, solution: Dict, output_path: str):
        """Export solution to CSV file"""

    def export_pdf(self, solution: Dict, problem_data: Dict,
                   output_path: str):
        """Export solution report to PDF"""

    def export_geojson(self, solution: Dict, coordinates: Dict,
                      output_path: str):
        """Export routes as GeoJSON for mapping"""
```

---

### 6. Utils Module (`src/utils.py`)

```python
"""
Helper functions for MDVRP solvers
"""

import time

def seconds(val: float) -> float:
    """Identity function for clarity"""
    return val

def minutes(val: float) -> float:
    """Convert minutes to seconds"""
    return val * 60

def hours(val: float) -> float:
    """Convert hours to seconds"""
    return val * 3600

class TimeLimiter:
    """Context manager for time limiting"""

    def __init__(self, timeout: float):
        self.timeout = timeout
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, *args):
        pass

    def is_exceeded(self) -> bool:
        """Check if time limit exceeded"""
        if self.timeout is None:
            return False
        return (time.time() - self.start_time) > self.timeout
```

## Unified Solver Interface

All solvers will implement:

```python
def solve(self,
           time_limit=None,        # Maximum runtime in seconds
           max_iterations=None,    # Maximum iterations/generations
           progress_callback=None, # Function(current, total, message)
           verbose=True):          # Print to console
    """
    Returns:
        (solution_dict, status_string)
    """
```

**Example Usage:**

```python
# Unified interface across all solvers
solvers = {
    'HGA': MDVRPHGA(...),
    'Greedy': MDVRPGreedy(...),
    'MILP': MDVRP(...)
}

for name, solver in solvers.items():
    solution, status = solver.solve(
        time_limit=minutes(5),  # 5 minute timeout
        verbose=True
    )
```

## Data Format Specifications

### CSV Format

**depots.csv**
```csv
depot_id,latitude,longitude
D1,-6.104563,106.940091
D2,-6.276544,106.821847
```

**customers.csv**
```csv
customer_id,latitude,longitude,deadline_hours
C1,-6.224176,106.800890,8
C2,-6.137930,106.780949,8
```

**vehicles.csv**
```csv
vehicle_id,depot_id,capacity_kg,max_time_hours,speed_kmh
V1,D1,40,8,40
V2,D2,45,10,40
```

**orders.csv**
```csv
customer_id,item_id,quantity
C1,I1,2
C1,I2,0
```

**items.csv**
```csv
item_id,weight_kg,expiry_hours
I1,6.41,100
I2,7.16,100
```

### Output Format (CSV)

**solution.csv**
```csv
vehicle_id,route,Distance_km,Time_hours,Load_kg
V1,"D1 -> C4 -> C1 -> D1",12.5,2.3,35
V2,"D2 -> C3 -> C5 -> C2 -> D2",18.3,3.1,42
```

## Performance Considerations

### NumPy Benefits
- **Distance Matrix**: O(n²) computation using optimized C code
- **Fitness Evaluation**: Vectorized operations instead of Python loops
- **Memory Efficiency**: Compact array storage vs nested dicts

### Expected Performance Improvements
| Operation | Current (Dict) | NumPy | Speedup |
|-----------|----------------|-------|---------|
| Distance matrix (100 nodes) | ~500ms | ~50ms | 10x |
| Fitness eval (50 pop) | ~200ms | ~20ms | 10x |
| Route distance calc | ~5ms | ~0.5ms | 10x |

### Memory Usage
- **Current**: Nested dicts, high overhead
- **NumPy**: Contiguous arrays, ~3-4x less memory

## Backward Compatibility

### Maintained APIs
```python
# These continue to work unchanged:
MDVRPHGA(depots, customers, vehicles, items, params, ...)
MDVRPGreedy(depots, customers, vehicles, items, params, ...)
MDVRP(depots, customers, vehicles, items, params)
```

### New Capabilities
```python
# Can now also:
loader = MDVRPDataLoader()
data = loader.load_csv('data/')
params = DistanceMatrixBuilder(...).build_all_matrices(...)

# Export results
exporter = MDVRPExporter()
exporter.export_csv(solution, 'output.csv')
exporter.export_pdf(solution, data, 'output.pdf')
exporter.export_geojson(solution, coords, 'output.geojson')
```

## Error Handling

### Data Validation
- Check for missing required columns
- Validate coordinate ranges (-90 to 90, -180 to 180)
- Check for duplicate IDs
- Validate capacity/time constraints

### Solver Errors
- Invalid parameters → clear error messages
- No feasible solution → return status='infeasible'
- Timeout → return status='timeout' with best found

## Testing Strategy

### Unit Tests (Optional)
- `test_data_loader.py` - Test all input formats
- `test_distance_matrix.py` - Validate matrix computations
- `test_solvers.py` - Test each solver with known instances

### Integration Tests
- Run `run_small_*.py` scripts successfully
- Compare outputs with current implementation
- Verify export formats are valid

### Performance Tests
- Benchmark before/after for same instances
- Measure time_limit accuracy
- Memory usage profiling

## Future Extensions

Out of scope but considered:
- Web frontend integration
- Real-time solver monitoring
- Parallel DEAP evaluation
- Additional export formats (KML, SVG)
- Interactive visualization
