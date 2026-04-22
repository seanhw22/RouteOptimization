# HGA Elitism Specification

## ADDED Requirements

### Requirement: Elite preservation
The HGA evolution loop SHALL preserve the top N elite individuals from each generation and inject them unchanged into the next generation.

#### Scenario: Elites survive to next generation
- **GIVEN** elite size is 3
- **AND** current generation has 20 individuals
- **WHEN** evolution produces next generation
- **THEN** the 3 best individuals from current generation SHALL be in next generation
- **AND** their fitness values SHALL remain unchanged

#### Scenario: Elites not replaced by offspring
- **GIVEN** elite size is 3
- **AND** population size is 20
- **WHEN** generating offspring
- **THEN** system SHALL generate 17 offspring (20 - 3 elites)
- **AND** next generation SHALL contain 3 elites + 17 offspring

### Requirement: Elite selection by fitness
Elites SHALL be selected as the individuals with the best (lowest) fitness values in the current population.

#### Scenario: Elites are best solutions
- **GIVEN** population sorted by fitness (ascending)
- **AND** elite size is 3
- **THEN** elites are individuals at indices 0, 1, 2
- **AND** no non-elite individual has better fitness than any elite

### Requirement: Elites bypass genetic operators
Elite individuals SHALL NOT undergo crossover or mutation when preserved to the next generation.

#### Scenario: Elites remain unchanged
- **GIVEN** an individual is selected as elite
- **WHEN** elite is copied to next generation
- **THEN** elite's chromosome SHALL be identical
- **AND** elite's fitness SHALL remain valid (no re-evaluation needed)

### Requirement: Configurable elite size
The elite size SHALL be configurable via the `elite_size` parameter (default 3).

#### Scenario: Different elite sizes
- **WHEN** elite size is set to 2
- **THEN** 2 best individuals are preserved each generation
- **WHEN** elite size is set to 5
- **THEN** 5 best individuals are preserved each generation
- **AND** elite size MUST be less than population size
