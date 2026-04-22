# Proposal: Refactor MDVRP Library Integration

## Overview

Refactor MDVRP (Multi-Depot Vehicle Routing Problem) implementation to align with thesis claims regarding library usage. The current codebase was developed as a proof-of-concept using manual implementations and hardcoded data. This refactoring will integrate the libraries claimed in the thesis: DEAP, NumPy, Pandas, SciPy, and tqdm.

## Background

The current implementation:
- Uses custom genetic algorithm implementation (not DEAP)
- Stores data in nested dictionaries (not NumPy arrays)
- Hardcodes problem data in Python files (not Pandas DataFrames)
- Calculates distances with manual loops (not SciPy)
- Uses print statements for progress (not tqdm)
- Works correctly but doesn't match thesis documentation

This creates a discrepancy between what the thesis claims and what the code actually does, which could be problematic for thesis defense and academic integrity.

## Goals

### Primary Goals
1. **Integrate DEAP** - Replace custom GA loop with DEAP framework for HGA solver
2. **Adopt NumPy** - Convert distance matrices to NumPy arrays for efficient computation
3. **Implement Pandas** - Add CSV/XLSX data loading and DataFrame-based data management
4. **Utilize SciPy** - Use `scipy.spatial.distance.cdist()` for distance matrix calculation
5. **Add tqdm** - Implement progress bars for all iterative processes

### Secondary Goals
1. **Unified API** - Standardize solve() interface across all solvers
2. **Time Limits** - Add timeout support for all solvers (for web frontend compatibility)
3. **Export Formats** - Support CSV, PDF, and GeoJSON output
4. **Backward Compatibility** - Ensure existing `run_small_*.py` scripts continue working

## Scope

### In Scope
- **HGA Solver** (`mdvrp_hga.py`)
  - Complete refactor to use DEAP framework
  - NumPy-based fitness calculations
  - Pandas I/O integration
  - tqdm progress tracking

- **Greedy Solver** (`mdvrp_greedy.py`)
  - NumPy distance calculations
  - Pandas I/O integration
  - tqdm progress tracking

- **MILP Solver** (`milp.py`)
  - Pandas I/O integration only
  - tqdm progress tracking
  - Gurobi implementation unchanged (already correct)

- **New Modules**
  - `data_loader.py` - CSV/XLSX/dict data loading with Pandas
  - `distance_matrix.py` - SciPy/NumPy matrix computation (shared preprocessing)
  - `exporter.py` - CSV/PDF/GeoJSON export functionality
  - `utils.py` - Helper functions (time unit conversions, etc.)

### Out of Scope
- Gurobi MILP algorithm (already implemented correctly)
- Web frontend implementation (future work)
- Algorithm logic changes (only library integration)
- New MDVRP variants or constraints

## Success Criteria

1. **Thesis Alignment**
   - All claimed libraries are actually used in code
   - Usage matches thesis descriptions
   - Code can be presented during thesis defense

2. **Functional Correctness**
   - All three solvers produce valid solutions
   - Results match or improve upon current implementation
   - `run_small_*.py` scripts work without modification

3. **API Consistency**
   - All solvers share unified `solve()` signature
   - Support `time_limit` parameter (in seconds)
   - Support `progress_callback` for web UI integration

4. **Data Format Support**
   - Load data from CSV files
   - Load data from XLSX files
   - Support dict-based input (backward compatibility)

5. **Output Formats**
   - Export results to CSV
   - Export reports to PDF
   - Export routes to GeoJSON

## Implementation Strategy

### Recommended Approach: Phased Implementation

**Phase 1: Foundation**
- Create `data_loader.py` with Pandas
- Create `distance_matrix.py` with SciPy/NumPy
- Create `utils.py` with helper functions
- Create sample CSV data files

**Phase 2: Output Layer**
- Create `exporter.py` (CSV/PDF/GeoJSON)
- Test all export formats

**Phase 3: Greedy Refactor**
- Integrate NumPy distance matrix usage
- Add Pandas I/O
- Add tqdm progress bars
- Add time_limit support

**Phase 4: HGA Refactor**
- Integrate DEAP framework
- Convert to NumPy arrays
- Add Pandas I/O
- Add tqdm progress bars
- Add time_limit support

**Phase 5: MILP Integration**
- Add Pandas I/O only
- Add tqdm progress

**Phase 6: Integration & Testing**
- Verify all solvers work with new data flow
- Test backward compatibility
- Performance benchmarking
- Documentation updates

## Timeline Estimate

- **Phase 1**: 2-3 hours
- **Phase 2**: 2-3 hours
- **Phase 3**: 3-4 hours
- **Phase 4**: 6-8 hours (most complex)
- **Phase 5**: 1-2 hours
- **Phase 6**: 2-3 hours

**Total**: 16-23 hours of development time

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| DEAP learning curve | Medium | Study DEAP documentation; start with simple example |
| Breaking existing scripts | High | Maintain constructor signatures; test run_small_*.py frequently |
| Performance regression | Low | NumPy/SciPy should improve performance; benchmark before/after |
| PDF/GeoJSON complexity | Medium | Use established libraries (reportlab, geojson); start simple |
| Scope creep | Medium | Stick to library integration only; no algorithm changes |

## Dependencies

### Python Packages (new)
- `deap>=1.4.1`
- `pandas>=2.0.0`
- `scipy>=1.11.0`
- `tqdm>=4.66.0`
- `openpyxl>=3.1.0`
- `reportlab>=4.0.0`
- `geojson>=3.1.0`
- `matplotlib>=3.8.0`

### Already Installed
- `numpy>=2.4.4` ✓
- `gurobipy>=12.0.3` ✓

## Related Changes

None - this is a new change proposal.

## Open Questions

1. **Sample Data**: Should we create example CSV files from `mdvrp_small.py` data, or wait for web frontend format?
2. **Testing**: Create unit tests or rely on manual testing with `run_small_*.py`?
3. **Quality Level**: Production-ready with full error handling, or thesis-functional (works but rough edges)?

## Approval Criteria

- [ ] Proposal reviewed and accepted
- [ ] Design document approved
- [ ] Task breakdown accepted
- [ ] Implementation phases agreed upon
- [ ] Ready to proceed with Phase 1
