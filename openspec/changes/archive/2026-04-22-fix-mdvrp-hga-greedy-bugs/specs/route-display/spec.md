# Route Display Specification

## ADDED Requirements

### Requirement: Route string includes depot
Route string representations SHALL include the depot at both the start and end of the route.

#### Scenario: Non-empty route display
- **GIVEN** vehicle V1 has route nodes [C3, C5]
- **AND** depot for V1 is D1
- **WHEN** route string is formatted
- **THEN** string is "D1 -> C3 -> C5 -> D1"
- **AND** format is "depot -> customers... -> depot"

#### Scenario: Empty route display
- **GIVEN** vehicle V2 has empty route nodes []
- **AND** depot for V2 is D2
- **WHEN** route string is formatted
- **THEN** string is "D2 -> D2"
- **AND** represents empty route (depot to depot)

### Requirement: Depot identification
The depot for each vehicle SHALL be obtained from the problem data's `depot_for_vehicle` mapping.

#### Scenario: Correct depot per vehicle
- **GIVEN** depot_for_vehicle = {'V1': 'D1', 'V2': 'D2'}
- **WHEN** formatting route for V1
- **THEN** depot is D1
- **WHEN** formatting route for V2
- **THEN** depot is D2

### Requirement: Consistent format across outputs
Route format SHALL be consistent across CSV export, PDF export, and console display.

#### Scenario: CSV export format
- **GIVEN** solution with V1 route [C3, C5]
- **WHEN** exported to CSV
- **THEN** route column shows "D1 -> C3 -> C5 -> D1"

#### Scenario: PDF export format
- **GIVEN** solution with V1 route [C3, C5]
- **WHEN** exported to PDF
- **THEN** route table cell shows "D1 -> C3 -> C5 -> D1"

#### Scenario: Console output format
- **GIVEN** solution with V1 route [C3, C5]
- **WHEN** printed to console
- **THEN** route display shows "D1 -> C3 -> C5 -> D1"

### Requirement: Arrow separator format
Route nodes SHALL be separated by " -> " (space, dash, dash, space) for readability.

#### Scenario: Separator consistency
- **GIVEN** route with nodes [D1, C1, C2, D1]
- **WHEN** route string is created
- **THEN** separator between all nodes is " -> "
- **AND** no trailing separator
- **AND** no leading separator

### Requirement: Node type handling
Route display SHALL handle both string node IDs (e.g., "C1", "D1") and numeric IDs.

#### Scenario: String node IDs
- **GIVEN** route nodes are strings ["C1", "C2"]
- **WHEN** route string is formatted
- **THEN** nodes appear as "C1" and "C2" in output

#### Scenario: Numeric node IDs
- **GIVEN** route nodes are integers [1, 2]
- **AND** depot is integer 0
- **WHEN** route string is formatted
- **THEN** nodes appear as "0 -> 1 -> 2 -> 0"
- **AND** integers are converted to strings for display
