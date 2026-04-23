"""
Database connection management for MDVRP system.
Uses PostgreSQL with psycopg2 driver.
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from typing import Optional
import os
from pathlib import Path


class DatabaseConnection:
    """Manage PostgreSQL database connections for MDVRP system."""

    def __init__(self, db_url: Optional[str] = None):
        """
        Initialize database connection.

        Args:
            db_url: PostgreSQL database URL
                   Format: 'postgresql://user:password@host:port/database'
                   If None, loads from .env file or uses environment variable DATABASE_URL
        """
        if db_url is None:
            # Try to load from .env file in project root
            env_file = Path(__file__).parent.parent / '.env'
            if env_file.exists():
                # Load .env file manually (python-dotenv not installed)
                with open(env_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            os.environ[key.strip()] = value.strip()

            # Now get DATABASE_URL from environment
            db_url = os.getenv(
                'DATABASE_URL',
                'postgresql://mdvrp:mdvrp@localhost:5432/mdvrp'
            )

        self.engine = create_engine(db_url, pool_size=10, max_overflow=20)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def get_session(self):
        """
        Get new database session.

        Returns:
            SQLAlchemy session object
        """
        return self.SessionLocal()

    def initialize_schema(self, schema_sql_path: str):
        """
        Initialize database schema from SQL file.

        Args:
            schema_sql_path: Path to SQL file with CREATE TABLE statements

        Raises:
            FileNotFoundError: If schema file not found
            Exception: If SQL execution fails
        """
        if not os.path.exists(schema_sql_path):
            raise FileNotFoundError(f"Schema file not found: {schema_sql_path}")

        with open(schema_sql_path, 'r') as f:
            schema_sql = f.read()

        with self.engine.begin() as conn:
            conn.execute(text(schema_sql))

    def test_connection(self) -> bool:
        """
        Test database connection.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            with self.get_session() as session:
                session.execute(text("SELECT 1"))
            return True
        except Exception as e:
            print(f"Database connection failed: {e}")
            return False
