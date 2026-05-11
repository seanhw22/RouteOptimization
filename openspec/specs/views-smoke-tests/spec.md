## ADDED Requirements

### Requirement: Dataset views return correct HTTP responses
The test suite SHALL verify that dataset views respond with expected status codes for authenticated and guest users.

#### Scenario: GET upload page — authenticated user
- **WHEN** an authenticated client GETs `/datasets/upload/`
- **THEN** response status is 200

#### Scenario: GET upload page — unauthenticated redirect
- **WHEN** an anonymous client (no guest flag) GETs `/datasets/upload/`
- **THEN** response redirects to the login page

#### Scenario: GET dataset list — authenticated user
- **WHEN** an authenticated client GETs `/datasets/`
- **THEN** response status is 200

#### Scenario: GET dataset detail — owner
- **WHEN** the owning authenticated client GETs `/datasets/<id>/`
- **THEN** response status is 200

#### Scenario: GET dataset detail — non-owner returns 404
- **WHEN** a different authenticated user GETs `/datasets/<id>/` they do not own
- **THEN** response status is 404

### Requirement: Runs configure view creates batch and redirects
The test suite SHALL verify the configure POST flow creates a batch and redirects to the viewer.

#### Scenario: Valid POST creates batch and redirects
- **WHEN** the owning client POSTs a valid solver config form to `/runs/configure/<dataset_id>/`
- **THEN** a `RunBatch` row is created, `launch_all` is called once, and the response redirects to the viewer URL

#### Scenario: GET configure page returns 200
- **WHEN** the owning client GETs `/runs/configure/<dataset_id>/`
- **THEN** response status is 200

### Requirement: Runs status endpoint returns correct JSON shape
The test suite SHALL verify that the polling endpoint returns a well-formed JSON payload.

#### Scenario: Status response for a pending batch
- **WHEN** the owning client GETs `/runs/status/<batch_id>/`
- **THEN** response is JSON with keys `batch_status` and `experiments`; `experiments` is a list

### Requirement: Kill endpoint returns JSON confirmation
The test suite SHALL verify the kill endpoint returns `{"ok": true}` for a running experiment.

#### Scenario: Kill a running experiment
- **WHEN** the owning client POSTs to `/runs/kill/<batch_id>/<exp_id>/` for a running experiment
- **THEN** response is JSON with `ok=True` and experiment status becomes `killed`
