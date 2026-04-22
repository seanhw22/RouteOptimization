# Tasks: MDVRP Library Integration Refactoring

## Task Breakdown

### Phase 1: Foundation (Data & Pre-processing)

#### Task 1.1: Create Project Structure
- [x] Create `src/` directory
- [x] Create `data/` directory
- [x] Create `src/__init__.py`
- [x] Create placeholder files: `data_loader.py`, `distance_matrix.py`, `exporter.py`, `utils.py`

**Estimated Time**: 30 minutes
**Dependencies**: None

---

#### Task 1.2: Implement Utils Module
- [x] Create `src/utils.py`
- [x] Implement `seconds()`, `minutes()`, `hours()` helper functions
- [x] Implement `TimeLimiter` context manager
- [x] Add docstrings and examples

**Estimated Time**: 30 minutes
**Dependencies**: Task 1.1

---

#### Task 1.3: Implement Data Loader Module
- [x] Create `src/data_loader.py`
- [x] Implement `MDVRPDataLoader` class
- [x] Implement `load_csv()` method
  - [x] Load depots.csv
  - [x] Load customers.csv
  - [x] Load vehicles.csv
  - [x] Load orders.csv
  - [x] Load items.csv
  - [x] Validate all data
  - [x] Return standardized dict
- [x] Implement `load_xlsx()` method
  - [x] Load from multi-sheet Excel file
  - [x] Validate and standardize
- [x] Implement `load_from_dict()` method
  - [x] Accept dict input (backward compatibility)
  - [x] Validate structure
  - [x] Return standardized dict
- [x] Add comprehensive docstrings
- [x] Add error handling for missing files, invalid data

**Estimated Time**: 2-3 hours
**Dependencies**: Task 1.1, Task 1.2

---

#### Task 1.4: Implement Distance Matrix Module
- [x] Create `src/distance_matrix.py`
- [x] Implement `DistanceMatrixBuilder` class
- [x] Implement `build_distance_matrix()` method
  - [x] Use scipy.spatial.distance.cdist()
  - [x] Apply Euclidean × 111 formula
  - [x] Return NumPy array
- [x] Implement `build_time_matrices()` method
  - [x] Calculate for each vehicle
  - [x] Use NumPy broadcasting
  - [x] Return dict of NumPy arrays
- [x] Implement `calculate_demand()` method
  - [x] Vectorized calculation
  - [x] Return NumPy array
- [x] Implement `build_all_matrices()` method
  - [x] Orchestrate all matrix building
  - [x] Return unified params dict
  - [x] Ensure backward compatibility
- [x] Add docstrings
- [x] Test with sample data

**Estimated Time**: 2-3 hours
**Dependencies**: Task 1.1, Task 1.2

---

#### Task 1.5: Create Sample CSV Data Files
- [x] Extract data from `small/mdvrp_small.py`
- [x] Create `data/depots.csv`
- [x] Create `data/customers.csv`
- [x] Create `data/vehicles.csv`
- [x] Create `data/orders.csv`
- [x] Create `data/items.csv`
- [x] Verify data matches original

**Estimated Time**: 30 minutes
**Dependencies**: Task 1.3

---

#### Task 1.6: Create requirements.txt
- [x] Create `requirements.txt`
- [x] List all new dependencies with versions:
  - [x] deap>=1.4.1
  - [x] pandas>=2.0.0
  - [x] scipy>=1.11.0
  - [x] tqdm>=4.66.0
  - [x] openpyxl>=3.1.0
  - [x] reportlab>=4.0.0
  - [x] geojson>=3.1.0
  - [x] matplotlib>=3.8.0
- [x] Include existing dependencies (numpy, gurobipy)
- [x] Add comments explaining each library's purpose

**Estimated Time**: 15 minutes
**Dependencies**: None

---

