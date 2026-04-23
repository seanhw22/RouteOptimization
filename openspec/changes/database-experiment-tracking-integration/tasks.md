# Implementation Tasks

## 1. Core Module Creation

- [ ] 1.1 Create `src/distance_cache.py` with DistanceCache class
  - Implement `__init__(db_session, dataset_id, coordinates)`
  - Implement `is_valid()` method with spot-check validation (3 random samples)
  - Implement `load()` method to return NumPy distance matrix from cache
  - Implement `save(dist_matrix)` method with batch insert using executemany
  - Add error handling for database connection failures

- [ ] 1.2 Create `src/experiment_tracker.py` with ExperimentTracker class
  - Implement `__init__(db_session)`
  - Implement `create_experiment(metadata)` method that returns experiment_id
  - Implement `save_result_metrics(experiment_id, metrics)` method
  - Implement `save_routes(experiment_id, routes)` method with segment storage
  - Add `load_routes(experiment_id)` helper for route reconstruction

- [ ] 1.3 Write unit tests for DistanceCache
  - Test `is_valid()` with valid cache returns True
  - Test `is_valid()` with invalid cache returns False
  - Test `is_valid()` with no cache returns False
  - Test `load()` returns correct NumPy array shape
  - Test `save()` inserts all node pairs correctly

- [ ] 1.4 Write unit tests for ExperimentTracker
  - Test `create_experiment()` returns integer experiment_id
  - Test `save_result_metrics()` inserts row with correct runtime
  - Test `save_routes()` inserts correct number of segments
  - Test `load_routes()` reconstructs routes correctly

## 2. Database Integration

- [ ] 2.1 Add dataset loading to MDVRPDataLoader
  - Verify existing `load_from_database()` method works correctly
  - Test loading from database with sample dataset_id=1
  - Ensure returned dict format matches CSV loading

- [ ] 2.2 Update `src/database.py` DatabaseConnection class
  - Verify connection pooling configuration (pool_size=10, max_overflow=20)
  - Add `get_dataset(dataset_id)` helper method
  - Add `dataset_exists(dataset_id)` validation method

- [ ] 2.3 Create database validation helper
  - Add `validate_dataset_id(db_session, dataset_id)` function
  - Raise clear error if dataset_id doesn't exist
  - Return True if valid

## 3. Solver Integration - run_greedy.py

- [ ] 3.1 Add CLI arguments to run_greedy.py
  - Add `--dataset` argument (optional, type=int)
  - Add `--db-url` argument (optional, string, overrides DATABASE_URL)
  - Default to CSV mode if no --dataset provided

- [ ] 3.2 Add database mode logic to run_greedy.py
  - Check if --dataset argument provided
  - If yes: load from database using MDVRPDataLoader.load_from_database()
  - If no: use existing CSV loading (unchanged behavior)
  - Validate dataset_id exists before proceeding

- [ ] 3.3 Integrate DistanceCache in run_greedy.py
  - Initialize DistanceCache if database mode
  - Check cache validity with `is_valid()`
  - Load from cache if valid, else compute and save
  - Pass distance matrix to MDVRPGreedy solver

- [ ] 3.4 Integrate ExperimentTracker in run_greedy.py
  - Create experiment record before solver.solve() call
  - Store experiment_id for later use
  - Save result_metrics after solver completes
  - Save routes after solver completes
  - Handle solver failures gracefully (experiment exists, no results)

- [ ] 3.5 Test run_greedy.py database mode
  - Run with `--dataset 1` and verify experiment created
  - Verify node_distances populated if first run
  - Verify node_distances used on second run (cache hit)
  - Verify result_metrics and routes stored correctly

- [ ] 3.6 Test run_greedy.py CSV mode (backward compatibility)
  - Run without --dataset argument
  - Verify behavior matches pre-integration (no database access)
  - Verify solution dict format unchanged

## 4. Solver Integration - run_hga.py

- [ ] 4.1 Add CLI arguments to run_hga.py
  - Add `--dataset` argument (optional, type=int)
  - Add `--db-url` argument (optional, string)
  - Default to CSV mode if no --dataset provided

- [ ] 4.2 Add database mode logic to run_hga.py
  - Check if --dataset argument provided
  - Load from database or CSV based on argument
  - Validate dataset_id exists

- [ ] 4.3 Integrate DistanceCache in run_hga.py
  - Initialize and use DistanceCache same as run_greedy.py
  - Pass distance matrix to MDVRPHGA solver

- [ ] 4.4 Integrate ExperimentTracker in run_hga.py
  - Create experiment record with HGA-specific parameters:
    - algorithm='HGA'
    - population_size, mutation_rate, crossover_rate, seed
  - Save result_metrics and routes after solve
  - Handle failures gracefully

- [ ] 4.5 Test run_hga.py database mode
  - Run with `--dataset 1` and verify all HGA parameters stored
  - Verify cache usage on subsequent runs
  - Verify results stored correctly

