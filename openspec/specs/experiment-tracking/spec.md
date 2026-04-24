# Capability: Experiment Tracking

## ADDED Requirements

### Requirement: Create experiment record before solver runs

The system SHALL create a record in the `experiments` table before invoking the solver to track each solver run.

#### Scenario: Create experiment for HGA
- **WHEN** solver runs HGA algorithm with database mode
- **THEN** system creates experiment record with algorithm='HGA'
- **AND** system includes population_size, mutation_rate, crossover_rate, seed
- **AND** system links to dataset via dataset_id foreign key
- **AND** system receives experiment_id (SERIAL primary key)

#### Scenario: Create experiment for Greedy
- **WHEN** solver runs Greedy algorithm with database mode
- **THEN** system creates experiment record with algorithm='Greedy'
- **AND** system includes seed parameter
- **AND** system sets population_size, mutation_rate, crossover_rate to NULL
- **AND** system receives experiment_id

#### Scenario: Create experiment for MILP
- **WHEN** solver runs MILP algorithm with database mode
- **THEN** system creates experiment record with algorithm='MILP'
- **AND** system includes seed parameter if specified
- **AND** system sets GA-specific parameters to NULL
- **AND** system receives experiment_id

### Requirement: Store all solver parameters

The system SHALL store all relevant solver parameters in the experiments table for reproducibility.

#### Scenario: HGA parameters
- **WHEN** creating experiment for HGA
- **THEN** system stores: population_size, mutation_rate, crossover_rate, seed

#### Scenario: Greedy parameters
- **WHEN** creating experiment for Greedy
- **THEN** system stores: seed (random seed for reproducibility)

#### Scenario: MILP parameters
- **WHEN** creating experiment for MILP
- **THEN** system stores: seed (if used by solver)

### Requirement: Use experiment_id for result linking

The system SHALL use the returned experiment_id to link results and routes to the experiment.

#### Scenario: Link results to experiment
- **WHEN** solver completes and returns results
- **THEN** system saves results using the experiment_id created before solving
- **AND** result_metrics row references experiment_id via foreign key

#### Scenario: Link routes to experiment
- **WHEN** solver completes and returns routes
- **THEN** system saves routes using the experiment_id created before solving
- **AND** routes rows reference experiment_id via foreign key

### Requirement: Support run_all with multiple experiments

The system SHALL create separate experiment records for each algorithm when run_all executes.

#### Scenario: run_all creates 3 experiments
- **WHEN** run_all.py executes with --dataset argument
- **THEN** system creates experiment record for Greedy run
- **AND** system creates experiment record for HGA run
- **AND** system creates experiment record for MILP run
- **AND** each experiment has unique experiment_id
- **AND** all experiments reference the same dataset_id

### Requirement: Provide opt-in via CLI argument

The system SHALL only create experiment records when --dataset argument is provided.

#### Scenario: Database mode with --dataset
- **WHEN** solver runs with --dataset 1 argument
- **THEN** system creates experiment record
- **AND** system tracks run in database

#### Scenario: CSV mode without --dataset
- **WHEN** solver runs without --dataset argument
- **THEN** system does NOT create experiment record
- **AND** system behaves as before integration

### Requirement: Validate dataset exists before creating experiment

The system SHALL validate that the specified dataset_id exists before creating experiment record.

#### Scenario: Valid dataset_id
- **WHEN** solver runs with --dataset 1
- **AND** dataset with dataset_id=1 exists in database
- **THEN** system proceeds to create experiment record

#### Scenario: Invalid dataset_id
- **WHEN** solver runs with --dataset 999
- **AND** dataset with dataset_id=999 does NOT exist
- **THEN** system aborts with error message "Dataset 999 not found"
- **AND** system does NOT create experiment record
- **AND** system does NOT run solver