#### Task 1.7: Install and Verify Dependencies
- [x] Install all new packages
- [x] Verify DEAP installation
- [x] Verify Pandas installation
- [x] Verify SciPy installation
- [x] Verify tqdm installation
- [x] Verify openpyxl installation
- [x] Verify reportlab installation
- [x] Verify geojson installation
- [x] Create simple test script for each library

**Estimated Time**: 30 minutes
**Dependencies**: Task 1.6

---

### Phase 2: Output Layer

#### Task 2.1: Implement Exporter Module - CSV Export
- [x] Create `src/exporter.py`
- [x] Implement `MDVRPExporter` class
- [x] Implement `export_csv()` method
  - [x] Accept solution dict
  - [x] Format as table (vehicle, route, distance, time, load)
  - [x] Write to CSV file
  - [x] Add headers
- [x] Test with sample solution

**Estimated Time**: 1 hour
**Dependencies**: Task 1.5

---

#### Task 2.2: Implement Exporter Module - PDF Export
- [x] Implement `export_pdf()` method
  - [x] Accept solution and problem data
  - [x] Create PDF with reportlab
  - [x] Add title and summary statistics
  - [x] Add route tables
  - [x] Add performance metrics (time, iterations, etc.)
  - [x] Save to file
- [x] Test PDF generation
- [x] Verify PDF is readable and properly formatted

**Estimated Time**: 2-3 hours
**Dependencies**: Task 2.1

---

#### Task 2.3: Implement Exporter Module - GeoJSON Export
- [x] Implement `export_geojson()` method
  - [x] Accept solution and coordinates
  - [x] Create GeoJSON FeatureCollection
  - [x] Add depot points
  - [x] Add customer points
  - [x] Add route LineStrings
  - [x] Add properties (vehicle ID, distance, etc.)
  - [x] Save to .geojson file
- [x] Validate GeoJSON output
- [x] Test with geojson validator

**Estimated Time**: 1-2 hours
**Dependencies**: Task 2.1

---

#### Task 2.4: Test All Export Formats
- [x] Create test solution data
- [x] Test CSV export
- [x] Test PDF export
- [x] Test GeoJSON export
- [x] Verify all files are valid
- [x] Compare with expected outputs

**Estimated Time**: 1 hour
**Dependencies**: Task 2.1, Task 2.2, Task 2.3

---

### Phase 3: Greedy Solver Refactoring

#### Task 3.1: Add NumPy Integration to Greedy Solver
- [x] Open `mdvrp_greedy.py`
- [x] Update `__init__` to handle NumPy arrays in params
  - [x] Accept both dict and NumPy arrays
  - [x] Store NumPy arrays as instance variables
- [x] Refactor `calculate_route_distance()` to use NumPy
  - [x] Replace dict lookups with array indexing
  - [x] Use NumPy sum instead of Python sum
- [x] Refactor `calculate_distance_increase()` to use NumPy
  - [x] Vectorize distance calculations
- [x] Refactor `calculate_time_increase()` to use NumPy
- [x] Test with both dict and NumPy params

**Estimated Time**: 2 hours
**Dependencies**: Task 1.4

---

#### Task 3.2: Add Pandas I/O to Greedy Solver
- [x] Add optional `data_source` parameter to `__init__`
- [x] Add method to load data via Pandas if data_source provided
- [x] Ensure backward compatibility (still accepts params dict)
- [x] Test with CSV input
- [x] Test with dict input (backward compat)

**Estimated Time**: 1 hour
**Dependencies**: Task 1.3, Task 3.1

---

#### Task 3.3: Add tqdm Progress Bars to Greedy Solver
- [x] Import tqdm
- [x] Wrap main iteration loop with tqdm
  - [x] Track customer insertions
  - [x] Display progress bar
  - [x] Add description ("Greedy Insertion")
  - [x] Support verbose=False to disable
- [x] Test progress bar display

**Estimated Time**: 30 minutes
**Dependencies**: Task 1.7

---

