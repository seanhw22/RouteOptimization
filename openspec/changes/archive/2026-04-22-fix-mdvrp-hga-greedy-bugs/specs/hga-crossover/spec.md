# HGA Crossover Specification

## ADDED Requirements

### Requirement: Vehicle-scoped order crossover
The HGA crossover operator SHALL apply Order Crossover (OX) independently to each vehicle's customer segment, preserving depot positions and vehicle-depot assignments.

#### Scenario: Crossover produces valid offspring
- **WHEN** two parent chromosomes undergo crossover
- **THEN** offspring chromosomes have depots in same positions as parents
- **AND** each vehicle's customer segment is recombined using OX
- **AND** depot-for-vehicle assignments remain unchanged

#### Scenario: Crossover generates genetic diversity
- **WHEN** HGA runs for multiple generations with crossover enabled
- **THEN** solutions in population SHALL differ from each other
- **AND** final solution SHALL differ from MILP solution
- **AND** population fitness SHALL show variance (not all identical)

### Requirement: Crossover respects chromosome structure
The crossover operator SHALL treat the MDVRP chromosome as a sequence of depot-delimited vehicle routes, not as a flat permutation of all customers.

#### Scenario: Single vehicle route crossover
- **GIVEN** parent1 has route `[D1, C1, C2, C3, D2, C4, D1]` (V1: C1,C2,C3; V2: C4)
- **AND** parent2 has route `[D1, C4, C2, D2, C1, C3, D1]` (V1: C4,C2; V2: C1,C3)
- **WHEN** crossover is applied
- **THEN** offspring V1 segment contains subset of {C1, C2, C3, C4} in OX pattern
- **AND** offspring V2 segment contains remaining customers in OX pattern
- **AND** depots D1 and D2 remain at same positions

### Requirement: Crossover probability
The crossover operator SHALL be applied to offspring pairs based on the configured crossover rate (default 0.8).

#### Scenario: Crossover rate controls application
- **GIVEN** crossover rate is 0.8
- **WHEN** 100 offspring pairs are generated
- **THEN** approximately 80 pairs undergo crossover
- **AND** approximately 20 pairs are copied without crossover
