## ADDED Requirements

### Requirement: Upload dataset via CSV files
The system SHALL accept a ZIP archive or individual CSV file uploads for depots, customers, vehicles, items, and orders.

#### Scenario: Valid CSV upload
- **WHEN** a user uploads CSV files matching the expected schema (depot_id/x/y, customer_id/x/y/deadline_hours, etc.)
- **THEN** the system parses and validates the data
- **AND** displays a preview table for each entity type
- **AND** prompts the user to confirm before saving

#### Scenario: Invalid CSV schema
- **WHEN** a user uploads a CSV file missing required columns (e.g., `deadline_hours`)
- **THEN** the system displays a specific error identifying the missing column
- **AND** does NOT save any data

#### Scenario: Duplicate entity IDs
- **WHEN** a user uploads a CSV file containing duplicate `depot_id` or `customer_id` values
- **THEN** the system displays a warning listing the duplicate IDs
- **AND** does NOT save the dataset

### Requirement: Upload dataset via XLSX file
The system SHALL accept a single Excel file with sheets named `depots`, `customers`, `vehicles`, `orders`, `items`.

#### Scenario: Valid XLSX upload
- **WHEN** a user uploads a valid XLSX file with all required sheets
- **THEN** the system processes it identically to CSV upload
- **AND** displays a preview and confirmation prompt

#### Scenario: Missing sheet in XLSX
- **WHEN** a user uploads an XLSX file missing a required sheet (e.g., `vehicles`)
- **THEN** the system displays an error identifying the missing sheet
- **AND** does NOT save any data

### Requirement: Save validated dataset to database
The system SHALL persist a confirmed valid dataset to the database via Django ORM.

#### Scenario: Authenticated user saves dataset
- **WHEN** an authenticated user confirms a valid dataset
- **THEN** the system creates a `Dataset` record linked to `user_id`
- **AND** inserts all nodes, depots, customers, vehicles, items, and orders
- **AND** redirects to the solver configuration page for this dataset

#### Scenario: Guest user saves dataset
- **WHEN** a guest user confirms a valid dataset
- **THEN** the system creates a `Dataset` record with `user_id=NULL` and `expires_at = now() + 3 days`
- **AND** adds the `dataset_id` to `request.session['guest_datasets']`
- **AND** redirects to the solver configuration page

### Requirement: Dataset name and listing
The system SHALL allow users to name datasets and view their previously uploaded datasets.

#### Scenario: Name a dataset
- **WHEN** a user confirms a dataset upload
- **THEN** the system requires a non-empty dataset name
- **AND** stores it in the `Dataset.name` field

#### Scenario: List own datasets
- **WHEN** an authenticated user visits the datasets list page
- **THEN** the system displays all datasets belonging to that user, ordered by creation date descending

#### Scenario: Node count display
- **WHEN** a dataset is listed or viewed
- **THEN** the system displays the total node count (depots + customers)
- **AND** indicates whether MILP will be available (node count ≤ 25)
