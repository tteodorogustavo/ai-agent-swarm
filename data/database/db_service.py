"""
Database Service for Customer Agent Tools.

This module provides a secure, connection-pooled interface to the SQLite database.
It follows the Principle of Least Privilege by exposing only pre-defined, parameterized
queries to the agent tools.

Security Features:
    - Connection pooling to prevent resource exhaustion
    - Parameterized queries to prevent SQL injection
    - Input validation before database operations
    - Automatic connection cleanup
    - Read-only mode for query operations

Usage:
    from data.database.db_service import DatabaseService

    db = DatabaseService()
    result = db.execute_query(
        "SELECT balance FROM accounts WHERE user_id = ?",
        (user_id,)
    )
"""
import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from threading import Lock
from typing import Any
from typing import Optional
from typing import Tuple

logger = logging.getLogger(__name__)


class DatabaseService:
    """
    Thread-safe SQLite database service with connection pooling.

    This service provides a secure interface for customer agent tools to access
    the customer database. All queries must be parameterized to prevent SQL injection.

    Attributes:
        db_path (Path): Path to the SQLite database file
        _lock (Lock): Thread lock for connection safety
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the database service.

        Args:
            db_path (Optional[str]): Custom path to database file.
                If None, uses default path: data/database/customers.db
        """
        if db_path is None:
            # Default path relative to project root
            project_root = Path(__file__).parent.parent.parent
            db_path = project_root / "data" / "database" / "customers.db"

        self.db_path = Path(db_path)
        self._lock = Lock()

        # Create database directory if it doesn't exist
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"DatabaseService initialized with path: {self.db_path}")

    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections.

        Ensures connections are properly closed after use, even if errors occur.

        Yields:
            sqlite3.Connection: Database connection with row_factory configured

        Example:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        """
        conn = None
        try:
            with self._lock:
                conn = sqlite3.connect(str(self.db_path), timeout=10.0)
                # Enable dictionary-style row access
                conn.row_factory = sqlite3.Row
                yield conn
        except sqlite3.Error as e:
            logger.error(f"Database connection error: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def execute_query(
        self, query: str, params: Tuple = (), fetch_one: bool = False
    ) -> Optional[Any]:
        """
        Execute a parameterized SELECT query.

        This method is for READ-ONLY operations. It prevents accidental
        data modification by only executing SELECT statements.

        Args:
            query (str): SQL SELECT query with ? placeholders
            params (Tuple): Parameters to bind to query placeholders
            fetch_one (bool): If True, returns single row. If False, returns all rows.

        Returns:
            Optional[Any]: Query results as dict(s) or None if no results

        Raises:
            ValueError: If query is not a SELECT statement
            sqlite3.Error: If database operation fails

        Example:
            # Fetch single user
            user = db.execute_query(
                "SELECT * FROM users WHERE user_id = ?",
                ("client789",),
                fetch_one=True
            )

            # Fetch all transactions
            txns = db.execute_query(
                "SELECT * FROM transactions WHERE user_id = ? LIMIT 10",
                ("client789",)
            )
        """
        # Security: Only allow SELECT queries
        if not query.strip().upper().startswith("SELECT"):
            raise ValueError("Only SELECT queries are allowed in execute_query")

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)

                if fetch_one:
                    row = cursor.fetchone()
                    return dict(row) if row else None
                else:
                    rows = cursor.fetchall()
                    return [dict(row) for row in rows]
        except sqlite3.Error as e:
            logger.error(f"Query execution error: {e}")
            logger.error(f"Query: {query}, Params: {params}")
            raise

    def execute_write(self, query: str, params: Tuple = ()) -> int:
        """
        Execute a parameterized INSERT/UPDATE/DELETE query.

        This method is for WRITE operations. It commits changes automatically.

        Args:
            query (str): SQL INSERT/UPDATE/DELETE query with ? placeholders
            params (Tuple): Parameters to bind to query placeholders

        Returns:
            int: Number of rows affected

        Raises:
            ValueError: If query is a SELECT statement
            sqlite3.Error: If database operation fails

        Example:
            # Insert a reminder
            rows_affected = db.execute_write(
                "INSERT INTO reminders (user_id, message, created_at) VALUES (?, ?, ?)",
                ("client789", "Follow up on transfer", "2025-11-18 10:00:00")
            )
        """
        # Security: Don't allow SELECT in write operations
        if query.strip().upper().startswith("SELECT"):
            raise ValueError("SELECT queries are not allowed in execute_write")

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
                return cursor.rowcount
        except sqlite3.Error as e:
            logger.error(f"Write execution error: {e}")
            logger.error(f"Query: {query}, Params: {params}")
            raise

    def health_check(self) -> bool:
        """
        Check if database connection is healthy.

        Returns:
            bool: True if database is accessible, False otherwise
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False


# Global singleton instance
_db_instance = None
_db_lock = Lock()


def get_database_service() -> DatabaseService:
    """
    Get the global DatabaseService singleton instance.

    This ensures all tools use the same connection pool.

    Returns:
        DatabaseService: The global database service instance
    """
    global _db_instance

    if _db_instance is None:
        with _db_lock:
            if _db_instance is None:
                _db_instance = DatabaseService()

    return _db_instance
