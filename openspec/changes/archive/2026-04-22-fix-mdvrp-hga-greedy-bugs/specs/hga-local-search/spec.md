# HGA Local Search Specification

## ADDED Requirements

### Requirement: Deterministic local search application
The HGA mutation pipeline SHALL apply 2-opt local search to every mutated individual, not probabilistically.

#### Scenario: Local search always runs
- **GIVEN** an individual undergoes mutation
- **WHEN** mutation pipeline executes
- **THEN** 2-opt local search is ALWAYS applied to the individual
- **AND** no random probability check is performed

#### Scenario: Local search improves every mutation
- **GIVEN** population size is 20
- **AND** mutation rate is 0.2
- **WHEN** one generation of evolution occurs
- **THEN** approximately 4 individuals undergo mutation (20 × 0.2)
- **AND** all 4 mutated individuals have 2-opt local search applied
- **AND** approximately 16 unmutated individuals remain unchanged

### Requirement: 2-opt local search behavior
The 2-opt operator SHALL evaluate all possible edge swaps in each route and apply the best improvement found.

#### Scenario: 2-opt finds improving swap
- **GIVEN** vehicle route is `[C1, C2, C3, C4, C5]`
- **AND** reversing segment C2-C3-C4 reduces distance by 8.5 km
- **WHEN** 2-opt is applied
- **THEN** route becomes `[C1, C4, C3, C2, C5]`
- **AND** route distance is reduced

#### Scenario: 2-opt evaluates all swaps
- **GIVEN** vehicle route has N customers
- **WHEN** 2-opt is applied
- **THEN** system evaluates all N×(N-1)/2 possible 2-opt swaps
- **AND** applies the swap with maximum distance reduction
- **AND** iterates until no improving swap is found (local optimum)

### Requirement: Local search iteration limit
2-opt local search SHALL limit iterations to avoid excessive computation (default 10 iterations).

#### Scenario: Local search terminates at local optimum
- **GIVEN** a route that can be improved
- **WHEN** 2-opt is applied
- **THEN** system iterates until no improving swap exists
- **OR** maximum iteration limit (10) is reached
- **AND** returns the best route found

#### Scenario: Local search terminates early if no improvement
- **GIVEN** a route is already at local optimum
- **WHEN** 2-opt is applied
- **THEN** system evaluates all swaps in first iteration
- **AND** finds no improving swap
- **AND** terminates immediately (single iteration)
