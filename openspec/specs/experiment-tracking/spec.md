# Capability: Experiment Tracking

## ADDED Requirements

### Requirement: Create experiment record before solver runs

The system SHALL create a record in the `experiments` table before invoking the solver to track each solver run.

#### Scenario: Create experiment for HGA
- **WHEN** solver runs HGA algorithm via the web interface or with database mode
- **THEN** system creates experiment record with algorithm='HGA'
- **AND** system includes population_size, mutation_rate, crossover_rate, seed
- **AND** system links to dataset via dataset_id foreign key
- **AND** system sets status='pending', pid=NULL, progress_pct=0
- **AND** system sets run_batch_id foreign key

#### Scenario: Create experiment for Greedy
- **WHEN** solver runs Greedy algorithm via the web interface or with database mode
- **THEN** system creates experiment record with algorithm='Greedy'
- **AND** system includes seed parameter
- **AND** system sets population_size, mutation_rate, crossover_rate to NULL
- **AND** system sets status='pending', pid=NULL, progress_pct=0
- **AND** system sets run_batch_id foreign key

#### Scenario: Create experiment for MILP
- **WHEN** solver runs MILP algorithm via the web interface or with database mode
- **THEN** system creates experiment record with algorithm='MILP'
- **AND** system includes seed parameter if specified
- **AND** system sets GA-specific parameters to NULL
- **AND** system sets status='pending', pid=NULL, progress_pct=0
- **AND** system sets run_batch_id foreign key

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

### Requirement: Track experiment lifecycle status
The system SHALL track the execution lifecycle of each experiment via a `status` field.

#### Scenario: Initial status on creation
- **WHEN** a new experiment record is created via the web interface
- **THEN** the system sets `status = 'pending'`

#### Scenario: Status transitions
- **WHEN** the solver subprocess is launched and the PID stored
- **THEN** the system sets `status = 'running'` and `started_at = now()`
- **WHEN** the solver subprocess exits successfully
- **THEN** the system sets `status = 'completed'` and `completed_at = now()`
- **WHEN** the solver subprocess is killed via user request
- **THEN** the system sets `status = 'killed'` and `completed_at = now()`
- **WHEN** the solver subprocess exits with a non-zero code
- **THEN** the system sets `status = 'failed'` and `completed_at = now()`

### Requirement: Store subprocess PID for kill support
The system SHALL store the OS-level PID of each solver subprocess.

#### Scenario: PID stored on launch
- **WHEN** a solver subprocess is launched
- **THEN** the system stores the process PID in `Experiment.pid`

#### Scenario: PID used for termination
- **WHEN** a kill request is received for an experiment
- **THEN** the system reads `Experiment.pid` and calls `process.terminate()` using that PID

### Requirement: Store live progress data
The system SHALL allow solver subprocesses to write progress updates to the experiment record.

#### Scenario: Progress percentage update
- **WHEN** the HGA solver completes a generation
- **THEN** the subprocess writes `progress_pct = int(generation / total_generations * 100)` to the experiment record

#### Scenario: Best objective update
- **WHEN** the solver finds a new best solution
- **THEN** the subprocess writes the best total distance to `best_objective`

#### Scenario: Log line append
- **WHEN** the solver has a progress message (e.g., "Generation 50/100: best=123.4")
- **THEN** the subprocess appends the message to `progress_log` (JSON array of strings)
- **AND** truncates to the most recent 100 entries if the array exceeds that length

### Requirement: Link experiments to a run batch
The system SHALL associate each experiment with a `RunBatch` via foreign key.

#### Scenario: Batch FK on creation
- **WHEN** a user triggers a solver run from the web interface
- **THEN** all experiments created in that run share the same `run_batch_id` foreign key

#### Scenario: Query all experiments in a batch
- **WHEN** the Live Run Viewer requests batch status
- **THEN** the system can retrieve all experiments for the batch with a single query on `run_batch_id`
