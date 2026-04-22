# Fix MDVRP HGA and Greedy Bugs

## Why

The Hybrid Genetic Algorithm (HGA) and Greedy implementations contain critical bugs that prevent them from producing correct results. HGA produces identical output to MILP due to disabled genetic operators and missing elitism, while Greedy incorrectly reports route time as 0.0 hours instead of the actual travel time. These bugs undermine the core functionality of both algorithms and make them unusable for research or practical applications.

## What Changes

This change fixes 7 critical bugs across both algorithms:

### HGA (mdvrp_hga.py)
- **Fix disabled crossover**: Order crossover is completely disabled, returning copies of parents instead of creating offspring. This eliminates genetic diversity.
- **Implement elitism**: Evolution loop replaces entire population each generation, losing best solutions. Need to preserve top N elites.
- **Fix local search frequency**: Local search (2-opt) only runs 30% of the time due to random check. Should run 100% of the time as required.
- **Add relocation operator**: Relocation local search is not implemented. Only 2-opt exists.
- **Export route time**: Time is calculated correctly but not exported in solution dict.

### Greedy (mdvrp_greedy.py)
- **Fix time calculation order**: Customer is inserted into route BEFORE time increase is calculated, resulting in 0.0 delta. Time never accumulates.
- **Reorder operations**: Calculate time increase first, then insert customer, then update route_time.

### Exporter (src/exporter.py)
- **Include depot in route display**: Route strings show only customers (e.g., "C3 -> C5") but should include depot at start and end (e.g., "D1 -> C3 -> C5 -> D1").

## Capabilities

### New Capabilities
- `hga-crossover`: Order crossover operator for MDVRP that respects depot boundaries in chromosome representation
- `hga-elitism`: Elite individual preservation across generations in HGA evolution loop
- `hga-relocation`: Relocation local search operator for moving customers between positions and routes

### Modified Capabilities
- `hga-local-search`: Change local search from probabilistic (30% chance) to deterministic (always run)
- `hga-time-export`: Add route time to exported solution dictionary for HGA
- `greedy-time-tracking`: Fix time calculation order to properly accumulate travel time in Greedy
- `route-display`: Modify route string formatting to include depot at origin and destination

## Impact

**Affected Files:**
- `mdvrp_hga.py` (~5 changes: crossover, elitism, local search, relocation, time export)
- `mdvrp_greedy.py` (1 change: time calculation order)
- `src/exporter.py` (1 change: route display format)

**Behavioral Changes:**
- HGA will produce different, more diverse solutions each run (current behavior: always produces MILP solution)
- Greedy will report correct route times instead of 0.0
- Route displays will show complete paths including depot

**No Breaking Changes:**
- All fixes maintain existing API contracts
- Solution dictionary structure gains optional 'time' field (backward compatible)
- Route display format change is additive (adds depot info)

**Performance Impact:**
- HGA: Local search now runs every mutation (was 30%) → slightly slower per generation, but better convergence
- Greedy: Negligible (just reordering operations)
