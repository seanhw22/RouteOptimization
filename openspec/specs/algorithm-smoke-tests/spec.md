## ADDED Requirements

### Requirement: Greedy solver runs and returns a valid solution
The test suite SHALL verify that `MDVRPGreedy` produces a non-empty solution on the `tiny_problem` fixture.

#### Scenario: Greedy returns completed status
- **WHEN** `MDVRPGreedy` is instantiated with `tiny_problem` data and `solve()` is called
- **THEN** the returned status is `'completed'`

#### Scenario: Greedy covers all customers
- **WHEN** `MDVRPGreedy.solve()` completes on `tiny_problem`
- **THEN** every customer in the problem appears in exactly one route

#### Scenario: Greedy solution has positive fitness
- **WHEN** `MDVRPGreedy.solve()` completes on `tiny_problem`
- **THEN** `solution['fitness']` is a positive float

### Requirement: HGA solver runs and returns a valid solution
The test suite SHALL verify that `MDVRPHGA` produces a non-empty solution on the `tiny_problem` fixture using minimal generations.

#### Scenario: HGA returns completed status
- **WHEN** `MDVRPHGA` is instantiated with `tiny_problem` data, `population_size=4, generations=2`, and `solve()` is called
- **THEN** the returned status is `'completed'`

#### Scenario: HGA covers all customers
- **WHEN** `MDVRPHGA.solve()` completes on `tiny_problem`
- **THEN** every customer in the problem appears in at least one route across all vehicles

#### Scenario: HGA solution has positive fitness
- **WHEN** `MDVRPHGA.solve()` completes on `tiny_problem`
- **THEN** `solution['fitness']` is a positive float
