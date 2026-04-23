# Proposal: Database Integration for MDVRP System

## Overview

Add PostgreSQL database support to the MDVRP solver system. The database will store all data currently in CSV files, plus enable webapp features like user management, experiments, and result tracking. All solver algorithms remain **unchanged** - they just get data from a dict regardless of source (CSV or database).

## Motivation

### Current Limitations
- **File-based data storage**: No user management or session handling
- **No experiment persistence**: Cannot store or compare historical runs
- **Limited webapp support**: Multi-user scenarios impossible with CSV files
- **No data relationships**: Cannot track which datasets belong to which users/experiments

### Business Context
- **Deadline**: 2 weeks until thesis submission
- **Webapp Requirements**:
  - Multi-user support with authentication
  - Dataset management per user
  - Experiment history and comparison
  - Algorithm performance tracking

## Goals

### Primary Goals
1. ✅ Add `load_from_database()` method to data loader
2. ✅ Support both CSV and database data sources seamlessly
3. ✅ Maintain 100% backward compatibility with existing algorithms
4. ✅ Enable webapp features: users, sessions, experiments, results
5. ✅ Update database schema (add missing `deadline_hours` to customers)

### Non-Goals (Explicitly Out of Scope)
- ❌ Modifying algorithm logic (Greedy, HGA, MILP remain unchanged)
- ❌ Changing solver interfaces or return formats
- ❌ Implementing the webapp itself (separate project)
- ❌ Database migration tools (initial schema only)
- ❌ Advanced database features (triggers, stored procedures)

## What You Need to Do

### 1. Create Database Tables
Run [`database/schema.sql`](../database/schema.sql) in your PostgreSQL database:
```bash
psql -U your_user -d your_database -f database/schema.sql
```

### 2. Update CSV Column Names
Update files in `data/` directory:
- `depots.csv`: Rename `latitude,longitude` → `x,y`
- `customers.csv`: Rename `latitude,longitude` → `x,y`
- `vehicles.csv`: Rename `max_time_hours` → `max_operational_hrs`

### 3. Update Python Code
- Modify [`src/data_loader.py`](../../src/data_loader.py) to use new column names
- Add `load_from_database()` method
- Create [`src/database.py`](../../src/database.py) for connection management

### 4. Install Dependencies
```bash
pip install sqlalchemy psycopg2-binary
```

## Architecture

```
MDVRP Solvers (Unchanged)
    ↓
Data Abstraction Layer (src/data_loader.py)
    ├─ load_csv()        (existing)
    └─ load_from_database()  (new)
    ↓
Same Dict Format Either Way
```

**Key**: Solvers don't care where data comes from. They just get a dict.

## Database Schema

All tables are in [`database/schema.sql`](../database/schema.sql).

**Key fixes from your original spec:**
- ✅ Added `deadline_hours` to customers table (was missing)
- ✅ Used PostgreSQL types: `SERIAL`, `VARCHAR`, `DOUBLE PRECISION`, `NUMERIC`
- ✅ Node/depot/customer IDs are `VARCHAR(50)` to match 'D1', 'C1' format

**Core tables for solver:**
- `nodes`, `depots`, `customers`, `vehicles`, `items`, `orders`

**Webapp tables:**
- `users`, `sessions`, `datasets`, `experiments`, `result_metrics`, `routes`

## CSV File Updates

Rename these columns in your CSV files:

```csv
# data/depots.csv
depot_id,x,y          # was: depot_id,latitude,longitude

# data/customers.csv
customer_id,x,y,deadline_hours  # was: customer_id,latitude,longitude,deadline_hours

# data/vehicles.csv
vehicle_id,depot_id,vehicle_type,capacity_kg,max_operational_hrs,speed_kmh
# was: vehicle_id,depot_id,capacity_kg,max_time_hours,speed_kmh
# (add vehicle_type column too)

# data/items.csv (unchanged)
item_id,weight_kg,expiry_hours

# data/orders.csv (unchanged)
customer_id,item_id,quantity
```

## Implementation Details

### 1. CSV Updates (Manual)

