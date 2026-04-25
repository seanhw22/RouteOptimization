## Context

The MDVRP solver project has three algorithm implementations (`MDVRPGreedy`, `MDVRPHGA`, `MDVRP`) plus a near-duplicate debug file. All four share an identical 30-line data-loading block in `__init__`, and two carry `solve_legacy()` methods with no callers. The `src/` layer (`data_loader`, `distance_matrix`, `distance_cache`, `experiment_tracker`) is well-factored; the problem is confined to `algorithms/` and the root-level docs.

The existing `src/` module is the natural home for shared algorithm utilities. No database, API, or external dependency changes are involved.

## Goals / Non-Goals

**Goals:**
- Eliminate `mdvrp_greedy_debug.py` entirely
- Extract the duplicated data-loading init block into a single function in `src/solver_base.py`
- Remove `solve_legacy()` from both solvers that carry it
- Consolidate duplicated route-distance loop into a shared helper
- Delete two obsolete doc files, absorb useful fragments, fix README accuracy

**Non-Goals:**
- Introducing inheritance / base class — a function is sufficient and avoids DEAP `creator` conflicts in HGA
- Changing solver public interfaces (`solve()`, constructor signatures)
- Altering algorithm logic or parameters
- Adding tests (existing test suite is the regression check)

## Decisions

### Decision 1: Function over base class for shared init

**Choice:** A standalone function `load_solver_data(data_source, depots, customers, vehicles, items, params)` in `src/solver_base.py`, returning `(depots, customers, vehicles, items, params)`.

**Why not a `BaseSolver` class?** HGA uses DEAP's `creator.create()` at import time, which conflicts with multiple-inheritance patterns and makes a shared `__init__` harder to reason about. A plain function keeps each solver's `__init__` explicit and avoids metaclass complexity. Three similar calls to the same function are far less risky than a class hierarchy the solvers weren't designed for.

**Alternatives considered:**
- `BaseSolver.__init__` — rejected (DEAP conflict, forces restructure of HGA's `Individual` class)
- Mixin class — rejected (same risks, more complexity for no gain)

### Decision 2: Route-distance helper as a module-level function

**Choice:** `calculate_route_distance(route, depot, dist, node_to_idx, uses_numpy)` as a free function in `src/solver_base.py`.

The Greedy version (`calculate_route_distance(self, vehicle)`) reads state from `self`; the HGA version (`_calculate_route_distance(self, vehicle, route)`) takes `route` as an argument. The HGA signature is more reusable. The function will accept the route list plus the lookup data it needs, keeping it stateless.

Both solver methods become thin wrappers that pass their own state in.

### Decision 3: Doc consolidation strategy

**Choice:** Delete `MIGRATION.md` and `IMPLEMENTATION_SUMMARY.md` outright. Fold DATABASE_USAGE.md's unique content (SQL query examples, troubleshooting table) into `DATABASE_SETUP.md`, then delete `DATABASE_USAGE.md`. Fix `README.md` in place.

**Why not merge everything into README?** README is already 443 lines. The setup/troubleshooting material belongs in `DATABASE_SETUP.md` which is scoped to that concern. README stays as the entry point; DATABASE_SETUP.md stays as the deep-dive.

### Decision 4: What to rescue from deleted files

- `MIGRATION.md` → one paragraph on "reverting to CSV mode" → added to `README.md` under a "Reverting to CSV Mode" subsection
- `DATABASE_USAGE.md` → SQL query examples and troubleshooting table → added to `DATABASE_SETUP.md`
- `IMPLEMENTATION_SUMMARY.md` → nothing; pure historical artifact, content is in git history

## Risks / Trade-offs

- **Greedy callers of `calculate_route_distance`** — Greedy calls this method internally in several places. The wrapper approach means the public method signature is unchanged, so no risk of external breakage. Internal calls just delegate to the helper.
- **`mdvrp_greedy_debug.py` deletion** — If any script imports from it, that script will break. Verified: no imports exist anywhere (`grep` confirms zero references). Safe to delete.
- **`solve_legacy()` removal** — Same check: zero callers in `algorithms/`, `scripts/`, `individual_runs/`, or `scripts/tests/`. Safe to remove.
- **Doc deletions** — `IMPLEMENTATION_SUMMARY.md` and `MIGRATION.md` are not linked from any code or other docs. `DATABASE_USAGE.md` is linked once from `README.md` ("See DATABASE_USAGE.md"); that link will be updated to point to `DATABASE_SETUP.md`.

## Migration Plan

No runtime migration needed — this is a purely internal refactor with no API surface changes and no database schema changes.

Order of operations during implementation:
1. Create `src/solver_base.py` with `load_solver_data()` and `calculate_route_distance()`
2. Update `milp.py` (simplest, no route-distance changes needed)
3. Update `mdvrp_greedy.py` (route-distance wrapper + load_solver_data)
4. Update `mdvrp_hga.py` (route-distance wrapper + load_solver_data + remove solve_legacy)
5. Delete `mdvrp_greedy_debug.py`
6. Fix docs (README, DATABASE_SETUP, deletions)

Rollback: `git revert` — no migration artifacts to clean up.
