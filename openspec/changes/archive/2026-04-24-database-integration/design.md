# Design: Database Integration for MDVRP System

## System Architecture

### Component Overview

```
┌───────────────────────────────────────────────────────────────┐
│                    Application Layer                          │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐              │
│  │   Greedy   │  │    HGA     │  │   MILP     │              │
│  │  Solver    │  │  Solver    │  │  Solver    │              │
│  └────────────┘  └────────────┘  └────────────┘              │
└───────────────────────────────────────────────────────────────┘
                            ↓
┌───────────────────────────────────────────────────────────────┐
│                   Data Abstraction Layer                      │
│                  (src/data_loader.py)                         │
│                                                               │
│  ┌────────────────────┐         ┌────────────────────┐       │
│  │   load_csv()       │         │ load_from_database()│       │
│  │                    │         │                     │       │
│  │  - Read CSV files  │         │  - Execute SQL      │       │
│  │  - Parse data      │         │  - JOIN tables      │       │
│  │  - Validate        │         │  - Transform rows   │       │
│  │  - Return dict     │         │  - Return dict      │       │
│  └────────────────────┘         └────────────────────┘       │
│           │                                │                  │
│           └────────────┬───────────────────┘                  │
│                        ↓                                     │
│            ┌───────────────────────┐                         │
│            │  Standardized Dict    │                         │
│            │  Format (Contract)    │                         │
│            └───────────────────────┘                         │
└───────────────────────────────────────────────────────────────┘
                    ↓                    ↓
           ┌─────────────┐      ┌─────────────┐
           │ CSV Files   │      │  Database   │
           │ (data/)     │      │ (PostgreSQL)│
           └─────────────┘      └─────────────┘
```

## Database Schema Design

### PostgreSQL-Specific Data Types

```sql
-- PostgreSQL uses SERIAL for auto-increment (not INTEGER PRIMARY KEY)
-- PostgreSQL uses DOUBLE PRECISION (not DOUBLE)
-- PostgreSQL uses NUMERIC/DECIMAL for precise decimal numbers
```

### Complete Schema with deadline_hours Fix (PostgreSQL)

```sql
-- Core data tables (used by solver)

CREATE TABLE nodes (
    node_id VARCHAR(50) PRIMARY KEY,  -- Changed from INTEGER to match node IDs like 'D1', 'C1'
    dataset_id INTEGER NOT NULL,
    x DOUBLE PRECISION NOT NULL,
    y DOUBLE PRECISION NOT NULL,
    FOREIGN KEY (dataset_id) REFERENCES datasets(dataset_id)
);

CREATE TABLE depots (
    depot_id VARCHAR(50) PRIMARY KEY,
    node_id VARCHAR(50) NOT NULL,
    dataset_id INTEGER NOT NULL,
    FOREIGN KEY (node_id) REFERENCES nodes(node_id),
    FOREIGN KEY (dataset_id) REFERENCES datasets(dataset_id)
);

CREATE TABLE customers (
    customer_id VARCHAR(50) PRIMARY KEY,
    node_id VARCHAR(50) NOT NULL,
    dataset_id INTEGER NOT NULL,
    deadline_hours INTEGER NOT NULL,  -- ← ADDED: Was missing in original spec
    FOREIGN KEY (node_id) REFERENCES nodes(node_id),
    FOREIGN KEY (dataset_id) REFERENCES datasets(dataset_id)
);

CREATE TABLE vehicles (
    vehicle_id VARCHAR(50) PRIMARY KEY,
    depot_id VARCHAR(50) NOT NULL,
    dataset_id INTEGER NOT NULL,
    vehicle_type VARCHAR(50) NOT NULL,
    capacity_kg NUMERIC(8,2) NOT NULL,
    max_operational_hrs NUMERIC(8,2) NOT NULL,
    speed_kmh NUMERIC(8,2) NOT NULL,
    FOREIGN KEY (depot_id) REFERENCES depots(depot_id),
    FOREIGN KEY (dataset_id) REFERENCES datasets(dataset_id)
);

CREATE TABLE items (
    item_id VARCHAR(50) PRIMARY KEY,
    dataset_id INTEGER NOT NULL,
    weight_kg NUMERIC(8,2) NOT NULL,
    expiry_hours INTEGER NOT NULL,
    FOREIGN KEY (dataset_id) REFERENCES datasets(dataset_id)
);

CREATE TABLE orders (
    order_id SERIAL PRIMARY KEY,  -- Auto-increment integer ID
    customer_id VARCHAR(50) NOT NULL,
    item_id VARCHAR(50) NOT NULL,
    dataset_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    FOREIGN KEY (item_id) REFERENCES items(item_id),
    FOREIGN KEY (dataset_id) REFERENCES datasets(dataset_id)
);

-- Webapp tables (not used by solvers)

CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

CREATE TABLE sessions (
    session_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE datasets (
    dataset_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    session_id INTEGER,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);

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

CREATE TABLE result_metrics (
    result_id SERIAL PRIMARY KEY,
    experiment_id INTEGER NOT NULL,
    runtime_id NUMERIC(8,2),
    constraint_violation INTEGER,
    FOREIGN KEY (experiment_id) REFERENCES experiments(experiment_id)
);

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

-- Optional: Pre-computed distances (not used in initial implementation)
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
```