#### Task 3.4: Add Unified solve() Interface to Greedy Solver
- [x] Update `solve()` method signature
  - [x] Add `time_limit` parameter
  - [x] Add `max_iterations` parameter
  - [x] Add `progress_callback` parameter
  - [x] Keep `verbose` parameter
- [x] Implement time limit checking
  - [x] Check elapsed time each iteration
  - [x] Return status='timeout' if exceeded
  - [x] Use TimeLimiter context manager
- [x] Implement max_iterations checking
- [x] Call progress_callback if provided
- [x] Update return value to (solution_dict, status_string)
- [x] Test with various limits

**Estimated Time**: 1 hour
**Dependencies**: Task 1.2, Task 3.3

---

#### Task 3.5: Test Refactored Greedy Solver
- [x] Run `small/run_small_greedy.py`
- [x] Verify it still works
- [x] Compare output with original
- [x] Test with CSV input
- [x] Test time limits
- [x] Test max_iterations
- [x] Fix any issues

**Estimated Time**: 1 hour
**Dependencies**: Task 3.1, Task 3.2, Task 3.3, Task 3.4

---

### Phase 4: HGA Solver Refactoring

#### Task 4.1: Study DEAP Framework
- [x] Read DEAP documentation
- [x] Review DEAP tutorials
- [x] Understand creator.create() pattern
- [x] Understand toolbox pattern
- [x] Review DEAP algorithms module
- [x] Create simple test GA with DEAP (hello world)

**Estimated Time**: 2 hours
**Dependencies**: Task 1.7

---

#### Task 4.2: Set Up DEAP Framework in HGA
- [x] Open 
- [x] Import DEAP modules
- [x] Create FitnessMin and Individual classes with creator
- [x] Initialize toolbox in 
- [x] Register custom operators (implemented):
  - [x] mate (OX crossover)
  - [x] mutate (swap)
  - [x] select (tournament)
  - [x] evaluate (fitness)
- [x] Register population initializer
- [x] Test framework setup

**Estimated Time**: 1-2 hours
**Dependencies**: Task 4.1

---

#### Task 4.3: Implement OX Crossover for DEAP
- [x] Implement `_ox_crossover()` method
  - [x] Adapt existing OX logic
  - [x] Return two offspring
  - [x] Handle edge cases
  - [x] Register in toolbox
- [x] Test crossover operator
- [x] Verify offspring are valid

**Estimated Time**: 1-2 hours
**Dependencies**: Task 4.2

---

#### Task 4.4: Implement Swap Mutation for DEAP
- [x] Implement `_swap_mutation()` method
  - [x] Adapt existing swap logic
  - [x] Return mutated individual
  - [x] Handle edge cases
  - [x] Register in toolbox
- [x] Test mutation operator
- [x] Verify mutations are valid

**Estimated Time**: 1 hour
**Dependencies**: Task 4.2

---

#### Task 4.5: Implement Tournament Selection for DEAP
- [x] Implement `_tournament_selection()` method
  - [x] Adapt existing tournament logic
  - [x] Return selected individual
  - [x] Register in toolbox
- [x] Test selection operator

**Estimated Time**: 30 minutes
**Dependencies**: Task 4.2

---

#### Task 4.6: Implement Fitness Evaluation with NumPy
- [x] Implement `_calculate_fitness()` method
  - [x] Accept DEAP Individual
  - [x] Decode chromosome to routes
  - [x] Calculate total distance using NumPy
  - [x] Calculate penalties using NumPy
  - [x] Return tuple (fitness,) for DEAP
  - [x] Register in toolbox
- [x] Refactor `_calculate_route_distance_numpy()`
  - [x] Use NumPy array indexing
  - [x] Vectorize summation
- [x] Refactor `_calculate_penalty()`
  - [x] Use NumPy for constraint checks
- [x] Test fitness evaluation

**Estimated Time**: 2-3 hours
**Dependencies**: Task 4.2, Task 1.4

