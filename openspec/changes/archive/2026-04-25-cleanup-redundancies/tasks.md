## 1. Create Shared Solver Utilities

- [x] 1.1 Create `src/solver_base.py` with `load_solver_data(data_source, depots, customers, vehicles, items, params)` function
- [x] 1.2 Add `calculate_route_distance(route, depot, dist, node_to_idx=None, uses_numpy=False)` to `src/solver_base.py`
- [x] 1.3 Export both functions from `src/__init__.py`

## 2. Refactor `algorithms/milp.py`

- [x] 2.1 Replace the inline data-loading block in `__init__` with a call to `load_solver_data()`

## 3. Refactor `algorithms/mdvrp_greedy.py`

- [x] 3.1 Replace the inline data-loading block in `__init__` with a call to `load_solver_data()`
- [x] 3.2 Update `calculate_route_distance(self, vehicle)` to delegate to `solver_base.calculate_route_distance()`
- [x] 3.3 Remove `solve_legacy()` method

## 4. Refactor `algorithms/mdvrp_hga.py`

- [x] 4.1 Replace the inline data-loading block in `__init__` with a call to `load_solver_data()`
- [x] 4.2 Update `_calculate_route_distance(self, vehicle, route)` to delegate to `solver_base.calculate_route_distance()`
- [x] 4.3 Remove `solve_legacy()` method

## 5. Delete Dead Files

- [x] 5.1 Delete `algorithms/mdvrp_greedy_debug.py`

## 6. Fix Documentation

- [x] 6.1 Delete `IMPLEMENTATION_SUMMARY.md`
- [x] 6.2 Delete `MIGRATION.md`
- [x] 6.3 Delete `DATABASE_USAGE.md`
- [x] 6.4 Add SQL query examples and troubleshooting content from `DATABASE_USAGE.md` into `DATABASE_SETUP.md` before deleting it
- [x] 6.5 Fix `README.md` import paths (`from mdvrp_greedy import X` → `from algorithms.mdvrp_greedy import X`)
- [x] 6.6 Remove all references to `small/` directory from `README.md`
- [x] 6.7 Remove all references to `data/` directory structure from `README.md`
- [x] 6.8 Update project structure diagram in `README.md` to reflect actual layout (`algorithms/`, `src/` with all files)
- [x] 6.9 Fix duplicate "Option 3" section numbering in `README.md`
- [x] 6.10 Update `README.md` link from `DATABASE_USAGE.md` to `DATABASE_SETUP.md`
- [x] 6.11 Add "Reverting to CSV Mode" subsection to `README.md` (salvaged from `MIGRATION.md`)

## 7. Verify

- [x] 7.1 Confirm no remaining imports of `mdvrp_greedy_debug` anywhere in the codebase
- [x] 7.2 Confirm no remaining calls to `solve_legacy()` anywhere in the codebase
- [x] 7.3 Run `individual_runs/run_greedy.py` and confirm it executes without error
- [x] 7.4 Run `individual_runs/run_hga.py` and confirm it executes without error
- [x] 7.5 Run `individual_runs/run_milp.py` and confirm it executes without error
