## ADDED Requirements

### Requirement: Interactive route map
The system SHALL render an interactive map showing vehicle routes for each completed algorithm.

#### Scenario: Map renders from GeoJSON
- **WHEN** a user views the results dashboard for a completed run batch
- **THEN** the system generates GeoJSON via the existing `MDVRPExporter.export_geojson()` function
- **AND** renders it on a Leaflet.js map with depot markers, customer markers, and color-coded route lines

#### Scenario: Algorithm selector on map
- **WHEN** multiple algorithms completed in the batch
- **THEN** the user can toggle between algorithms (Greedy / HGA / MILP) to see each algorithm's routes on the map

#### Scenario: Route tooltip
- **WHEN** a user hovers over a route line on the map
- **THEN** the map shows a tooltip with: vehicle ID, total distance, load, travel time

### Requirement: Per-route statistics table
The system SHALL display a table of per-vehicle route statistics.

#### Scenario: Route stats table
- **WHEN** a user views results for a specific algorithm
- **THEN** the system displays a table with columns: Vehicle ID, Route (stop sequence), Distance (km), Time (h), Load (kg)
- **AND** shows a summary row with totals

### Requirement: Algorithm comparison chart
The system SHALL show a bar chart comparing total distance across all completed algorithms in the batch.

#### Scenario: Comparison chart renders
- **WHEN** at least two algorithms completed in the batch
- **THEN** the system renders a Chart.js bar chart with one bar per algorithm showing total route distance
- **AND** labels each bar with the algorithm name and distance value

#### Scenario: Single algorithm result
- **WHEN** only one algorithm completed (e.g., MILP was killed)
- **THEN** the system shows the chart with a single bar and a note that other algorithms were not completed

### Requirement: Export results from dashboard
The system SHALL allow users to download solution files from the results dashboard.

#### Scenario: Download CSV
- **WHEN** a user clicks "Download CSV" for a completed experiment
- **THEN** the system generates the CSV via `MDVRPExporter.export_csv()` and serves it as a file download

#### Scenario: Download PDF
- **WHEN** a user clicks "Download PDF" for a completed experiment
- **THEN** the system generates the PDF via `MDVRPExporter.export_pdf()` and serves it as a file download

#### Scenario: Download GeoJSON
- **WHEN** a user clicks "Download GeoJSON" for a completed experiment
- **THEN** the system generates the GeoJSON via `MDVRPExporter.export_geojson()` and serves it as a file download

### Requirement: Save results for authenticated users
The system SHALL persist results permanently for authenticated users and temporarily for guests.

#### Scenario: Authenticated user results
- **WHEN** an authenticated user's run batch completes
- **THEN** the results remain accessible under "My Experiments" indefinitely

#### Scenario: Guest user results
- **WHEN** a guest user's run batch completes
- **THEN** the results are accessible for 3 days (inheriting the dataset's `expires_at`)
- **AND** a banner informs the guest that results will expire and prompts registration to save permanently
