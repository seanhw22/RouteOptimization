# PostgreSQL Setup Guide for MDVRP System

## Quick Start (Docker - Recommended)

### Prerequisites
- Docker Desktop installed and running

### Setup Steps

1. **Create docker-compose.yml** in project root:

```yaml
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
      - ./database/schema.sql:/docker-entrypoint-initdb.d/schema.sql

volumes:
  postgres_data:
```

2. **Start PostgreSQL**:

```bash
docker-compose up -d
```

3. **Verify connection**:

```bash
docker exec -it mdvrp_db psql -U mdvrp -d mdvrp -c "SELECT 1;"
```

4. **Initialize database schema** (if not auto-loaded):

```bash
docker exec -it mdvrp_db psql -U mdvrp -d mdvrp -f /docker-entrypoint-initdb.d/schema.sql
```

5. **Stop database**:

```bash
docker-compose down
```

---

## Alternative: Local PostgreSQL Installation

### Windows

1. **Download installer** from https://www.postgresql.org/download/windows/

2. **Or use Chocolatey**:
```bash
choco install postgresql
```

3. **Start PostgreSQL service**:
```bash
# Should start automatically after installation
# If not, start from Services
```

4. **Create database and user**:
```bash
# Open psql as postgres user
psql -U postgres

# In psql:
CREATE DATABASE mdvrp;
CREATE USER mdvrp WITH PASSWORD 'mdvrp';
GRANT ALL PRIVILEGES ON DATABASE mdvrp TO mdvrp;
\q
```

### Linux (Ubuntu/Debian)

1. **Install PostgreSQL**:
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
```

2. **Start service**:
```bash
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

3. **Create database and user**:
```bash
sudo -u postgres psql

# In psql:
CREATE DATABASE mdvrp;
CREATE USER mdvrp WITH PASSWORD 'mdvrp';
GRANT ALL PRIVILEGES ON DATABASE mdvrp TO mdvrp;
\q
```

### macOS

1. **Install using Homebrew**:
```bash
brew install postgresql@14
brew services start postgresql@14
```

2. **Create database and user**:
```bash
psql postgres

# In psql:
CREATE DATABASE mdvrp;
CREATE USER mdvrp WITH PASSWORD 'mdvrp';
GRANT ALL PRIVILEGES ON DATABASE mdvrp TO mdvrp;
\q
```

---

## Environment Configuration

### Option 1: .env file

Create `.env` in project root:

```bash
DATABASE_URL=postgresql://mdvrp:mdvrp@localhost:5432/mdvrp
```

### Option 2: System environment variable

**Windows (PowerShell)**:
```powershell
$env:DATABASE_URL="postgresql://mdvrp:mdvrp@localhost:5432/mdvrp"
```

**Linux/macOS**:
```bash
export DATABASE_URL="postgresql://mdvrp:mdvrp@localhost:5432/mdvrp"
```

### Option 3: Pass directly in code

```python
from src.database import DatabaseConnection

conn = DatabaseConnection('postgresql://mdvrp:mdvrp@localhost:5432/mdvrp')
```

---

## Test Database Connection

Create test script `tests/test_db_connection.py`:

```python
from src.database import DatabaseConnection

def test_connection():
    """Test database connection."""
    try:
        conn = DatabaseConnection()
        if conn.test_connection():
            print("✅ Database connection successful!")
            return True
        else:
            print("❌ Database connection failed!")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == '__main__':
    test_connection()
```

Run test:
```bash
python tests/test_db_connection.py
```

---

## Initialize Database Schema

After database is running, initialize schema:

```bash
# From project root
python scripts/init_database.py
```

Or manually:

```bash
psql -U mdvrp -d mdvrp -f database/schema.sql
```

---

## Common Issues and Solutions

### Issue: "Connection refused"

**Solution**: Check if PostgreSQL is running:

```bash
# Linux/macOS
sudo systemctl status postgresql

# Windows
# Check Services for "postgresql-x64-[version]"

# Docker
docker ps | grep postgres
```

### Issue: "FATAL: database "mdvrp" does not exist"

**Solution**: Create the database:

```bash
psql -U postgres -c "CREATE DATABASE mdvrp;"
psql -U postgres -c "CREATE USER mdvrp WITH PASSWORD 'mdvrp';"
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE mdvrp TO mdvrp;"
```

### Issue: "FATAL: password authentication failed"

**Solution**: Reset password:

```bash
psql -U postgres
ALTER USER mdvrp WITH PASSWORD 'mdvrp';
\q
```

### Issue: Port 5432 already in use

**Solution**: Change port in docker-compose.yml:

```yaml
ports:
  - "5433:5432"  # Use 5433 instead
```

Then update DATABASE_URL:
```bash
DATABASE_URL=postgresql://mdvrp:mdvrp@localhost:5433/mdvrp
```

---

## PostgreSQL GUI Tools (Optional)

### pgAdmin 4
- Download: https://www.pgadmin.org/download/
- Visual database management
- Query editor
- Backup/restore tools

### DBeaver
- Download: https://dbeaver.io/download/
- Free, open-source
- Supports multiple databases
- Great for development

### VS Code Extension
- Install "PostgreSQL" extension
- Query directly from VS Code
- Convenient for development

---

## Backup and Restore

### Backup database

```bash
pg_dump -U mdvrp mdvrp > backup.sql
```

### Restore database

```bash
psql -U mdvrp mdvrp < backup.sql
```

### Docker backup

```bash
# Backup
docker exec mdvrp_db pg_dump -U mdvrp mdvrp > backup.sql

# Restore
docker exec -i mdvrp_db psql -U mdvrp mdvrp < backup.sql
```

---

## Performance Tuning (Optional)

### PostgreSQL Configuration

Edit `postgresql.conf` (location varies by OS):

```ini
# Memory settings
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB

# Connection settings
max_connections = 100

# Query optimization
random_page_cost = 1.1  # For SSD storage
```

Restart PostgreSQL after changes.

---

## Next Steps

After PostgreSQL is set up:

1. ✅ Initialize database schema
2. ✅ Test connection with Python
3. ✅ Implement `load_from_database()` method
4. ✅ Test with MDVRP solvers

---

**Need help?**
- PostgreSQL Docs: https://www.postgresql.org/docs/
- SQLAlchemy Docs: https://docs.sqlalchemy.org/
- Docker PostgreSQL: https://hub.docker.com/_/postgres