### Database Indexes (Performance)

```sql
-- Speed up common queries

CREATE INDEX idx_nodes_dataset ON nodes(dataset_id);
CREATE INDEX idx_depots_dataset ON depots(dataset_id);
CREATE INDEX idx_customers_dataset ON customers(dataset_id);
CREATE INDEX idx_vehicles_dataset ON vehicles(dataset_id);
CREATE INDEX idx_items_dataset ON items(dataset_id);
CREATE INDEX idx_orders_customer ON orders(customer_id);

-- Webapp queries
CREATE INDEX idx_experiments_dataset ON experiments(dataset_id);
CREATE INDEX idx_datasets_user ON datasets(user_id);
CREATE INDEX idx_sessions_user ON sessions(user_id);
CREATE INDEX idx_sessions_token ON sessions(session_token);
```

## Data Loading Implementation

### CSV Loading Updates

#### Modified File: `src/data_loader.py`

**Column Name Changes:**
```python
# Line 88-93: Depot coordinates
coordinates[row['depot_id']] = (row['x'], row['y'])  # was lat/lon

# Line 92-94: Customer coordinates
coordinates[row['customer_id']] = (row['x'], row['y'])  # was lat/lon

# Line 105: Max operational time
max_operational_time = vehicles_df.set_index('vehicle_id')['max_operational_hrs'].to_dict()
```

**No changes needed:**
- ✅ `deadline_hours` (already correct)
- ✅ `quantity` in orders (already correct)
- ✅ All other fields

### Database Loading Implementation

#### New Method: `load_from_database()`

