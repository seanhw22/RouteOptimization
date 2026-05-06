## ADDED Requirements

### Requirement: User registration
The system SHALL allow new users to register with an email and password.

#### Scenario: Successful registration
- **WHEN** a visitor submits a valid registration form with email and password
- **THEN** the system creates a Django auth user account
- **AND** logs the user in automatically
- **AND** redirects to the dashboard

#### Scenario: Duplicate email rejected
- **WHEN** a visitor submits a registration form with an email already in use
- **THEN** the system displays an error message indicating the email is taken
- **AND** does NOT create a new account

### Requirement: User login and logout
The system SHALL allow registered users to log in and out.

#### Scenario: Successful login
- **WHEN** a registered user submits valid email and password
- **THEN** the system authenticates the user and creates a Django session
- **AND** redirects to the dashboard

#### Scenario: Failed login
- **WHEN** a user submits an incorrect email or password
- **THEN** the system displays a generic "Invalid credentials" error
- **AND** does NOT reveal which field was wrong

#### Scenario: Logout
- **WHEN** an authenticated user clicks logout
- **THEN** the system destroys the session
- **AND** redirects to the login page

### Requirement: Guest (anonymous) session
The system SHALL allow users to proceed without registering as a guest.

#### Scenario: Continue as guest
- **WHEN** a visitor clicks "Continue as Guest" on the auth page
- **THEN** the system assigns a Django anonymous session
- **AND** stores a `is_guest=True` flag in the session
- **AND** redirects to the dataset upload page

#### Scenario: Guest dataset ownership
- **WHEN** a guest user creates a dataset
- **THEN** the system stores the dataset ID in `request.session['guest_datasets']`
- **AND** sets `expires_at = now() + 3 days` on the dataset record
- **AND** does NOT require a user_id foreign key

#### Scenario: Guest session expiry
- **WHEN** the `cleanup_expired_datasets` management command runs
- **THEN** the system deletes all datasets whose `expires_at` is in the past and have no authenticated user owner
- **AND** cascades deletion to associated experiments, routes, and result_metrics

### Requirement: Dataset ownership enforcement
The system SHALL prevent users from accessing datasets or experiments they do not own.

#### Scenario: Authenticated user access
- **WHEN** an authenticated user requests a dataset detail page
- **AND** the dataset's `user_id` matches the requesting user
- **THEN** the system displays the dataset

#### Scenario: Unauthorized dataset access
- **WHEN** a user requests a dataset that belongs to a different user or a different guest session
- **THEN** the system returns a 404 response

#### Scenario: Guest access to own datasets
- **WHEN** a guest user requests a dataset detail page
- **AND** the dataset ID is in `request.session['guest_datasets']`
- **THEN** the system displays the dataset
