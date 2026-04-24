# Capability: Distance Caching

## ADDED Requirements

### Requirement: Cache distance matrix in database

The system SHALL cache computed node distances in the `node_distances` table to avoid redundant calculations in subsequent solver runs.

#### Scenario: First run - cache miss
- **WHEN** solver runs with a dataset that has no cached distances
- **THEN** system computes distance matrix using DistanceMatrixBuilder
- **AND** system inserts all node pairs into node_distances table
- **AND** system includes distance, travel_time, node_start_id, node_end_id, dataset_id

#### Scenario: Subsequent run - cache hit with valid data
- **WHEN** solver runs with a dataset that has cached distances
- **AND** cache validation passes
- **THEN** system loads distance matrix from node_distances table
- **AND** system does NOT recompute distances

#### Scenario: Cache invalid - corrupted data
- **WHEN** solver runs with a dataset that has cached distances
- **AND** cache validation fails (distances don't match expected values)
- **THEN** system deletes all cached distances for that dataset_id
- **AND** system recomputes distance matrix
- **AND** system inserts fresh distance data into node_distances table

### Requirement: Validate cached distances before use

The system SHALL validate cached distances using spot-check validation before loading from cache.

#### Scenario: Spot-check validation passes
- **WHEN** system validates cache for a dataset
- **AND** 3 random sampled node pairs match cached distances within 0.01 tolerance
- **THEN** system considers cache valid
- **AND** system loads distances from cache

#### Scenario: Spot-check validation fails
- **WHEN** system validates cache for a dataset
- **AND** any sampled node pair differs from cached distance by more than 0.01
- **THEN** system considers cache invalid
- **AND** system recomputes all distances

#### Scenario: No cache exists
- **WHEN** system validates cache for a dataset
- **AND** node_distances table contains no rows for that dataset_id
- **THEN** system considers cache invalid
- **AND** system computes and caches distances

### Requirement: Support batch insert for performance

The system SHALL insert all distance matrix entries in a single batch operation for performance.

#### Scenario: Batch insert distances
- **WHEN** system saves a computed distance matrix
- **THEN** system inserts all node pairs in one batch operation
- **AND** system uses executemany or similar bulk insert mechanism
- **AND** operation completes within 200ms for typical datasets (≤100 nodes)

### Requirement: Provide fallback to CSV mode

The system SHALL support CSV mode without database integration for backward compatibility.

#### Scenario: CSV mode without database
- **WHEN** solver runs without --dataset argument
- **THEN** system computes distance matrix on every run
- **AND** system does NOT attempt to access database for distances
- **AND** system behaves identically to pre-integration behavior

### Requirement: Load distances as NumPy array

The system SHALL return cached distances in the same NumPy array format as DistanceMatrixBuilder for compatibility with solvers.

#### Scenario: Load cached distances
- **WHEN** system loads distances from cache
- **THEN** system returns a square NumPy array
- **AND** array indexing matches node order (depots + customers)
- **AND** array is compatible with existing solver code expecting DistanceMatrixBuilder output