```python
def load_from_database(self, db_connection, dataset_id: int) -> Dict:
    """
    Load MDVRP data from database.

    Args:
        db_connection: SQLAlchemy connection or session
        dataset_id: ID of dataset to load

    Returns:
        Dict with same structure as load_csv()

    Raises:
        ValueError: If data validation fails
    """
    import pandas as pd

    # Query depots with coordinates (JOIN)
    depots_query = text("""
        SELECT d.depot_id, n.x, n.y
        FROM depots d
        JOIN nodes n ON d.node_id = n.node_id
        WHERE d.dataset_id = :dataset_id
    """)
    depots_df = pd.read_sql(
        depots_query,
        db_connection.bind,
        params={'dataset_id': dataset_id}
    )

    # Query customers with coordinates and deadlines (JOIN)
    customers_query = text("""
        SELECT c.customer_id, n.x, n.y, c.deadline_hours
        FROM customers c
        JOIN nodes n ON c.node_id = n.node_id
        WHERE c.dataset_id = :dataset_id
    """)
    customers_df = pd.read_sql(
        customers_query,
        db_connection.bind,
        params={'dataset_id': dataset_id}
    )

    # Query vehicles with depot info
    vehicles_query = text("""
        SELECT vehicle_id, depot_id, vehicle_type,
               capacity_kg, max_operational_hrs, speed_kmh
        FROM vehicles
        WHERE dataset_id = :dataset_id
    """)
    vehicles_df = pd.read_sql(
        vehicles_query,
        db_connection.bind,
        params={'dataset_id': dataset_id}
    )

    # Query items
    items_query = text("""
        SELECT item_id, weight_kg, expiry_hours
        FROM items
        WHERE dataset_id = :dataset_id
    """)
    items_df = pd.read_sql(
        items_query,
        db_connection.bind,
        params={'dataset_id': dataset_id}
    )

    # Query orders (need to join to customers to filter by dataset)
    orders_query = text("""
        SELECT o.customer_id, o.item_id, o.quantity
        FROM orders o
        JOIN customers c ON o.customer_id = c.customer_id
        WHERE c.dataset_id = :dataset_id
    """)
    orders_df = pd.read_sql(
        orders_query,
        db_connection.bind,
        params={'dataset_id': dataset_id}
    )

    # Process data identically to CSV loading
    # (reuse existing logic from load_csv())

    self.depots = depots_df['depot_id'].tolist()
    self.customers = customers_df['customer_id'].tolist()
    self.vehicles = vehicles_df['vehicle_id'].tolist()
    self.items = items_df['item_id'].tolist()

    # Build coordinates
    coordinates = {}
    for _, row in depots_df.iterrows():
        coordinates[row['depot_id']] = (row['x'], row['y'])
    for _, row in customers_df.iterrows():
        coordinates[row['customer_id']] = (row['x'], row['y'])

    # Build vehicle attributes
    vehicle_speed = vehicles_df.set_index('vehicle_id')['speed_kmh'].to_dict()
    depot_for_vehicle = vehicles_df.set_index('vehicle_id')['depot_id'].to_dict()
    vehicle_capacity = vehicles_df.set_index('vehicle_id')['capacity_kg'].to_dict()
    max_operational_time = vehicles_df.set_index('vehicle_id')['max_operational_hrs'].to_dict()

    # Build customer attributes
    customer_deadlines = customers_df.set_index('customer_id')['deadline_hours'].to_dict()

    # Build item attributes
    item_weights = items_df.set_index('item_id')['weight_kg'].to_dict()
    item_expiry = items_df.set_index('item_id')['expiry_hours'].to_dict()

    # Build customer orders (nested dict)
    customer_orders = {}
    for customer in self.customers:
        customer_orders[customer] = {}
        customer_orders_df = orders_df[orders_df['customer_id'] == customer]
        for _, row in customer_orders_df.iterrows():
            customer_orders[customer][row['item_id']] = row['quantity']

    # Validate using existing validation method
    self._validate_data(
        coordinates, vehicle_speed, depot_for_vehicle,
        vehicle_capacity, max_operational_time, customer_deadlines,
        item_weights, item_expiry, customer_orders
    )

    # Package data (identical to CSV format)
    self.data = {
        'depots': self.depots,
        'customers': self.customers,
        'vehicles': self.vehicles,
        'items': self.items,
        'coordinates': coordinates,
        'vehicle_speed': vehicle_speed,
        'depot_for_vehicle': depot_for_vehicle,
        'vehicle_capacity': vehicle_capacity,
        'max_operational_time': max_operational_time,
        'customer_deadlines': customer_deadlines,
        'item_weights': item_weights,
        'item_expiry': item_expiry,
        'customer_orders': customer_orders
    }

    return self.data
```

### Database Connection Layer

#### New File: `src/database.py`

