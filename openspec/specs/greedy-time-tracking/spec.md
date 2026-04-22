# Greedy Time Tracking Specification

## ADDED Requirements

### Requirement: Time increase calculation before insertion
The Greedy `insert_customer` method SHALL calculate the time increase BEFORE inserting the customer into the route.

#### Scenario: Time calculation order
- **GIVEN** vehicle V2 has empty route []
- **AND** customer C1 is to be inserted at position 0
- **WHEN** insert_customer is called
- **THEN** calculate_time_increase is called FIRST (route is empty)
- **AND** customer is inserted SECOND
- **AND** route_time is updated THIRD

#### Scenario: Time increase reflects actual delta
- **GIVEN** route is empty []
- **AND** inserting C1 at position 0
- **AND** time from depot D2 to C1 is 0.5 hours
- **AND** time from C1 to depot D2 is 0.5 hours
- **WHEN** time increase is calculated
- **THEN** time increase is 1.0 hours (0.5 + 0.5)
- **AND** route_time becomes 1.0 hours (not 0.0)

### Requirement: Correct time accumulation
Route time SHALL accumulate correctly as customers are inserted, reflecting the total travel time for the complete route.

#### Scenario: Time accumulates with each insertion
- **GIVEN** vehicle V1 starts with empty route and time = 0.0
- **WHEN** C3 is inserted (adds 1.5 hours)
- **THEN** route_time[V1] = 1.5 hours
- **WHEN** C5 is inserted (adds 1.2 hours)
- **THEN** route_time[V1] = 2.7 hours (1.5 + 1.2)

#### Scenario: Final route time matches manual calculation
- **GIVEN** vehicle V1 final route is [C3, C5]
- **AND** depot is D1
- **AND** T[V1][D1][C3] = 1.5, T[V1][C3][C5] = 0.8, T[V1][C5][D1] = 0.4
- **WHEN** route_time is examined after all insertions
- **THEN** route_time[V1] = 2.7 hours
- **AND** manual calculation: 1.5 + 0.8 + 0.4 = 2.7 hours

### Requirement: Time increase uses insertion position
Time increase calculation SHALL account for the position where the customer is inserted in the route.

#### Scenario: Insert at beginning
- **GIVEN** existing route is [C2, C3]
- **AND** inserting C1 at position 0 (before C2)
- **WHEN** time increase is calculated
- **THEN** delta = (depot→C1) + (C1→C2) - (depot→C2)

#### Scenario: Insert in middle
- **GIVEN** existing route is [C1, C3]
- **AND** inserting C2 at position 1 (between C1 and C3)
- **WHEN** time increase is calculated
- **THEN** delta = (C1→C2) + (C2→C3) - (C1→C3)

#### Scenario: Insert at end
- **GIVEN** existing route is [C1, C2]
- **AND** inserting C3 at position 2 (after C2)
- **WHEN** time increase is calculated
- **THEN** delta = (C2→C3) + (C3→depot) - (C2→depot)

### Requirement: Time export accuracy
The exported solution SHALL include correct route times that match the accumulated time during construction.

#### Scenario: Exported time equals accumulated time
- **GIVEN** Greedy completes with route_time[V1] = 2.7 hours
- **WHEN** solution is exported
- **THEN** solution['routes']['V1']['time'] = 2.7 hours
- **AND** time is not 0.0

#### Scenario: All routes have valid times
- **GIVEN** Greedy completes with 2 vehicles
- **WHEN** solution is exported
- **THEN** solution['routes']['V1']['time'] > 0 (or 0.0 if empty)
- **AND** solution['routes']['V2']['time'] > 0 (or 0.0 if empty)
- **AND** times are in hours with 2 decimal places
