# HGA Time Export Specification

## ADDED Requirements

### Requirement: Route time in solution dictionary
The HGA solution dictionary SHALL include route travel time for each vehicle in the routes output.

#### Scenario: Solution includes time data
- **GIVEN** HGA produces a solution
- **WHEN** solution dictionary is examined
- **THEN** solution['routes'][vehicle] contains 'time' key
- **AND** time value is greater than 0 (for non-empty routes)
- **AND** time value is in hours

#### Scenario: Time format matches distance format
- **GIVEN** solution['routes']['V1'] = {'distance': 108.73, 'time': 2.72}
- **WHEN** time value is examined
- **THEN** time is a float type
- **AND** time is rounded to 2 decimal places
- **AND** time represents total travel time in hours

### Requirement: Time calculation accuracy
Route time SHALL be calculated as the sum of travel times between consecutive nodes (depot → customers → depot) using the time matrix T.

#### Scenario: Time calculation matches manual calculation
- **GIVEN** vehicle V1 route is `[C3, C5]`
- **AND** depot is D1
- **AND** time matrix T[V1][D1][C3] = 1.5 hours
- **AND** T[V1][C3][C5] = 0.8 hours
- **AND** T[V1][C5][D1] = 0.4 hours
- **WHEN** route time is calculated
- **THEN** total time is 2.7 hours (1.5 + 0.8 + 0.4)

#### Scenario: Empty route has zero time
- **GIVEN** vehicle V2 route is empty []
- **WHEN** route time is calculated
- **THEN** time is 0.0 hours

### Requirement: Time matrix uses vehicle speed
Route time SHALL be calculated using the vehicle-specific time matrix T[vehicle], which accounts for different vehicle speeds.

#### Scenario: Different speeds produce different times
- **GIVEN** V1 speed is 40 km/h
- **AND** V2 speed is 50 km/h
- **AND** both travel same distance of 40 km
- **WHEN** route times are calculated
- **THEN** V1 time is 1.0 hours (40 km ÷ 40 km/h)
- **AND** V2 time is 0.8 hours (40 km ÷ 50 km/h)

### Requirement: Time export consistency
The time export format SHALL match the Greedy algorithm's time export format for consistency.

#### Scenario: HGA and Greedy time formats match
- **GIVEN** both HGA and Greedy solve the same problem
- **WHEN** solution dictionaries are compared
- **THEN** both have 'time' key in routes
- **AND** time values are in same units (hours)
- **AND** time values have same precision (2 decimal places)
