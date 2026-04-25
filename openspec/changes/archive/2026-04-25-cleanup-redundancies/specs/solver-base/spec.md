## ADDED Requirements

### Requirement: Shared data loading function
`src/solver_base.py` SHALL provide a `load_solver_data(data_source, depots, customers, vehicles, items, params)` function that encapsulates the CSV/XLSX loading and distance-matrix construction logic shared by all solvers.

#### Scenario: Directory data source
- **WHEN** `data_source` is a directory path
- **THEN** function loads CSV files via `MDVRPDataLoader.load_csv()`
- **AND** builds distance matrices via `DistanceMatrixBuilder.build_all_matrices()`
- **AND** returns `(depots, customers, vehicles, items, params)` with all fields populated

#### Scenario: XLSX data source
- **WHEN** `data_source` ends with `.xlsx`
- **THEN** function loads via `MDVRPDataLoader.load_xlsx()`
- **AND** returns `(depots, customers, vehicles, items, params)` with all fields populated

#### Scenario: Unsupported data source
- **WHEN** `data_source` is a non-directory, non-xlsx path
- **THEN** function raises `ValueError` with a descriptive message

#### Scenario: No data source (passthrough)
- **WHEN** `data_source` is `None`
- **THEN** function returns the inputs unchanged without loading anything

### Requirement: Shared route distance calculation
`src/solver_base.py` SHALL provide a `calculate_route_distance(route, depot, dist, node_to_idx=None, uses_numpy=False)` function that computes the total distance of a vehicle route.

#### Scenario: NumPy distance matrix
- **WHEN** `uses_numpy` is `True` and `node_to_idx` is provided
- **THEN** function uses index lookup into the NumPy `dist` array
- **AND** returns total distance as a float

#### Scenario: Dict distance matrix
- **WHEN** `uses_numpy` is `False`
- **THEN** function uses dict key lookup on the `dist` mapping
- **AND** returns total distance as a float

#### Scenario: Empty route
- **WHEN** `route` is an empty list
- **THEN** function returns the depot-to-depot distance (round trip with no customers)

### Requirement: No change to solver public interfaces
The extraction of shared logic SHALL NOT alter the public method signatures of `MDVRPGreedy`, `MDVRPHGA`, or `MDVRP`.

#### Scenario: Solver constructor unchanged
- **WHEN** any solver is instantiated with the same arguments as before
- **THEN** behaviour is identical to the pre-refactor implementation