Just rename the columns in your CSV files:
- `data/depots.csv`: change header line
- `data/customers.csv`: change header line
- `data/vehicles.csv`: change header line, add `vehicle_type` column

### 2. Python Code Changes

**File**: `src/data_loader.py`
- Line ~88, 93: Change `row['latitude']`, `row['longitude']` → `row['x']`, `row['y']`
- Line ~105: Change `'max_time_hours'` → `'max_operational_hrs'`
- Add new method: `load_from_database()` (see design.md for code)

**File**: `src/database.py` (new file)
- Create `DatabaseConnection` class
- Handles SQLAlchemy connections
- See design.md for complete code

### 3. Dependencies

Add to `requirements.txt`:
```
sqlalchemy>=2.0.0
psycopg2-binary>=2.9.0
```

Then:
```bash
pip install -r requirements.txt
```

#### New Method: `load_from_database()`

```python
def load_from_database(self, db_connection, dataset_id: int) -> Dict:
    """
    Load MDVRP data from database.

    Performs JOINs to denormalize data into same format as CSV loading.
    Returns identical dict structure as load_csv() for compatibility.

    Args:
        db_connection: Database connection object
        dataset_id: ID of dataset to load

    Returns:
        Dict with same structure as load_csv()

    Raises:
        ValueError: If data validation fails
        DatabaseError: If query fails
    """
    # Query depots with coordinates
    depots_query = """
        SELECT d.depot_id, n.x, n.y
        FROM depots d
        JOIN nodes n ON d.node_id = n.node_id
        WHERE d.dataset_id = ?
    """

    # Query customers with coordinates and deadlines
    customers_query = """
        SELECT c.customer_id, n.x, n.y, c.deadline_hours
        FROM customers c
        JOIN nodes n ON c.node_id = n.node_id
        WHERE c.dataset_id = ?
    """

    # Query vehicles with depot assignments
    vehicles_query = """
        SELECT vehicle_id, depot_id, vehicle_type,
               capacity_kg, max_operational_hrs, speed_kmh
        FROM vehicles
        WHERE dataset_id = ?
    """

    # Query items
    items_query = """
        SELECT item_id, weight_kg, expiry_hours
        FROM items
        WHERE dataset_id = ?
    """

    # Query orders
    orders_query = """
        SELECT o.customer_id, o.item_id, o.quantity
        FROM orders o
        JOIN customers c ON o.customer_id = c.customer_id
        WHERE c.dataset_id = ?
    """

    # Transform to same dict format as CSV
    # ... (implementation details in design doc)
```

### 3. Algorithm Compatibility

**NO CHANGES NEEDED** to:
- ✅ `mdvrp_greedy.py`
- ✅ `mdvrp_hga.py`
- ✅ `milp.py`
- ✅ `src/distance_matrix.py`
- ✅ `src/exporter.py`

All solvers work with the dict format regardless of whether data came from CSV or database.

### 3. Algorithm Compatibility

#### No Changes Required To:
- ✅ `mdvrp_greedy.py`: Uses dict from data loader, doesn't care about source
- ✅ `mdvrp_hga.py`: Uses dict from data loader, doesn't care about source
- ✅ `milp.py`: Uses dict from data loader, doesn't care about source
- ✅ `src/distance_matrix.py`: Works with coordinates dict regardless of source
- ✅ `src/exporter.py`: Exports solver results, independent of data source

#### Data Format Contract
```python
# Both CSV and DB loading must return this exact structure:
{
    'depots': [...],
    'customers': [...],
    'vehicles': [...],
    'items': [...],
    'coordinates': {node_id: (x, y), ...},
    'vehicle_speed': {...},
    'depot_for_vehicle': {...},
    'vehicle_capacity': {...},
    'max_operational_time': {...},
    'customer_deadlines': {...},
    'item_weights': {...},
    'item_expiry': {...},
    'customer_orders': {...}
}
```

## Testing Strategy