```python
"""
Database connection management for MDVRP system.
Uses PostgreSQL with psycopg2 driver.
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from typing import Optional
import os

class DatabaseConnection:
    """Manage database connections for MDVRP system."""

    def __init__(self, db_url: Optional[str] = None):
        """
        Initialize database connection.

        Args:
            db_url: PostgreSQL database URL
                   Format: 'postgresql://user:password@host:port/database'
                   If None, uses environment variable DATABASE_URL
        """
        if db_url is None:
            db_url = os.getenv(
                'DATABASE_URL',
                'postgresql://mdvrp:mdvrp@localhost:5432/mdvrp'
            )

        self.engine = create_engine(db_url, pool_size=10, max_overflow=20)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def get_session(self):
        """Get new database session."""
        return self.SessionLocal()

    def initialize_schema(self, schema_sql_path: str):
        """
        Initialize database schema from SQL file.

        Args:
            schema_sql_path: Path to SQL file with CREATE TABLE statements
        """
        with open(schema_sql_path, 'r') as f:
            schema_sql = f.read()

        with self.engine.begin() as conn:
            conn.execute(text(schema_sql))

    def test_connection(self) -> bool:
        """Test database connection."""
        try:
            with self.get_session() as session:
                session.execute(text("SELECT 1"))
            return True
        except Exception as e:
            print(f"Database connection failed: {e}")
            return False
```

## Data Format Contract

### Standardized Dict Structure

Both `load_csv()` and `load_from_database()` MUST return this exact structure:

```python
{
    # Entity lists
    'depots': List[str],              # ['D1', 'D2', ...]
    'customers': List[str],           # ['C1', 'C2', ...]
    'vehicles': List[str],            # ['V1', 'V2', ...]
    'items': List[str],               # ['I1', 'I2', ...]

    # Coordinate mapping
    'coordinates': Dict[str, Tuple[float, float]],
    # {'D1': (-6.104, 106.940), 'C1': (-6.200, 106.850), ...}

    # Vehicle attributes
    'vehicle_speed': Dict[str, float],
    # {'V1': 60.0, 'V2': 50.0, ...}

    'depot_for_vehicle': Dict[str, str],
    # {'V1': 'D1', 'V2': 'D1', ...}

    'vehicle_capacity': Dict[str, float],
    # {'V1': 40.0, 'V2': 30.0, ...}

    'max_operational_time': Dict[str, float],
    # {'V1': 8.0, 'V2': 8.0, ...}

    # Customer attributes
    'customer_deadlines': Dict[str, int],
    # {'C1': 24, 'C2': 18, ...}

    # Item attributes
    'item_weights': Dict[str, float],
    # {'I1': 5.0, 'I2': 3.5, ...}

    'item_expiry': Dict[str, int],
    # {'I1': 24, 'I2': 48, ...}

    # Order mapping (nested dict)
    'customer_orders': Dict[str, Dict[str, int]],
    # {'C1': {'I1': 10, 'I2': 5}, 'C2': {'I1': 8}, ...}
}
```

## Testing Strategy

### Unit Tests: `tests/test_database_loading.py`

