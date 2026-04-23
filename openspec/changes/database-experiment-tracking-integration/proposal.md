# Proposal: Database Experiment Tracking Integration

## Why

The MDVRP system currently has database tables for experiments, results, routes, and distance caching, but they are completely unused. Solvers run in isolation with no experiment tracking, making it impossible to:
- Compare solver performance across runs
- Identify which parameter combinations work best
- Cache expensive distance computations between runs
- Reconstruct and analyze historical routing solutions

This integration will enable proper experiment tracking, performance analysis, and computational efficiency through distance caching.

## What Changes

### Database Integration
- **Distance caching layer**: Cache computed node distances in `node_distances` table with validation
- **Experiment tracking**: Create `experiments` records for each solver run (Greedy, HGA, MILP)
- **Result storage**: Store solver runtime in `result_metrics` table
- **Route persistence**: Store route segments in `routes` table for solution reconstruction

### Solver Integration
- Modify `run_greedy.py`, `run_hga.py`, `run_milp.py` to:
  - Accept `--dataset` CLI argument to load from database
  - Check distance cache before computing
  - Create experiment record before solving
  - Save results/routes to database after solving
- Modify `run_all.py` to pass dataset ID to individual solvers

### New Modules
- `src/distance_cache.py`: Handle distance caching logic with validation
- `src/experiment_tracker.py`: Handle experiment/result/route database operations
- `scripts/load_dataset.py`: Helper to load dataset by ID

## Capabilities

### New Capabilities
- `distance-caching`: Cache and validate computed node distances to avoid redundant calculations
- `experiment-tracking`: Track solver runs with parameters, timestamps, and dataset context
- `result-storage`: Store solver runtime metrics for performance analysis
- `route-persistence`: Store route segments for solution reconstruction and analysis

### Modified Capabilities
- None (existing solver behavior preserved, only adding database integration)

## Impact

### Code Changes
- **Modified**: `individual_runs/run_greedy.py`, `individual_runs/run_hga.py`, `individual_runs/run_milp.py`, `individual_runs/run_all.py`
- **New**: `src/distance_cache.py`, `src/experiment_tracker.py`, `scripts/load_dataset.py`

### Dependencies
- No new Python packages (uses existing SQLAlchemy and psycopg2)

### Database
- Uses existing tables: `experiments`, `result_metrics`, `routes`, `node_distances`
- No schema changes required

### Backward Compatibility
- **Fully backward compatible**: Solvers can still run without database (CSV-only mode)
- Database integration is opt-in via `--dataset` argument
- Existing workflow unchanged if no database specified

### Performance
- **First run**: Slight overhead for database inserts (~100-200ms)
- **Subsequent runs**: Significant speedup from distance caching (avoids recomputing distance matrix)
- Expected 50-80% reduction in data loading time for cached datasets