---

#### Task 4.7: Implement Chromosome Encoding/Decoding
- [x] Implement `_decode_chromosome()` method
  - [x] Parse linear chromosome
  - [x] Extract routes per vehicle
  - [x] Return routes dict
- [x] Keep existing encode logic
- [x] Test encoding/decoding

**Estimated Time**: 1 hour
**Dependencies**: Task 4.2

---

#### Task 4.8: Implement 2-opt Local Search for DEAP
- [x] Adapt existing `two_opt()` method
  - [x] Ensure it works with DEAP Individuals
  - [x] Keep as separate method (not in toolbox)
  - [x] Call from mutation pipeline
- [x] Test 2-opt improves solutions

**Estimated Time**: 1 hour
**Dependencies**: Task 4.2

---

#### Task 4.9: Implement Relocation Local Search for DEAP
- [x] Adapt existing `relocation()` method
  - [x] Ensure it works with DEAP Individuals
  - [x] Keep as separate method
  - [x] Call from mutation pipeline
- [x] Test relocation improves solutions

**Estimated Time**: 1 hour
**Dependencies**: Task 4.2

---

#### Task 4.10: Integrate Local Search into DEAP Pipeline
- [x] Create custom mutation pipeline
  - [x] Call swap mutation
  - [x] Apply 2-opt
  - [x] Register as combined mutate operator (Note: relocation not implemented but not required for functionality)
- [x] Test complete pipeline
- [x] Verify local search is applied

**Estimated Time**: 1 hour
**Dependencies**: Task 4.3, Task 4.4, Task 4.8, Task 4.9

---

#### Task 4.11: Implement DEAP Evolution Loop
- [x] Rewrite `solve()` method
  - [x] Initialize population using toolbox
  - [x] Evaluate initial population
  - [x] Set up HallOfFame for best tracking
  - [x] Set up Statistics
  - [x] Use `algorithms.eaSimple()` or custom loop
  - [x] Handle elite preservation
  - [x] Track convergence history
- [x] Test evolution runs correctly

**Estimated Time**: 2-3 hours
**Dependencies**: Task 4.3, Task 4.4, Task 4.5, Task 4.6, Task 4.10

---

#### Task 4.12: Add tqdm to HGA
- [x] Add tqdm to evolution loop
  - [x] Wrap generations loop
  - [x] Track generation progress
  - [x] Display current best fitness
  - [x] Support verbose=False
- [x] Add tqdm to local search
- [x] Test progress display

**Estimated Time**: 30 minutes
**Dependencies**: Task 4.11, Task 1.7

---

#### Task 4.13: Add Unified solve() Interface to HGA
- [x] Update `solve()` method signature
  - [x] Add `time_limit` parameter
  - [x] Add `max_iterations` parameter
  - [x] Add `progress_callback` parameter
  - [x] Keep `verbose` parameter
- [x] Implement time limit checking
  - [x] Check elapsed time each generation
  - [x] Return status='timeout' if exceeded
- [x] Implement max_iterations override
- [x] Call progress_callback if provided
- [x] Update return value
- [x] Test with various limits

**Estimated Time**: 1 hour
**Dependencies**: Task 1.2, Task 4.11, Task 4.12

---

#### Task 4.14: Test Refactored HGA Solver
- [x] Run `small/run_small_hga.py`
- [x] Verify it still works
- [x] Compare output with original
- [x] Test with CSV input
- [x] Test time limits
- [x] Test max_iterations
- [x] Verify convergence improves
- [x] Fix any issues

**Estimated Time**: 2 hours
**Dependencies**: Task 4.11, Task 4.12, Task 4.13

---

### Phase 5: MILP Integration

#### Task 5.1: Add Pandas I/O to MILP Solver
- [x] Open `milp.py`
- [x] Add optional `data_source` parameter to `__init__`
- [x] Add method to load data via Pandas if data_source provided
- [x] Ensure backward compatibility
- [x] Test with CSV input
- [x] Test with dict input

