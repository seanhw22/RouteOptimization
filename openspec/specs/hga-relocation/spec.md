# HGA Relocation Local Search Specification

## ADDED Requirements

### Requirement: Intra-route relocation
The relocation operator SHALL attempt to move each customer to different positions within its current route to find improvements.

#### Scenario: Intra-route relocation finds better position
- **GIVEN** vehicle route is `[C1, C2, C3, C4]`
- **AND** moving C3 from position 2 to position 0 reduces distance by 5.2 km
- **WHEN** relocation is applied
- **THEN** route becomes `[C3, C1, C2, C4]`
- **AND** route distance is reduced

#### Scenario: Intra-route relocation evaluates all positions
- **GIVEN** vehicle route has N customers
- **WHEN** intra-route relocation runs
- **THEN** system evaluates moving each customer to each of N possible positions
- **AND** selects the move with maximum distance reduction
- **AND** applies the move only if it improves the route

### Requirement: Inter-route relocation
If intra-route relocation finds no improvement, the operator SHALL attempt to move customers to different vehicles' routes.

#### Scenario: Inter-route relocation balances load
- **GIVEN** V1 route is overloaded (42 kg load, 40 kg capacity)
- **AND** V2 route has spare capacity
- **AND** moving C5 from V1 to V2 reduces penalties
- **WHEN** inter-route relocation runs
- **THEN** C5 is moved from V1 route to V2 route
- **AND** total solution fitness improves

#### Scenario: Inter-route relocation respects capacity
- **GIVEN** V1 route has customer C7 with demand 10 kg
- **AND** V2 route current load is 38 kg (capacity 40 kg)
- **WHEN** evaluating moving C7 to V2
- **THEN** move is rejected due to capacity violation
- **AND** system evaluates alternative moves

### Requirement: Relocation improves solutions
The relocation operator SHALL only apply moves that result in lower total distance or reduced penalties.

#### Scenario: No beneficial moves found
- **GIVEN** all possible relocations increase distance or penalties
- **WHEN** relocation operator runs
- **THEN** route remains unchanged
- **AND** original route is returned

### Requirement: Relocation integrates with mutation pipeline
Relocation SHALL be applied after 2-opt local search in the mutation pipeline.

#### Scenario: Combined local search
- **GIVEN** an individual after mutation
- **WHEN** mutation pipeline executes
- **THEN** swap mutation is applied first
- **AND** 2-opt local search is applied second
- **AND** relocation is applied third
- **AND** result is an improved individual
