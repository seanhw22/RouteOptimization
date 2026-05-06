## ADDED Requirements

### Requirement: create_batch creates a RunBatch row
The test suite SHALL verify that `create_batch` persists a `RunBatch` linked to the given dataset.

#### Scenario: Authenticated user batch
- **WHEN** `create_batch` is called with a user and a dataset
- **THEN** a `RunBatch` row exists with `status='pending'` and correct `user` and `dataset` FK

#### Scenario: Guest batch gets share token
- **WHEN** `create_batch` is called with `user=None` and a session key
- **THEN** the batch has `share_token` set and `session_key` matches the input

### Requirement: create_experiments creates correct Experiment rows
The test suite SHALL verify that `create_experiments` creates one `Experiment` per enabled algorithm.

#### Scenario: Both Greedy and HGA enabled
- **WHEN** config has `run_greedy=True, run_hga=True, run_milp=False`
- **THEN** exactly two Experiment rows are created with algorithms `Greedy` and `HGA`

#### Scenario: HGA params are stored
- **WHEN** config includes `population_size=10, generations=5, mutation_rate=0.1, crossover_rate=0.8`
- **THEN** the HGA Experiment row stores those values

#### Scenario: No algorithms selected creates no experiments
- **WHEN** config has all `run_*` flags False
- **THEN** zero Experiment rows are created
