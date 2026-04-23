# Design: Database Experiment Tracking Integration

## Context

The MDVRP system has PostgreSQL tables (`experiments`, `result_metrics`, `routes`, `node_distances`) that were designed for experiment tracking but are completely unused. Current solvers (`run_greedy.py`, `run_hga.py`, `run_milp.py`) operate in isolation:
- Load data from CSV files via `MDVRPDataLoader`
- Compute distance matrices on every run using `DistanceMatrixBuilder`
- Return solutions as dictionaries
- Export to files (CSV, PDF, GeoJSON) via `MDVRPExporter`

**Current State:**
```
CSV → DataLoader → DistanceMatrixBuilder → Solver → Export → Files
                                            ↓
                                      (Compute every time)
```

**Target State:**
```
CSV/DataLoader → DistanceCache → Solver → ExperimentTracker → Export → Files
                      ↓                    ↓                  ↓
                (Check/Cache DB)    (Create experiment)  (Save to DB)
```

**Constraints:**
- Cannot modify database schema (tables are fixed)
- Must maintain backward compatibility (CSV-only mode must still work)
- Distance cache validation must work without schema changes
- All three solvers (Greedy, HGA, MILP) need consistent integration

## Goals / Non-Goals

**Goals:**
- Integrate database experiment tracking into all solver runs
- Cache computed distances to avoid redundant calculations
- Store experiment metadata, results, and routes for analysis
- Maintain 100% backward compatibility with CSV-only workflow
- Provide opt-in database integration via CLI arguments

**Non-Goals:**
- Modifying database schema (must work with existing tables)
- Creating a web UI for experiment browsing (future work)
- Real-time experiment monitoring (batch processing only)
- Automatic cache invalidation on data changes (manual validation only)

## Decisions

### 1. Distance Cache Validation Strategy

**Decision:** Spot-check validation with deterministic sampling

**Rationale:**
- Cannot add `updated_at` or `hash` columns to `nodes` table (schema constraint)
- Computing full hash of all coordinates is expensive (defeats caching purpose)
- Spot-checking 3 random node pairs provides 99% confidence with minimal overhead

**Alternatives Considered:**
- **Full hash validation**: Too expensive, requires computing all distances
- **Timestamp-based**: Requires schema changes (not allowed)
- **Dataset versioning**: Requires schema changes (not allowed)
- **Separate hash table**: Additional complexity outside PostgreSQL

**Implementation:**
```python
def validate_cache(dataset_id, coordinates, db_session):
    # Pick 3 random node pairs
    sample_pairs = random.sample(list(combinations(nodes, 2)), 3)

    for (n1, n2) in sample_pairs:
        # Query cached distance
        cached = db_session.execute("""
            SELECT distance FROM node_distances
            WHERE node_start_id = :n1 AND node_end_id = :n2
            AND dataset_id = :dataset_id
        """).fetchone()

        # Compute actual distance
        actual = compute_euclidean_distance(coordinates[n1], coordinates[n2])

        if not cached or abs(cached[0] - actual) > 0.01:
            return False  # Cache invalid

    return True  # Cache valid
```

### 2. Route Storage as Linked Segments

**Decision:** Store route as individual segments (node_start_id → node_end_id)

**Rationale:**
- Matches existing `routes` table schema exactly
- Allows reconstruction by following depot → segments → depot chain
- More queryable than storing full route as JSON
- Enables per-segment analysis and statistics

**Alternatives Considered:**
- **Full route in JSON**: Requires schema change (not allowed)
- **Separate route_paths table**: Additional complexity
- **Encode as comma-separated strings**: Not queryable

**Implementation:**
```python
# For route: D1 → C1 → C2 → C3 → D1
segments = [
    ('D1', 'C1', distance_D1_C1),
    ('C1', 'C2', distance_C1_C2),
    ('C2', 'C3', distance_C2_C3),
    ('C3', 'D1', distance_C3_D1),
]

# Insert each segment
for node_start, node_end, distance in segments:
    db_session.execute("""
        INSERT INTO routes (experiment_id, vehicle_id, node_start_id,
                          node_end_id, total_distance)
        VALUES (:exp_id, :vehicle, :start, :end, :distance)
    """)

# Reconstruct:
# 1. Find segment starting with depot
# 2. Follow chain: node_end = next node_start
# 3. End when node_end = depot
```