### Unit Tests
```python
# tests/test_database_loading.py

def test_load_database_returns_same_format_as_csv():
    """Verify DB loading returns identical structure to CSV loading."""
    csv_data = loader.load_csv('data/')
    db_data = loader.load_from_database(conn, dataset_id=1)

    assert set(csv_data.keys()) == set(db_data.keys())
    # Compare all nested structures...

def test_database_coordinates_match_csv():
    """Coordinates from DB match coordinates from CSV."""
    csv_data = loader.load_csv('data/')
    db_data = loader.load_from_database(conn, dataset_id=1)

    assert csv_data['coordinates'] == db_data['coordinates']

def test_all_solvers_work_with_db_data():
    """Verify all solvers work with database-loaded data."""
    from mdvrp_greedy import MDVRPGreedy
    from mdvrp_hga import MDVRPHGA
    from milp import MDVRP

    db_data = loader.load_from_database(conn, dataset_id=1)

    # Test each solver
    greedy = MDVRPGreedy(params=db_data, ...)
    solution, status = greedy.solve()
    assert status == 'feasible'
```

### Integration Test
```python
def test_full_database_workflow():
    """Test complete workflow: DB → Solver → Export."""
    # 1. Load from database
    data = loader.load_from_database(conn, dataset_id=1)

    # 2. Run solver
    solver = MDVRPGreedy(params=data, ...)
    solution, status = solver.solve()

    # 3. Verify solution
    assert status == 'feasible'
    assert solution['fitness'] > 0
```

## Implementation Tasks

### Phase 1: Prep Work (2-3 hours)
1. ✅ Run `database/schema.sql` in your PostgreSQL database
2. ✅ Rename columns in CSV files (depots, customers, vehicles)
3. ✅ Install dependencies: `pip install sqlalchemy psycopg2-binary`

### Phase 2: Code Changes (3-4 hours)
4. ✅ Update `src/data_loader.py` column references (x/y instead of lat/lon)
5. ✅ Create `src/database.py` with `DatabaseConnection` class
6. ✅ Add `load_from_database()` method to `src/data_loader.py`

### Phase 3: Testing (2-3 hours)
7. ✅ Test `load_from_database()` returns same format as CSV
8. ✅ Test all three solvers work with DB data
9. ✅ Compare results (DB vs CSV should be identical)

**Total**: ~7-10 hours of actual work

## Timeline

- **Days 1-2**: Complete implementation
- **Days 3-4**: Testing and validation
- **Days 5-7**: Buffer for issues and webapp prep

**Leaves 7 days for webapp development** 🎯

## Risks and Mitigations

### Risk 1: Algorithm Data Dependencies
**Risk**: Algorithms might have hidden dependencies on specific data formats
**Mitigation**: Comprehensive testing of all solvers with DB data before proceeding to webapp

### Risk 2: Performance Issues
**Risk**: Database queries slower than CSV file loading
**Mitigation**: Benchmark DB loading vs CSV, optimize queries if needed

### Risk 3: Schema Mismatches
**Risk**: Database schema doesn't match actual query needs
**Mitigation**: Test queries early, iterate schema if needed

### Risk 4: Time Constraints
**Risk**: 2-week deadline too aggressive
**Mitigation**: Use SQLite for simplicity, cut non-essential features, focus on core functionality

## Success Criteria

1. ✅ `load_from_database()` method working and tested
2. ✅ All three solvers (Greedy, HGA, MILP) work with DB data
3. ✅ DB-loaded data produces identical results to CSV-loaded data
4. ✅ No modifications to algorithm logic required
5. ✅ CSV loading still works (backward compatibility)
6. ✅ Database schema documented with deadline_hours added
7. ✅ Integration tests passing

## Timeline

- **Days 1-2**: Foundation (schema, CSV updates, connection layer)
- **Days 3-4**: Implement `load_from_database()` and testing
- **Days 5-6**: Solver validation and performance testing
- **Day 7**: Documentation and cleanup

**Total**: 7 days for database integration (leaves 7 days for webapp development)

## Next Steps

1. Review and approve this proposal
2. Create detailed design document
3. Begin implementation with Phase 1

---

**Status**: Proposed
**Priority**: High (blocker for webapp development)
**Dependencies**: None
