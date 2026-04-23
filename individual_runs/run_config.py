"""
Shared configuration and utilities for individual MDVRP run scripts
"""
import os
from pathlib import Path
from src.database import DatabaseConnection


# Add parent directory to path
def setup_path():
    """Add parent directory to Python path for imports"""
    import sys
    parent_dir = str(Path(__file__).parent.parent)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    return parent_dir


def load_env_config():
    """
    Load configuration from .env file

    Returns:
    --------
    dict with keys:
        - use_database: bool (from USE_DATABASE env var, default False)
        - dataset_id: int (from DATASET_ID env var, default 1)
    """
    # Load from .env
    env_file = Path(__file__).parent.parent / '.env'
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

    use_database = os.getenv('USE_DATABASE', 'false').lower() in ('true', '1', 'yes')
    dataset_id = int(os.getenv('DATASET_ID', '1'))

    return {
        'use_database': use_database,
        'dataset_id': dataset_id
    }


def setup_data_source(dataset_id=None):
    """
    Setup data source with automatic fallback: Database → CSV

    Priority:
    1. Database (if USE_DATABASE=true and connection succeeds)
    2. CSV files from data/ folder (fallback)
    3. Error if neither available

    Args:
    dataset_id: Dataset ID to load from database

    Returns:
    --------
    tuple: (db_connection, dataset_id, source_type)
        - db_connection: DatabaseConnection object or None
        - dataset_id: int or None
        - source_type: 'database' | 'csv' | None
    """
    config = load_env_config()
    dataset_id = dataset_id or config['dataset_id']

    # Try database first (if configured)
    if config['use_database']:
        try:
            db_connection = DatabaseConnection()
            if db_connection.test_connection():
                print(f"[INFO] Using database: dataset_id = {dataset_id}")
                return db_connection, dataset_id, 'database'
            else:
                print("[WARNING] Database connection failed")
                print("         Will attempt CSV fallback")
        except Exception as e:
            print(f"[WARNING] Database connection error: {e}")
            print("         Will attempt CSV fallback")

    # Fallback to CSV files
    data_dir = Path(__file__).parent.parent / 'data'
    if data_dir.exists() and (data_dir / 'depots.csv').exists():
        print("[INFO] Using CSV files from data/ directory")
        return None, None, 'csv'

    # Neither source available
    print("[ERROR] No data source available!")
    print("\nTroubleshooting:")
    print("  1. Database connection failed")
    print("     -> Check DATABASE_URL in .env file")
    print("     -> Verify PostgreSQL is running")
    print(f"     -> Current: DATABASE_URL={os.getenv('DATABASE_URL', 'not set')}")
    print("\n  2. CSV fallback not available")
    print(f"     -> data/ folder not found or missing depots.csv")
    print(f"     -> Expected location: {data_dir}")
    print("\nFix one of the above and try again.")
    exit(1)


def cleanup_database_connection(db_connection):
    """Cleanup database connection if it exists"""
    if db_connection:
        db_connection.engine.dispose()