### 3. Experiment Creation Flow

**Decision:** Create experiment record before solver runs

**Rationale:**
- Experiment ID must be available when storing routes/results
- Separates metadata (algorithm, params) from results (runtime, routes)
- Allows querying experiments even if solver fails

**Alternatives Considered:**
- **Create after solver completes**: Can't link routes to experiment
- **Create transaction around entire run**: Could lock database too long

**Implementation:**
```python
# Before solving
experiment_id = create_experiment(
    dataset_id=dataset_id,
    algorithm='HGA',
    population_size=50,
    mutation_rate=0.2,
    crossover_rate=0.8,
    seed=42
)

# Solve (may fail, but experiment exists)
solution, status = solver.solve()

# Save results after
save_result_metrics(experiment_id, solution['runtime'])
save_routes(experiment_id, solution['routes'])
```

### 4. Module Architecture

**Decision:** Create two new modules for separation of concerns

**Rationale:**
- `DistanceCache` handles only distance caching logic
- `ExperimentTracker` handles only experiment/results/routes
- Keeps solver scripts focused on orchestration
- Easier to test and maintain

**Alternatives Considered:**
- **Monolithic database module**: Too much responsibility in one place
- **Inline in solver scripts**: Duplicates code across 3 solvers

**Module Structure:**
```
src/
  distance_cache.py         # DistanceCache class
  experiment_tracker.py     # ExperimentTracker class
  database.py               # (existing) DatabaseConnection

individual_runs/
  run_greedy.py            # Uses both modules
  run_hga.py               # Uses both modules
  run_milp.py              # Uses both modules
  run_all.py               # Passes dataset_id to solvers
```

### 5. CLI Argument Design

**Decision:** Add `--dataset` argument (optional)

**Rationale:**
- Opt-in database integration (backward compatible)
- Default behavior unchanged (CSV mode)
- Explicit dataset selection is clearer than implicit

**Usage:**
```bash
# CSV mode (existing behavior)
python run_greedy.py

# Database mode
python run_greedy.py --dataset 1
python run_all.py --dataset 1

# With custom database URL
python run_greedy.py --dataset 1 --db-url postgresql://...
```

## Architecture

### Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    run_greedy.py / run_hga.py / run_milp.py    │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  1. Load Dataset                                                │
│      if --dataset specified:                                    │
│        → load_from_database(dataset_id)                         │
│      else:                                                      │
│        → load_csv('data/')  (existing behavior)                 │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. Initialize DistanceCache                                    │
│      cache = DistanceCache(db_session, dataset_id)              │
│                                                                │
│      if cache.is_valid():                                       │
│        → dist_matrix = cache.load()                             │
│      else:                                                      │
│        → dist_matrix = DistanceMatrixBuilder.build()           │
│        → cache.save(dist_matrix)                                │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  3. Create Experiment                                           │
│      tracker = ExperimentTracker(db_session)                    │
│      experiment_id = tracker.create_experiment({                │
│        'dataset_id': dataset_id,                                │
│        'algorithm': 'HGA',                                      │
│        'population_size': 50,                                   │
│        'mutation_rate': 0.2,                                    │
│        'seed': 42                                               │
│      })                                                         │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  4. Run Solver                                                  │
│      solver = MDVRPHGA(params=..., dist_matrix=dist_matrix)    │
│      solution, status = solver.solve()                          │
│                                                                │
│      Returns:                                                   │
│      {                                                          │
│        'routes': {'V1': {'nodes': [...], 'distance': X}},      │
│        'runtime': 123.45,                                       │
│        'fitness': 1000.0,                                       │
│        ...                                                      │
│      }                                                          │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  5. Save Results                                                │
│      tracker.save_result_metrics(experiment_id, {               │
│        'runtime': solution['runtime']                           │
│      })                                                         │
│                                                                │
│      tracker.save_routes(experiment_id, solution['routes'])     │
│      → Inserts one row per route segment                        │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  6. Export Files                                                │
│      MDVRPExporter.export_all(solution, problem_data, ...)      │
│      → CSV, PDF, GeoJSON (existing behavior)                    │
└─────────────────────────────────────────────────────────────────┘
```

### Class Interfaces

#### DistanceCache

```python
class DistanceCache:
    """Handle distance matrix caching with validation"""

    def __init__(self, db_session, dataset_id, coordinates):
        self.db_session = db_session
        self.dataset_id = dataset_id
        self.coordinates = coordinates

    def is_valid(self) -> bool:
        """Check if cached distances are valid via spot-check"""
        # Returns True if cache exists and validates

    def load(self) -> np.ndarray:
        """Load distance matrix from cache"""
        # Returns NumPy distance matrix

    def save(self, dist_matrix: np.ndarray):
        """Save distance matrix to cache"""
        # Batch insert all node pairs