- [ ] 4.6 Test run_hga.py CSV mode
  - Verify unchanged behavior without --dataset

## 5. Solver Integration - run_milp.py

- [ ] 5.1 Add CLI arguments to run_milp.py
  - Add `--dataset` argument (optional, type=int)
  - Add `--db-url` argument (optional, string)

- [ ] 5.2 Add database mode logic to run_milp.py
  - Implement same pattern as run_greedy.py and run_hga.py
  - Validate dataset_id exists

- [ ] 5.3 Integrate DistanceCache in run_milp.py
  - Use DistanceCache for distance matrix

- [ ] 5.4 Integrate ExperimentTracker in run_milp.py
  - Create experiment record with algorithm='MILP'
  - MILP-specific parameters: seed only (no GA params)
  - Save result_metrics and routes

- [ ] 5.5 Test run_milp.py database mode
  - Verify MILP experiment stored correctly
  - Verify cache integration works

- [ ] 5.6 Test run_milp.py CSV mode
  - Verify backward compatibility

## 6. run_all.py Integration

- [ ] 6.1 Add CLI arguments to run_all.py
  - Add `--dataset` argument (optional, type=int)
  - Add `--db-url` argument (optional, string)
  - Pass both arguments to individual solver calls

- [ ] 6.2 Modify run_all.py to pass dataset to solvers
  - Update run_greedy() call to include --dataset and --db-url
  - Update run_hga() call to include --dataset and --db-url
  - Update run_milp() call to include --dataset and --db-url

- [ ] 6.3 Test run_all.py database mode
  - Run `python run_all.py --dataset 1 --db-url postgresql://...`
  - Verify 3 experiments created (one per algorithm)
  - Verify all experiments reference same dataset_id
  - Verify all results and routes stored

- [ ] 6.4 Test run_all.py CSV mode
  - Run without --dataset argument
  - Verify unchanged behavior

## 7. Route Reconstruction Testing

- [ ] 7.1 Add route reconstruction test
  - Create test that stores route segments
  - Load segments using ExperimentTracker.load_routes()
  - Verify reconstructed route matches original
  - Test with depot → C1 → C2 → C3 → depot pattern

- [ ] 7.2 Add edge case tests for routes
  - Test empty route (depot → depot only)
  - Test single customer route (depot → C1 → depot)
  - Test route with many customers (>10)

## 8. Documentation

- [ ] 8.1 Update README.md with database mode usage
  - Add section on "Database Mode"
  - Document --dataset and --db-url arguments
  - Provide examples of running solvers with database
  - Document distance caching behavior

- [ ] 8.2 Create DATABASE_USAGE.md guide
  - Explain when to use database mode vs CSV mode
  - Document environment variable setup (DATABASE_URL)
  - Provide examples of querying experiments
  - Show SQL queries for analyzing results

- [ ] 8.3 Add docstrings to new modules
  - Add comprehensive docstrings to DistanceCache
  - Add comprehensive docstrings to ExperimentTracker
  - Include usage examples in docstrings

## 9. Integration Testing

- [ ] 9.1 Create end-to-end test script
  - Test complete workflow: CSV → database → solve → store → query
  - Test all three solvers
  - Verify distance cache works on second run
  - Verify experiment tracking creates correct records

- [ ] 9.2 Test concurrent runs
  - Run two solvers simultaneously with same dataset
  - Verify no database deadlocks
  - Verify both experiments created correctly

- [ ] 9.3 Test error handling
  - Test with invalid dataset_id (should fail fast)
  - Test with database connection failure (graceful degradation)
  - Test solver failure (experiment exists, no results)

## 10. Performance Validation

- [ ] 10.1 Benchmark distance cache performance
  - Measure first run time (with cache insert)
  - Measure second run time (cache hit)
  - Verify 50-80% reduction in data loading time

- [ ] 10.2 Verify batch insert performance
  - Test with 50 nodes (2500 distance pairs)
  - Ensure cache save completes in <200ms
  - Test with 100 nodes (10000 distance pairs)

- [ ] 10.3 Verify route storage performance
  - Test with 20 vehicles, 100 customers
  - Ensure route storage completes in <100ms

## 11. Code Review and Cleanup

- [ ] 11.1 Review all modified files
  - Ensure consistent code style
  - Remove debug print statements
  - Add appropriate error handling

- [ ] 11.2 Add type hints to new modules
  - Add type hints to DistanceCache methods
  - Add type hints to ExperimentTracker methods

- [ ] 11.3 Final testing
  - Run full test suite
  - Test all three solvers in both modes
  - Verify backward compatibility
  - Check for regressions

## 12. Deployment Preparation

- [ ] 12.1 Update .env.example
  - Add DATABASE_URL example with PostgreSQL format

- [ ] 12.2 Verify requirements.txt
  - Ensure SQLAlchemy and psycopg2 are listed
  - Check version compatibility

- [ ] 12.3 Create migration notes
  - Document upgrade path for existing users
  - Note that CSV mode still works (backward compatible)
