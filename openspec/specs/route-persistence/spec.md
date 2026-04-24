# Capability: Route Persistence

## ADDED Requirements

### Requirement: Store routes as linked segments

The system SHALL store vehicle routes as individual segments (node_start_id → node_end_id) in the `routes` table.

#### Scenario: Store simple route
- **WHEN** solver returns route D1 → C1 → C2 → D1 for vehicle V1
- **THEN** system inserts 3 rows into routes table:
  - (experiment_id, 'V1', 'D1', 'C1', distance_D1_C1)
  - (experiment_id, 'V1', 'C1', 'C2', distance_C1_C2)
  - (experiment_id, 'V1', 'C2', 'D1', distance_C2_D1)
- **AND** each row represents one route segment

#### Scenario: Store route with multiple customers
- **WHEN** solver returns route D1 → C1 → C2 → C3 → C4 → D1
- **THEN** system inserts 5 rows, one per segment
- **AND** segments follow depot → customer → ... → depot pattern

#### Scenario: Store empty route (vehicle unused)
- **WHEN** solver returns empty route for vehicle V2
- **THEN** system inserts 1 row: (experiment_id, 'V2', 'D1', 'D1', 0.0)
- **AND** segment starts and ends at depot with zero distance

### Requirement: Store all route metadata

The system SHALL store all relevant route metadata for each segment: experiment_id, vehicle_id, node_start_id, node_end_id, total_distance.

#### Scenario: Complete segment metadata
- **WHEN** inserting route segment
- **THEN** system includes: experiment_id (foreign key)
- **AND** system includes: vehicle_id (from solution)
- **AND** system includes: node_start_id (starting node of segment)
- **AND** system includes: node_end_id (ending node of segment)
- **AND** system includes: total_distance (distance for this segment)

### Requirement: Support route reconstruction

The system SHALL support reconstructing full routes from segments using linked-list traversal.

#### Scenario: Reconstruct route from segments
- **WHEN** loading routes for an experiment
- **THEN** system queries routes table for experiment_id
- **AND** system finds segment starting with depot for each vehicle
- **AND** system follows chain: node_end = next segment's node_start
- **AND** system reconstructs complete route ending at depot

#### Scenario: Reconstruction preserves order
- **WHEN** reconstructing route D1 → C1 → C2 → C3 → D1
- **THEN** system returns segments in correct order
- **AND** reconstructed route matches solver's original route

### Requirement: Handle all vehicles in solution

The system SHALL store routes for all vehicles included in the solution.

#### Scenario: Multiple vehicles
- **WHEN** solver returns routes for vehicles V1, V2, V3
- **THEN** system stores all segments for V1
- **AND** system stores all segments for V2
- **AND** system stores all segments for V3

#### Scenario: Partial vehicle usage
- **WHEN** solver returns routes for only 2 out of 3 vehicles
- **THEN** system stores routes for vehicles with assigned customers
- **AND** system stores empty route (depot→depot) for unused vehicle

### Requirement: Use distances from solution

The system SHALL use the total_distance values from the solver's solution when storing segments.

#### Scenario: Use solver-computed distances
- **WHEN** solver returns route with distances pre-computed
- **THEN** system uses solution['routes'][vehicle]['distance'] for segments
- **AND** system does NOT recompute distances from coordinates

#### Scenario: Distance from distance matrix
- **WHEN** solver uses cached distance matrix
- **THEN** segment distances match values from distance matrix
- **AND** system stores the same distances used during solving

### Requirement: Link routes to experiment

The system SHALL link all route segments to the experiment via experiment_id foreign key.

#### Scenario: Foreign key relationship
- **WHEN** inserting route segments
- **THEN** all segments for a solver run use the same experiment_id
- **AND** database enforces referential integrity
- **AND** routes can be queried by experiment_id

### Requirement: Support opt-in via CLI argument

The system SHALL only store routes when --dataset argument is provided.

#### Scenario: Database mode
- **WHEN** solver runs with --dataset argument
- **THEN** system stores routes in database

#### Scenario: CSV mode
- **WHEN** solver runs without --dataset argument
- **THEN** system does NOT store routes in database
- **AND** system returns routes in solution dict only

### Requirement: Batch insert route segments

The system SHALL insert all route segments in a single batch operation for performance.

#### Scenario: Batch insert all segments
- **WHEN** storing routes for a solution
- **THEN** system inserts all segments for all vehicles in one batch
- **AND** operation completes within 100ms for typical solutions (≤20 vehicles)

### Requirement: Validate route integrity

The system SHALL validate that reconstructed routes form valid cycles (start and end at depot).

#### Scenario: Valid route cycle
- **WHEN** storing route segments
- **THEN** system verifies first segment starts with depot
- **AND** system verifies last segment ends with depot
- **AND** system verifies all intermediate segments connect (node_end = next node_start)

#### Scenario: Invalid route (not a cycle)
- **WHEN** solver returns route that doesn't form a cycle
- **THEN** system logs warning but stores segments anyway
- **AND** system does NOT reject the solution