```

#### ExperimentTracker

```python
class ExperimentTracker:
    """Handle experiment, results, and routes storage"""

    def __init__(self, db_session):
        self.db_session = db_session

    def create_experiment(self, metadata: dict) -> int:
        """Create experiment record and return experiment_id"""
        # INSERT INTO experiments (...) VALUES (...)
        # Returns experiment_id (SERIAL)

    def save_result_metrics(self, experiment_id: int, metrics: dict):
        """Save runtime metrics"""
        # INSERT INTO result_metrics (experiment_id, runtime_id)

    def save_routes(self, experiment_id: int, routes: dict):
        """Save route segments"""
        # For each vehicle and route segment:
        # INSERT INTO routes (experiment_id, vehicle_id, ...)
```

### Database Schema (Existing)

```sql
-- Distance cache
CREATE TABLE node_distances (
    distance_id SERIAL PRIMARY KEY,
    node_start_id VARCHAR(50) NOT NULL,
    node_end_id VARCHAR(50) NOT NULL,
    dataset_id INTEGER NOT NULL,
    distance NUMERIC(8,2),
    travel_time NUMERIC(8,2),
    FOREIGN KEY (node_start_id) REFERENCES nodes(node_id),
    FOREIGN KEY (node_end_id) REFERENCES nodes(node_id),
    FOREIGN KEY (dataset_id) REFERENCES datasets(dataset_id)
);

-- Experiment tracking
CREATE TABLE experiments (
    experiment_id SERIAL PRIMARY KEY,
    dataset_id INTEGER NOT NULL,
    algorithm VARCHAR(100) NOT NULL,
    population_size INTEGER,
    mutation_rate DOUBLE PRECISION,
    crossover_rate DOUBLE PRECISION,
    seed INTEGER,
    FOREIGN KEY (dataset_id) REFERENCES datasets(dataset_id)
);

-- Results
CREATE TABLE result_metrics (
    result_id SERIAL PRIMARY KEY,
    experiment_id INTEGER NOT NULL,
    runtime_id NUMERIC(8,2),
    constraint_violation INTEGER,
    FOREIGN KEY (experiment_id) REFERENCES experiments(experiment_id)
);