```python
import pytest
from src.data_loader import MDVRPDataLoader
from src.database import DatabaseConnection

@pytest.fixture
def db_connection():
    """Create test database connection."""
    conn = DatabaseConnection('postgresql://mdvrp:mdvrp@localhost:5432/mdvrp_test')
    # Initialize test data
    yield conn
    # Cleanup

@pytest.fixture
def sample_csv_data():
    """Load sample CSV data for comparison."""
    loader = MDVRPDataLoader()
    return loader.load_csv('data/')

def test_database_connection(db_connection):
    """Test database connection works."""
    assert db_connection.test_connection() == True

def test_load_database_returns_valid_dict(db_connection):
    """Database loading returns valid dict structure."""
    loader = MDVRPDataLoader()
    data = loader.load_from_database(db_connection.get_session(), dataset_id=1)

    # Check required keys exist
    required_keys = [
        'depots', 'customers', 'vehicles', 'items',
        'coordinates', 'vehicle_speed', 'depot_for_vehicle',
        'vehicle_capacity', 'max_operational_time',
        'customer_deadlines', 'item_weights', 'item_expiry',
        'customer_orders'
    ]

    for key in required_keys:
        assert key in data

def test_database_coordinates_format(db_connection):
    """Coordinates from database are tuples (x, y)."""
    loader = MDVRPDataLoader()
    data = loader.load_from_database(db_connection.get_session(), dataset_id=1)

    for node_id, coords in data['coordinates'].items():
        assert isinstance(coords, tuple)
        assert len(coords) == 2
        assert isinstance(coords[0], (int, float))  # x
        assert isinstance(coords[1], (int, float))  # y

def test_database_data_matches_csv(db_connection, sample_csv_data):
    """Database-loaded data matches CSV-loaded data."""
    loader = MDVRPDataLoader()
    db_data = loader.load_from_database(db_connection.get_session(), dataset_id=1)

    # Compare coordinates
    assert db_data['coordinates'] == sample_csv_data['coordinates']

    # Compare all attributes
    assert db_data['vehicle_speed'] == sample_csv_data['vehicle_speed']
    assert db_data['depot_for_vehicle'] == sample_csv_data['depot_for_vehicle']
    assert db_data['customer_deadlines'] == sample_csv_data['customer_deadlines']

def test_solvers_work_with_database_data(db_connection):
    """All solvers work with database-loaded data."""
    from mdvrp_greedy import MDVRPGreedy
    from mdvrp_hga import MDVRPHGA
    from milp import MDVRP

    loader = MDVRPDataLoader()
    data = loader.load_from_database(db_connection.get_session(), dataset_id=1)

    # Test Greedy
    greedy = MDVRPGreedy(
        depots=data['depots'],
        customers=data['customers'],
        vehicles=data['vehicles'],
        items=data['items'],
        params=data,
        seed=42
    )
    solution, status = greedy.solve()
    assert status in ['feasible', 'optimal']

    # Test HGA
    hga = MDVRPHGA(
        depots=data['depots'],
        customers=data['customers'],
        vehicles=data['vehicles'],
        items=data['items'],
        params=data,
        seed=42,
        population_size=10,
        generations=5
    )
    solution, status = hga.solve()
    assert status in ['feasible', 'optimal']

    # Test MILP
    milp = MDVRP(
        depots=data['depots'],
        customers=data['customers'],
        vehicles=data['vehicles'],
        items=data['items'],
        params=data
    )
    milp.build_model()
    solution, status = milp.solve(time_limit=10)
    assert status in ['optimal', 'feasible', 'timeout']
```

### Integration Test: `tests/test_integration_database.py`

```python
def test_full_workflow_with_database():
    """Test complete workflow: DB → Solver → Export."""
    from src.data_loader import MDVRPDataLoader
    from src.database import DatabaseConnection
    from mdvrp_greedy import MDVRPGreedy
    from src.exporter import MDVRPExporter
    import tempfile
    import os

    # 1. Connect to database
    conn = DatabaseConnection('sqlite:///test_mdvrp.db')

    # 2. Load data from database
    loader = MDVRPDataLoader()
    data = loader.load_from_database(conn.get_session(), dataset_id=1)

    # 3. Run solver
    greedy = MDVRPGreedy(
        depots=data['depots'],
        customers=data['customers'],
        vehicles=data['vehicles'],
        items=data['items'],
        params=data,
        seed=42
    )
    solution, status = greedy.solve()

    # 4. Verify solution
    assert status == 'feasible'
    assert 'routes' in solution
    assert 'fitness' in solution

    # 5. Export solution
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        temp_file = f.name

    try:
        exporter = MDVRPExporter()
        exporter.export_csv(solution, temp_file)

        # Verify file created
        assert os.path.exists(temp_file)

        # Verify content
        with open(temp_file, 'r') as f:
            content = f.read()
            assert 'vehicle_id' in content
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)
```

## Performance Considerations

### Query Optimization

```python
# BAD: N+1 query problem
for vehicle in vehicles:
    depot = session.query(Depot).filter_by(depot_id=vehicle.depot_id).first()

# GOOD: Single query with JOIN
results = session.query(Vehicle, Depot)\
    .join(Depot, Vehicle.depot_id == Depot.depot_id)\
    .filter(Vehicle.dataset_id == dataset_id)\
    .all()
```

### Connection Pooling

