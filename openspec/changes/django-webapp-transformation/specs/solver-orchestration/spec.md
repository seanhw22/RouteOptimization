## ADDED Requirements

### Requirement: Solver configuration form
The system SHALL present a configuration form allowing users to set algorithm parameters before running.

#### Scenario: HGA parameters form
- **WHEN** a user opens the solver configuration page for a dataset
- **THEN** the system displays fields for HGA: generations (default 100), population_size (default 50), mutation_rate (default 0.1), crossover_rate (default 0.8), seed (default 42)

#### Scenario: MILP availability based on node count
- **WHEN** the dataset has ≤ 25 total nodes (depots + customers)
- **THEN** the system shows MILP as an enabled option with a time_limit field (default 3600s)
- **WHEN** the dataset has > 25 total nodes
- **THEN** the system shows MILP as disabled with an explanatory note

### Requirement: Create run batch and launch subprocesses
The system SHALL create a `RunBatch` record and per-algorithm `Experiment` records, then launch solver subprocesses.

#### Scenario: Launch all algorithms
- **WHEN** a user submits the solver configuration form
- **THEN** the system creates one `RunBatch` record
- **AND** creates one `Experiment` record per enabled algorithm (Greedy, HGA, optionally MILP), each with `status='pending'`
- **AND** launches each solver as a subprocess: `python run_greedy.py --experiment-id=X`, etc.
- **AND** stores each subprocess PID in the corresponding `Experiment.pid` field
- **AND** sets each `Experiment.status = 'running'` and `Experiment.started_at = now()`
- **AND** redirects to the Live Run Viewer for this batch

#### Scenario: Subprocess receives experiment ID
- **WHEN** a solver subprocess is launched with `--experiment-id=X`
- **THEN** the subprocess loads problem data from the DB using the experiment's `dataset_id`
- **AND** writes progress updates to the `Experiment` record periodically

### Requirement: Kill a running solver
The system SHALL allow a user to kill any running solver subprocess.

#### Scenario: Kill MILP
- **WHEN** a user clicks "Skip MILP" on the Live Run Viewer
- **THEN** the system calls `process.terminate()` on the MILP subprocess using the stored PID
- **AND** sets `Experiment.status = 'killed'` and `Experiment.completed_at = now()`
- **AND** returns a JSON response confirming the kill

#### Scenario: Kill non-existent process
- **WHEN** a kill request is made for an experiment whose process is no longer alive
- **THEN** the system sets `Experiment.status = 'killed'` regardless
- **AND** returns a success response (idempotent)

#### Scenario: Kill not allowed when already complete
- **WHEN** a kill request is made for an experiment with `status='completed'`
- **THEN** the system returns a 400 response with message "Experiment already completed"

### Requirement: Recover interrupted experiments on startup
The system SHALL mark stale running experiments as interrupted when the server starts.

#### Scenario: Server restart recovery
- **WHEN** the Django application starts
- **THEN** the system queries for all experiments with `status='running'`
- **AND** sets their `status = 'interrupted'` if their PID is no longer alive
- **AND** sets `completed_at = now()` for those experiments
