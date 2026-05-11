## ADDED Requirements

### Requirement: validate_frames rejects bad data
The test suite SHALL verify that `validate_frames` raises `DatasetValidationError` for common invalid inputs.

#### Scenario: Missing required column
- **WHEN** a DataFrame is missing a required column (e.g., `depot_id` from depots)
- **THEN** `DatasetValidationError` is raised mentioning the missing column

#### Scenario: Duplicate primary key
- **WHEN** the depots DataFrame contains two rows with the same `depot_id`
- **THEN** `DatasetValidationError` is raised mentioning the duplicate id

#### Scenario: Referential integrity — unknown customer in orders
- **WHEN** orders references a `customer_id` not present in customers
- **THEN** `DatasetValidationError` is raised

#### Scenario: Valid frames pass without error
- **WHEN** `validate_frames` is called with the `minimal_frames` fixture
- **THEN** no exception is raised

### Requirement: save_dataset persists all entities
The test suite SHALL verify that `save_dataset` creates the correct DB rows for each entity type.

#### Scenario: Dataset and child counts match input
- **WHEN** `save_dataset` is called with `minimal_frames` (2 depots, 3 customers, 2 vehicles, 1 item, 3 orders)
- **THEN** the returned Dataset has 2 depots, 3 customers, 2 vehicles, 1 item, 3 orders in the DB

#### Scenario: Guest dataset gets expiry and share token
- **WHEN** `save_dataset` is called with `is_guest=True`
- **THEN** `expires_at` is set and `share_token` is not None

#### Scenario: Authenticated dataset has no expiry
- **WHEN** `save_dataset` is called with a user and `is_guest=False`
- **THEN** `expires_at` is None

### Requirement: parse_uploaded handles CSV input
The test suite SHALL verify that `parse_uploaded` correctly reads five in-memory CSV files.

#### Scenario: Five valid CSVs return correct keys
- **WHEN** `parse_uploaded` is called with five in-memory CSV file objects keyed by entity name
- **THEN** the returned dict has keys `depots`, `customers`, `vehicles`, `items`, `orders`
