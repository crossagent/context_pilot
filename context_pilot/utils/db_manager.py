import sqlite3
import os
import logging
from contextlib import contextmanager
from datetime import datetime

# Adjust import based on where this is running vs where config is located
# Try relative import first, fallback to absolute path trick if needed (common in this codebase's scripts)
try:
    from context_pilot.scripts.rag_config import RagConfig
except ImportError:
    import sys
    # Add project root to path
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
    from context_pilot.scripts.rag_config import RagConfig

logger = logging.getLogger(__name__)

class DBManager:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.path.join(RagConfig.LOCAL_DATA_DIR, RagConfig.DB_FILENAME)
        self._ensure_dir()

    def _ensure_dir(self):
        dirname = os.path.dirname(self.db_path)
        if dirname:
            os.makedirs(dirname, exist_ok=True)

    def init_db(self):
        """Initializes the database using WAL mode and creates tables if they don't exist."""
        try:
            with self.get_connection() as conn:
                # Enable Write-Ahead Logging for better concurrency
                conn.execute("PRAGMA journal_mode=WAL;")
                
                # Create table with structured columns
                conn.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_entries (
                    id TEXT PRIMARY KEY,
                    intent TEXT,
                    problem_context TEXT,
                    root_cause TEXT,
                    solution_steps TEXT,
                    evidence TEXT,
                    tags TEXT,
                    contributor TEXT,
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP
                );
                """)
                logger.info(f"Database initialized at {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    @contextmanager
    def get_connection(self):
        """Yields a SQLite connection context manager."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Access columns by name
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

# Singleton-ish usage for convenience, assuming standard config usually
default_db_manager = DBManager()
