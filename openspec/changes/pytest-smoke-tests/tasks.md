## 1. Scaffolding (already done)

- [x] 1.1 Add `pytest-django>=4.8` to `requirements.txt`
- [x] 1.2 Create `pytest.ini` at project root
- [x] 1.3 Create `tests/conftest.py` with all shared fixtures

## 2. Dataset Service Tests

- [ ] 2.1 Create `tests/test_dataset_service.py`
- [ ] 2.2 Test `validate_frames` rejects missing column
- [ ] 2.3 Test `validate_frames` rejects duplicate primary key
- [ ] 2.4 Test `validate_frames` rejects bad referential integrity (orders → customers)
- [ ] 2.5 Test `validate_frames` passes on valid `minimal_frames`
- [ ] 2.6 Test `save_dataset` persists correct entity counts
- [ ] 2.7 Test `save_dataset` guest path sets `expires_at` and `share_token`
- [ ] 2.8 Test `save_dataset` authenticated path leaves `expires_at` as None
- [ ] 2.9 Test `parse_uploaded` with five in-memory CSV file objects returns correct keys

## 3. Runs Service Tests

- [ ] 3.1 Create `tests/test_runs_service.py`
- [ ] 3.2 Test `create_batch` for authenticated user (status, FK)
- [ ] 3.3 Test `create_batch` for guest (share_token set, session_key stored)
- [ ] 3.4 Test `create_experiments` with Greedy + HGA creates two rows
- [ ] 3.5 Test `create_experiments` HGA row stores population/generation/rate params
- [ ] 3.6 Test `create_experiments` with no algorithms creates zero rows

## 4. Dataset View Smoke Tests

- [ ] 4.1 Create `tests/test_views_datasets.py`
- [ ] 4.2 Test GET `/datasets/upload/` → 200 for `auth_client`
- [ ] 4.3 Test GET `/datasets/upload/` → redirect for anonymous client
- [ ] 4.4 Test GET `/datasets/` → 200 for `auth_client`
- [ ] 4.5 Test GET `/datasets/<id>/` → 200 for owner (`auth_client`)
- [ ] 4.6 Test GET `/datasets/<id>/` → 404 for non-owner

## 5. Runs View Smoke Tests

- [ ] 5.1 Create `tests/test_views_runs.py`
- [ ] 5.2 Test GET `/runs/configure/<dataset_id>/` → 200 for owner
- [ ] 5.3 Test POST `/runs/configure/<dataset_id>/` creates batch, calls `launch_all`, redirects (mock `launch_all`)
- [ ] 5.4 Test GET `/runs/status/<batch_id>/` → JSON with `batch_status` and `experiments` keys
- [ ] 5.5 Test POST `/runs/kill/<batch_id>/<exp_id>/` → `{"ok": true}` and experiment status `killed`

## 6. Algorithm Smoke Tests

- [ ] 6.1 Create `tests/test_algorithms.py`
- [ ] 6.2 Test `MDVRPGreedy.solve()` on `tiny_problem` returns status `'completed'`
- [ ] 6.3 Test Greedy solution covers all customers
- [ ] 6.4 Test Greedy `solution['fitness']` is positive
- [ ] 6.5 Test `MDVRPHGA.solve()` on `tiny_problem` (`population_size=4, generations=2`) returns status `'completed'`
- [ ] 6.6 Test HGA solution covers all customers
- [ ] 6.7 Test HGA `solution['fitness']` is positive

## 7. Verification

- [ ] 7.1 Run `pytest` from project root — all tests pass with no PostgreSQL connection
