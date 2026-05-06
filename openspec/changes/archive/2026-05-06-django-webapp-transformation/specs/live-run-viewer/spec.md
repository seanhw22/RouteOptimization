## ADDED Requirements

### Requirement: Display per-algorithm progress cards
The system SHALL show one progress card per algorithm in the run batch.

#### Scenario: Running algorithm card
- **WHEN** a user views the Live Run Viewer for an active run batch
- **THEN** the system displays a card for each algorithm showing: algorithm name, current status, progress percentage bar, best objective value so far, and elapsed time

#### Scenario: Completed algorithm card
- **WHEN** an algorithm's experiment reaches `status='completed'`
- **THEN** its card shows a green "Completed" badge and final metrics (total distance, runtime)

#### Scenario: Killed algorithm card
- **WHEN** an algorithm's experiment reaches `status='killed'` or `status='interrupted'`
- **THEN** its card shows a red "Killed" badge

### Requirement: Poll for progress updates
The system SHALL update the Live Run Viewer via AJAX polling without requiring a full page reload.

#### Scenario: Active poll
- **WHEN** at least one experiment in the batch has `status='running'`
- **THEN** the page JavaScript polls `GET /runs/<batch_id>/status/` every 3 seconds
- **AND** updates all algorithm cards with fresh data from the response

#### Scenario: Poll stops when all complete
- **WHEN** all experiments in the batch have a terminal status (`completed`, `killed`, `interrupted`, `failed`)
- **THEN** the JavaScript stops polling
- **AND** displays a "View Results" button linking to the results dashboard

### Requirement: Display execution log
The system SHALL show a scrollable log of recent progress messages for each algorithm.

#### Scenario: Log line display
- **WHEN** a solver subprocess appends a log line to `Experiment.progress_log`
- **THEN** the Live Run Viewer shows the last 20 log lines for that algorithm on the next poll

#### Scenario: Log line cap
- **WHEN** `Experiment.progress_log` would exceed 100 stored lines
- **THEN** the solver subprocess truncates the oldest entries before appending new ones

### Requirement: Status polling endpoint
The system SHALL provide a JSON endpoint for the Live Run Viewer to query batch status.

#### Scenario: Status response structure
- **WHEN** JavaScript calls `GET /runs/<batch_id>/status/`
- **THEN** the system returns JSON with: `batch_status` (all_complete bool), and per-algorithm: `status`, `progress_pct`, `best_objective`, `elapsed_seconds`, `log_tail` (last 20 lines)

#### Scenario: Unauthorized status request
- **WHEN** a user requests status for a batch they do not own
- **THEN** the system returns a 404 response