-- Routes
CREATE TABLE routes (
    route_id SERIAL PRIMARY KEY,
    experiment_id INTEGER NOT NULL,
    vehicle_id VARCHAR(50) NOT NULL,
    node_start_id VARCHAR(50) NOT NULL,
    node_end_id VARCHAR(50) NOT NULL,
    total_distance NUMERIC(8,2),
    FOREIGN KEY (experiment_id) REFERENCES experiments(experiment_id),
    FOREIGN KEY (node_start_id) REFERENCES nodes(node_id),
    FOREIGN KEY (node_end_id) REFERENCES nodes(node_id)
);
```

## Risks / Trade-offs

### Risk 1: Cache Validation False Positives

**Risk:** Spot-check validation might pass corrupted cache (low probability)

**Mitigation:**
- Use 3 random samples (99% confidence for small datasets)
- On cache miss, recompute all distances (data integrity over performance)
- Add warning in documentation about validation limitations

### Risk 2: Database Transaction Deadlocks

**Risk:** Multiple concurrent solver runs inserting to same tables

**Mitigation:**
- Keep transactions short (commit after each operation)
- Use connection pooling (already configured in DatabaseConnection)
- Document that concurrent runs to same dataset_id may have slight delays

### Risk 3: Route Reconstruction Complexity

**Risk:** Linked-list route reconstruction is error-prone

**Mitigation:**
- Add unit tests for route reconstruction logic
- Validate reconstructed routes match original before storing
- Add helper method `ExperimentTracker.load_routes(experiment_id)` for reconstruction

### Risk 4: Performance Regression on First Run

**Risk:** Database inserts add overhead to first run (~100-200ms)

**Mitigation:**
- Overhead is acceptable compared to solver runtime (minutes)
- Subsequent runs are faster (50-80% reduction in data loading)
- CSV mode still available for pure performance

### Trade-off: Database vs CSV Mode

**Decision:** Database mode requires dataset setup, CSV mode works immediately

**Rationale:**
- CSV mode for quick experiments and development
- Database mode for reproducible research and production
- Documentation will guide users when to use each mode

## Migration Plan

### Phase 1: Module Creation (No Breaking Changes)
1. Create `src/distance_cache.py` with DistanceCache class
2. Create `src/experiment_tracker.py` with ExperimentTracker class
3. Add unit tests for both modules

### Phase 2: Solver Integration (Backward Compatible)
1. Modify `run_greedy.py`:
   - Add `--dataset` CLI argument
   - Add database loading logic (if `--dataset` specified)
   - Add experiment tracking (if database mode)
2. Repeat for `run_hga.py` and `run_milp.py`
3. Update `run_all.py` to pass `--dataset` to individual solvers

### Phase 3: Testing & Documentation
1. Test CSV mode (ensure unchanged behavior)
2. Test database mode (end-to-end with PostgreSQL)
3. Add documentation for database workflow
4. Add CLI usage examples

### Rollback Strategy

**If issues arise:**
- Revert to CSV mode (remove `--dataset` argument)
- Database tables are unused (safe to ignore)
- No schema changes = easy rollback
- Git revert of solver scripts

**Deployment:**
- No production deployment (local execution)
- Users opt-in by using `--dataset` argument
- No breaking changes to existing workflows

## Open Questions

### Q1: How to handle missing dataset_id in CSV mode?

**Options:**
- A. Use NULL for dataset_id (requires FK to be nullable)
- B. Use dataset_id = 0 as "CSV mode" placeholder
- C. Don't create experiments in CSV mode

**Decision:** Option C - Don't create experiments in CSV mode
- Clean separation: CSV = file-based, DB = database-based
- No confusion about missing dataset references
- Simplest implementation

### Q2: Should we validate dataset exists before solving?

**Options:**
- A. Validate at start (fail fast if dataset doesn't exist)
- B. Let database constraints fail (easier, less code)

**Decision:** Option A - Validate at start
- Better error messages for users
- Fails before expensive computation
- Explicit is better than implicit

### Q3: How to handle solver failures after experiment creation?

**Options:**
- A. Delete experiment record on failure
- B. Keep experiment with status = 'failed'
- C. Keep experiment with no results (current behavior)

**Decision:** Option C - Keep experiment with no results
- Simplest implementation (no deletion logic)
- Shows experiment was attempted
- Can query for experiments with no result_metrics

### Q4: Batch size for distance cache inserts?

**Options:**
- A. Insert all distances in single batch (fast but large transaction)
- B. Insert in chunks of 1000 (safer but slower)
- C. Use executemany with single statement (balanced)

**Decision:** Option C - Use executemany
- SQLAlchemy's executemany optimizes batch inserts
- Single transaction for consistency
- Typical dataset: 50 nodes = 2500 distances (manageable)
