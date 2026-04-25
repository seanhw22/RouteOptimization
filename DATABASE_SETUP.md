# Database Setup Guide

## Quick Start with .env File

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Create Your .env File

Copy the example file:
```bash
cp .env.example .env
```

Edit `.env` with your database credentials:
```bash
# For default PostgreSQL setup
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/mdvrp

# Or with your specific user/password
DATABASE_URL=postgresql://your_user:your_password@localhost:5432/mdvrp
```

### 3. Create Database Tables

```bash
psql -U postgres -d mdvrp -f database/schema.sql
```

### 4. Populate with Sample Data

```bash
psql -U postgres -d mdvrp -f database/populate_data.sql
```

### 5. Test the Connection

```python
from src.data_loader import MDVRPDataLoader
from src.database import DatabaseConnection

# Automatically uses DATABASE_URL from .env file
conn = DatabaseConnection()

if conn.test_connection():
    print("Database connected!")
    
    loader = MDVRPDataLoader()
    data = loader.load_from_database(conn, dataset_id=1)
    
    print(f"Loaded {len(data['customers'])} customers")
    print(f"Loaded {len(data['vehicles'])} vehicles")
```

## Common Issues

### Issue: "password authentication failed"

**Solution**: Update the DATABASE_URL in `.env` with your correct PostgreSQL password.

### Issue: "database 'mdvrp' does not exist"

**Solution**: Create the database first:
```bash
psql -U postgres
CREATE DATABASE mdvrp;
\q
```

### Issue: "relation 'nodes' does not exist"

**Solution**: Run the schema file:
```bash
psql -U postgres -d mdvrp -f database/schema.sql
```

### Issue: "no data in tables"

**Solution**: Populate the data:
```bash
psql -U postgres -d mdvrp -f database/populate_data.sql
```

## Alternative: Without .env File

You can also set the DATABASE_URL directly in code:

```python
from src.database import DatabaseConnection

conn = DatabaseConnection('postgresql://user:pass@localhost:5432/mdvrp')
```

Or use environment variable:
```bash
export DATABASE_URL="postgresql://user:pass@localhost:5432/mdvrp"
python your_script.py
```

## Distance Caching

1. **First run** — computes distance matrix, saves to `node_distances` table
2. **Subsequent runs** — loads from cache (50-80% faster data loading)
3. **Validation** — spot-checks 3 random pairs to ensure cache integrity
4. **Invalidation** — if coordinates change, delete cache and recompute:
```sql
DELETE FROM node_distances WHERE dataset_id = 1;
```

## Querying Experiments

```sql
-- Compare runtimes across algorithms
SELECT
  algorithm,
  AVG(r.runtime_id) as avg_runtime,
  COUNT(*) as num_runs
FROM experiments e
LEFT JOIN result_metrics r ON e.experiment_id = r.experiment_id
GROUP BY algorithm
ORDER BY avg_runtime;

-- View all experiments with results
SELECT
  e.experiment_id,
  e.algorithm,
  e.seed,
  r.runtime_id as runtime_seconds,
  d.name as dataset_name
FROM experiments e
JOIN datasets d ON e.dataset_id = d.dataset_id
LEFT JOIN result_metrics r ON e.experiment_id = r.experiment_id
ORDER BY e.experiment_id DESC;

-- Retrieve route segments for an experiment
SELECT vehicle_id, node_start_id, node_end_id, total_distance
FROM routes
WHERE experiment_id = 123
ORDER BY vehicle_id, route_id;
```

## Troubleshooting

| Error | Likely cause | Fix |
|-------|-------------|-----|
| `password authentication failed` | Wrong credentials in DATABASE_URL | Update `.env` |
| `database 'mdvrp' does not exist` | DB not created | `CREATE DATABASE mdvrp;` in psql |
| `relation 'nodes' does not exist` | Schema not applied | Run `database/schema.sql` |
| `Dataset N not found` | Data not loaded | Run `scripts/populate_database.py` |
| Slow first run | Distance computation | Normal; subsequent runs use cache |

If PostgreSQL is not running: `docker ps` or `sudo systemctl status postgresql`

## PostgreSQL Setup (if needed)

### Windows
1. Download from: https://www.postgresql.org/download/windows/
2. Or use: `choco install postgresql`

### Linux
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
```

### macOS
```bash
brew install postgresql@14
brew services start postgresql@14
```

### Default PostgreSQL Credentials
- **User**: `postgres`
- **Password**: `postgres` (often the default on install)
- **Port**: `5432`
- **Host**: `localhost`
