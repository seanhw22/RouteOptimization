## Why

The codebase has accumulated ~35–40% redundancy: a near-duplicate solver file, copy-pasted initialisation logic across all four solvers, dead legacy methods, and five documentation files — two of which are fully obsolete and one with broken examples. This cleanup removes the dead weight before further feature work compounds the mess.

## What Changes

- **Delete** `algorithms/mdvrp_greedy_debug.py` — 818-line near-duplicate of `mdvrp_greedy.py`, same class name, no unique logic worth keeping
- **Extract** shared data-loading init block into `src/solver_base.py` — 30-line block copy-pasted verbatim in all four solvers (`mdvrp_greedy`, `mdvrp_greedy_debug`, `mdvrp_hga`, `milp`); extracted as a standalone function `load_solver_data()`
- **Remove** `solve_legacy()` from `mdvrp_greedy.py` and `mdvrp_hga.py` — verbose Indonesian-language debug output, zero callers anywhere in the codebase
- **Remove** duplicated `calculate_route_distance` logic — same loop body implemented independently in Greedy and HGA; consolidate into a shared helper in `src/solver_base.py`
- **Delete** `IMPLEMENTATION_SUMMARY.md` — historical sprint completion report referencing nonexistent files (`data/`, `small/`, test scripts)
- **Delete** `MIGRATION.md` — documents a migration that already happened; the one useful paragraph (rollback to CSV mode) absorbed into `README.md`
- **Fix** `README.md` — wrong import paths, references to nonexistent `small/` and `data/` directories, outdated project structure diagram, missing `src/` files, duplicate "Option 3" numbering
- **Delete** `DATABASE_USAGE.md` — 358 lines overlapping heavily with `README.md` and `DATABASE_SETUP.md`; unique content (troubleshooting, query examples) folded into `DATABASE_SETUP.md`

## Capabilities

### New Capabilities

- `solver-base`: Shared solver initialisation utility (`load_solver_data()`) and route distance helper used by all algorithm implementations

### Modified Capabilities

- `route-display`: `calculate_route_distance` signature consolidated — existing callers updated to use the shared helper

## Impact

- `algorithms/mdvrp_greedy.py` — removes `solve_legacy()`, adopts `load_solver_data()` and shared route-distance helper
- `algorithms/mdvrp_hga.py` — removes `solve_legacy()`, adopts `load_solver_data()` and shared route-distance helper
- `algorithms/milp.py` — adopts `load_solver_data()`
- `algorithms/mdvrp_greedy_debug.py` — deleted entirely
- `src/solver_base.py` — new file
- `README.md`, `DATABASE_SETUP.md` — updated in place
- `IMPLEMENTATION_SUMMARY.md`, `MIGRATION.md`, `DATABASE_USAGE.md` — deleted
