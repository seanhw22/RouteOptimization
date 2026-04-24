# Capability: Result Storage

## ADDED Requirements

### Requirement: Store solver runtime in database

The system SHALL store the solver's runtime (in seconds) in the `result_metrics` table after solver completion.

#### Scenario: Store runtime after successful solve
- **WHEN** solver completes successfully
- **THEN** system inserts row into result_metrics table
- **AND** system includes experiment_id foreign key
- **AND** system includes runtime_id with solver's runtime value in seconds
- **AND** system sets constraint_violation to NULL (not tracked)

#### Scenario: Runtime precision
- **WHEN** storing solver runtime
- **THEN** system stores runtime with at least 2 decimal places (e.g., 123.45 seconds)

### Requirement: Only store runtime metric

The system SHALL store only the runtime metric in result_metrics, as other metrics can be recomputed from routes.

#### Scenario: Minimal storage
- **WHEN** storing result metrics
- **THEN** system stores ONLY runtime_id
- **AND** system does NOT store total_distance (recomputable from routes)
- **AND** system does NOT store total_load (recomputable from orders)
- **AND** system does NOT store constraint_violations (recomputable from routes and constraints)

### Requirement: Link result to experiment

The system SHALL link result_metrics to the experiment via experiment_id foreign key.

#### Scenario: Foreign key relationship
- **WHEN** inserting result_metrics row
- **THEN** system uses experiment_id from pre-created experiment record
- **AND** database enforces referential integrity
- **AND** result can be joined with experiments for analysis

### Requirement: Store result only after solver completion

The system SHALL insert result_metrics only after solver completes (successfully or with error).

#### Scenario: Successful solver run
- **WHEN** solver completes with status='feasible' or 'optimal'
- **THEN** system inserts result_metrics with runtime from solution

#### Scenario: Failed solver run
- **WHEN** solver fails or returns status='error'
- **THEN** system does NOT insert result_metrics
- **AND** experiment record exists but has no linked result_metrics

#### Scenario: Timeout solver run
- **WHEN** solver times out with status='timeout'
- **THEN** system inserts result_metrics with runtime up to timeout point

### Requirement: Support opt-in via CLI argument

The system SHALL only store result metrics when --dataset argument is provided.

#### Scenario: Database mode
- **WHEN** solver runs with --dataset argument
- **THEN** system stores result_metrics in database

#### Scenario: CSV mode
- **WHEN** solver runs without --dataset argument
- **THEN** system does NOT store result_metrics in database
- **AND** system returns runtime in solution dict only

### Requirement: Use NUMERIC(8,2) for runtime storage

The system SHALL store runtime using NUMERIC(8,2) data type matching database schema.

#### Scenario: Runtime data type
- **WHEN** inserting runtime value
- **THEN** system stores as NUMERIC(8,2) in database
- **AND** format supports up to 999999.99 seconds (~277 hours)

#### Scenario: Runtime rounding
- **WHEN** solver runtime has more than 2 decimal places
- **THEN** system rounds to 2 decimal places for storage
- **AND** precision loss is minimal (±0.005 seconds)