SQLAlchemy handles connection pooling automatically:
```python
# Default: Pool of 5 connections
engine = create_engine('sqlite:///mdvrp.db', pool_size=5)

# For PostgreSQL (production)
engine = create_engine('postgresql://user:pass@localhost/mdvrp', pool_size=10)
```

### Expected Performance (PostgreSQL)

| Operation | CSV | PostgreSQL (Local) | PostgreSQL (Remote) |
|-----------|-----|-------------------|---------------------|
| Load 100 nodes | ~50ms | ~20ms | ~30-50ms |
| Load 1000 nodes | ~200ms | ~50ms | ~100-150ms |
| Coordinate lookup | O(1) | O(1) | O(1) |

PostgreSQL advantages over CSV:
- ✅ Indexed lookups (B-tree indexes)
- ✅ Query plan caching
- ✅ Connection pooling
- ✅ No CSV parsing overhead
- ✅ Concurrent query handling

### PostgreSQL Setup

#### Install PostgreSQL

**Windows:**
```bash
# Download installer from https://www.postgresql.org/download/windows/
# Or use Chocolatey:
choco install postgresql
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
```

**macOS:**
```bash
# Using Homebrew:
brew install postgresql@14
brew services start postgresql@14
```

#### Create Database and User

```bash
# Connect to PostgreSQL
psql -U postgres

# Create database and user
CREATE DATABASE mdvrp;
CREATE USER mdvrp WITH PASSWORD 'mdvrp';
GRANT ALL PRIVILEGES ON DATABASE mdvrp TO mdvrp;
\q

# Test connection
psql -U mdvrp -d mdvrp -c "SELECT 1;"
```

#### Environment Variables

```bash
# .env file or environment variables
DATABASE_URL=postgresql://mdvrp:mdvrp@localhost:5432/mdvrp
```

#### Docker Alternative (Recommended for Development)

```yaml
# docker-compose.yml
version: '3.8'
services:
  postgres:
    image: postgres:14-alpine
    container_name: mdvrp_db
    environment:
      POSTGRES_USER: mdvrp
      POSTGRES_PASSWORD: mdvrp
      POSTGRES_DB: mdvrp
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

```bash
# Start PostgreSQL
docker-compose up -d

# Stop PostgreSQL
docker-compose down

# Connect to database
docker exec -it mdvrp_db psql -U mdvrp -d mdvrp
```

## Error Handling

### Database Connection Errors

```python
def load_from_database(self, db_connection, dataset_id: int) -> Dict:
    try:
        # Attempt connection
        depots_df = pd.read_sql(depots_query, db_connection.bind, params={...})
    except OperationalError as e:
        raise ValueError(f"Database connection failed: {e}")
    except Exception as e:
        raise ValueError(f"Database query failed: {e}")
```

### Data Validation Errors

Reuse existing `_validate_data()` method to catch:
- Missing coordinates
- Invalid foreign keys
- Missing required attributes
- Data type mismatches

## Migration Commands

### CSV → PostgreSQL Migration Script

```python
# scripts/migrate_csv_to_database.py
import sys
from src.data_loader import MDVRPDataLoader
from src.database import DatabaseConnection

def migrate_csv_to_db(csv_dir: str, dataset_id: int, db_url: str):
    """Migrate CSV data to PostgreSQL database."""
    # Load from CSV
    loader = MDVRPDataLoader()
    data = loader.load_csv(csv_dir)

    # Connect to database
    conn = DatabaseConnection(db_url)

    # Insert data into database
    # (implementation details)

    print(f"Migrated dataset {dataset_id} from {csv_dir} to {db_url}")

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print("Usage: python migrate_csv_to_db.py <csv_dir> <dataset_id> <database_url>")
        print("Example: python migrate_csv_to_db.py data/1 'postgresql://mdvrp:mdvrp@localhost:5432/mdvrp'")
        sys.exit(1)

    migrate_csv_to_db(sys.argv[1], int(sys.argv[2]), sys.argv[3])
```

---

**Status**: Design Complete
**Next**: Implementation Phase
**Dependencies**: None