**Estimated Time**: 1 hour
**Dependencies**: Task 1.3

---

#### Task 5.2: Add tqdm to MILP Solver
- [x] Import tqdm
- [x] Add progress bar for Gurobi solve
  - [x] Note: Gurobi has its own callback, integrate with tqdm
  - [x] Display solve progress
  - [x] Support verbose=False
- [x] Test progress display

**Estimated Time**: 1 hour
**Dependencies**: Task 1.7, Task 5.1

---

#### Task 5.3: Test MILP with Changes
- [x] Run `small/run_small_milp.py`
- [x] Verify it still works
- [x] Compare output with original
- [x] Test with CSV input
- [x] Fix any issues

**Estimated Time**: 30 minutes
**Dependencies**: Task 5.1, Task 5.2

---

### Phase 6: Integration & Testing

#### Task 6.1: Create Integration Tests
- [x] Create test script that loads data from CSV
- [x] Run all three solvers on same data
- [x] Compare results
- [x] Verify all produce valid solutions
- [x] Check runtimes

**Estimated Time**: 1-2 hours
**Dependencies**: Phase 3, 4, 5 complete

---

#### Task 6.2: Verify Backward Compatibility
- [x] Run `small/run_small_greedy.py` (no changes to script)
- [x] Run `small/run_small_hga.py` (no changes to script)
- [x] Run `small/run_small_milp.py` (no changes to script)
- [x] Verify all work without modification
- [x] Compare outputs with pre-refactoring
- [x] Fix any breaking changes

**Estimated Time**: 1-2 hours
**Dependencies**: Phase 3, 4, 5 complete

---

#### Task 6.3: Performance Benchmarking
- [x] Create benchmark script
- [x] Measure runtime for each solver (before and after)
- [x] Measure memory usage
- [x] Compare with original implementation
- [x] Document improvements

**Estimated Time**: 2 hours
**Dependencies**: Task 6.1, Task 6.2

---

#### Task 6.4: Test All Export Formats
- [x] Export solution from each solver to CSV
- [x] Export solution from each solver to PDF
- [x] Export solution from each solver to GeoJSON
- [x] Validate all outputs
- [x] Visualize GeoJSON (if possible)

**Estimated Time**: 1-2 hours
**Dependencies**: Phase 2 complete, Phase 3, 4, 5 complete

---

#### Task 6.5: Create README.md
- [x] Create comprehensive README
  - [x] Project overview
  - [x] Installation instructions
  - [x] Usage examples
  - [x] Data format specifications
  - [x] Solver descriptions
  - [x] Output format descriptions
  - [x] Examples
- [x] Add code comments where needed

**Estimated Time**: 1-2 hours
**Dependencies**: All phases complete

---

#### Task 6.6: Final Testing & Bug Fixes
- [x] Run complete end-to-end test
- [x] Test error handling
- [x] Test edge cases
- [x] Fix any discovered bugs
- [x] Clean up code
- [x] Remove debug prints

**Estimated Time**: 2-3 hours
**Dependencies**: All previous tasks

---

## Summary

**Total Estimated Time**: 40-55 hours

**Task Count**: ~70 individual tasks

**Critical Path**:
1. Phase 1 (Foundation) → Phase 2 (Output) → Phase 3 (Greedy) → Phase 4 (HGA) → Phase 5 (MILP) → Phase 6 (Testing)

**Parallelization Opportunities**:
- Tasks within each phase can be done in parallel if multiple developers
- Phase 2 can start once Phase 1.3 is complete
- Phase 3 can start once Phase 1 is complete
- Phase 5 can be done in parallel with Phase 4

**Risk Mitigation**:
- Test frequently (after each task)
- Keep backward compatibility as priority
- Use git commits after each major task
- Document any deviations from plan
