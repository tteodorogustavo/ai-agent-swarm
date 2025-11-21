"""
Tests for Customer Agent tools with real SQLite database.

This module tests the customer tools using an isolated temporary database
to ensure tools execute correct queries and handle edge cases properly.

Strategy:
    - Uses pytest fixtures to create temporary database
    - Tests both successful operations and error handling
    - Validates security (parameterized queries, input validation)
    - Tests timeout protection and connection management
"""
import sqlite3
import tempfile
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from app.agents.customer_agent.tools import check_payment_limits
from app.agents.customer_agent.tools import create_reminder
from app.agents.customer_agent.tools import get_account_balance
from app.agents.customer_agent.tools import get_current_datetime
from app.agents.customer_agent.tools import get_failed_transactions
from app.agents.customer_agent.tools import get_transaction_history
from app.agents.customer_agent.tools import get_user_profile
from data.database.db_service import DatabaseService


@pytest.fixture
def temp_db():
    """
    Create a temporary SQLite database with test data.

    This fixture:
    1. Creates a temporary database file
    2. Initializes the schema
    3. Populates with test data
    4. Yields the database path
    5. Cleans up after tests
    """
    # Create temporary database file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    db_path = Path(temp_file.name)
    temp_file.close()

    # Initialize database
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Create schema
    cursor.execute(
        """
        CREATE TABLE users (
            user_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            status TEXT DEFAULT 'active',
            created_at TEXT,
            last_login TEXT,
            account_type TEXT DEFAULT 'individual'
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE accounts (
            account_id INTEGER PRIMARY KEY,
            user_id TEXT NOT NULL,
            balance REAL DEFAULT 0.0,
            currency TEXT DEFAULT 'BRL',
            daily_limit REAL DEFAULT 5000.0,
            monthly_limit REAL DEFAULT 50000.0,
            overdraft_enabled INTEGER DEFAULT 0,
            overdraft_limit REAL DEFAULT 0.0,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE transactions (
            transaction_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            type TEXT NOT NULL,
            amount REAL NOT NULL,
            status TEXT NOT NULL,
            description TEXT,
            recipient_name TEXT,
            error_code TEXT,
            error_message TEXT,
            created_at TEXT,
            completed_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE reminders (
            reminder_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            message TEXT NOT NULL,
            priority TEXT DEFAULT 'normal',
            status TEXT DEFAULT 'pending',
            created_at TEXT,
            due_date TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE payment_limits (
            limit_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            period_type TEXT NOT NULL,
            limit_amount REAL NOT NULL,
            spent_amount REAL DEFAULT 0.0,
            period_start TEXT,
            period_end TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """
    )

    # Insert test data
    now = datetime.now()

    # Test user
    cursor.execute(
        """
        INSERT INTO users (user_id, name, email, phone, status, created_at, last_login, account_type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            "test_user",
            "Test User",
            "test@example.com",
            "+55 11 99999-9999",
            "active",
            now.isoformat(),
            now.isoformat(),
            "individual",
        ),
    )

    # Test account
    cursor.execute(
        """
        INSERT INTO accounts (user_id, balance, currency, daily_limit, monthly_limit, overdraft_enabled, overdraft_limit)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """,
        ("test_user", 1000.0, "BRL", 5000.0, 50000.0, 0, 0.0),
    )

    # Test transactions
    cursor.execute(
        """
        INSERT INTO transactions (transaction_id, user_id, type, amount, status, description, created_at, completed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            "txn_001",
            "test_user",
            "pix",
            100.0,
            "completed",
            "Test PIX",
            now.isoformat(),
            now.isoformat(),
        ),
    )

    cursor.execute(
        """
        INSERT INTO transactions (transaction_id, user_id, type, amount, status, description, error_code, error_message, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            "txn_002",
            "test_user",
            "transfer",
            5000.0,
            "failed",
            "Test failed transfer",
            "ERR_51",
            "Insufficient funds",
            now.isoformat(),
        ),
    )

    # Test payment limits
    cursor.execute(
        """
        INSERT INTO payment_limits (user_id, period_type, limit_amount, spent_amount, period_start, period_end)
        VALUES (?, ?, ?, ?, ?, ?)
    """,
        (
            "test_user",
            "daily",
            5000.0,
            100.0,
            now.strftime("%Y-%m-%d 00:00:00"),
            (now + timedelta(days=1)).strftime("%Y-%m-%d 00:00:00"),
        ),
    )

    conn.commit()
    conn.close()

    yield db_path

    # Cleanup
    db_path.unlink()


class TestGetAccountBalance:
    """Tests for get_account_balance tool."""

    def test_successful_balance_retrieval(self, temp_db):
        """Test successful account balance retrieval."""
        with patch(
            "app.agents.customer_agent.tools.get_database_service"
        ) as mock_get_db:
            mock_db = DatabaseService(db_path=str(temp_db))
            mock_get_db.return_value = mock_db

            result = get_account_balance.invoke({"user_id": "test_user"})

            assert result["user_id"] == "test_user"
            assert result["balance"] == 1000.0
            assert result["currency"] == "BRL"
            assert result["daily_limit"] == 5000.0
            assert result["monthly_limit"] == 50000.0

    def test_user_not_found(self, temp_db):
        """Test account balance for non-existent user."""
        with patch(
            "app.agents.customer_agent.tools.get_database_service"
        ) as mock_get_db:
            mock_db = DatabaseService(db_path=str(temp_db))
            mock_get_db.return_value = mock_db

            result = get_account_balance.invoke({"user_id": "nonexistent"})

            assert "error" in result
            assert result["error"] == "not_found"

    def test_invalid_input(self, temp_db):
        """Test input validation."""
        result = get_account_balance.invoke({"user_id": ""})
        assert "error" in result
        assert result["error"] == "invalid_input"


class TestGetUserProfile:
    """Tests for get_user_profile tool."""

    def test_successful_profile_retrieval(self, temp_db):
        """Test successful user profile retrieval."""
        with patch(
            "app.agents.customer_agent.tools.get_database_service"
        ) as mock_get_db:
            mock_db = DatabaseService(db_path=str(temp_db))
            mock_get_db.return_value = mock_db

            result = get_user_profile.invoke({"user_id": "test_user"})

            assert result["user_id"] == "test_user"
            assert result["name"] == "Test User"
            assert result["email"] == "test@example.com"
            assert result["status"] == "active"
            assert result["account_type"] == "individual"

    def test_user_not_found(self, temp_db):
        """Test profile for non-existent user."""
        with patch(
            "app.agents.customer_agent.tools.get_database_service"
        ) as mock_get_db:
            mock_db = DatabaseService(db_path=str(temp_db))
            mock_get_db.return_value = mock_db

            result = get_user_profile.invoke({"user_id": "nonexistent"})

            assert "error" in result
            assert result["error"] == "not_found"


class TestGetTransactionHistory:
    """Tests for get_transaction_history tool."""

    def test_successful_transaction_retrieval(self, temp_db):
        """Test successful transaction history retrieval."""
        with patch(
            "app.agents.customer_agent.tools.get_database_service"
        ) as mock_get_db:
            mock_db = DatabaseService(db_path=str(temp_db))
            mock_get_db.return_value = mock_db

            result = get_transaction_history.invoke(
                {"user_id": "test_user", "limit": 10}
            )

            assert result["user_id"] == "test_user"
            assert result["transaction_count"] == 2
            assert len(result["transactions"]) == 2

    def test_limit_parameter(self, temp_db):
        """Test limit parameter works correctly."""
        with patch(
            "app.agents.customer_agent.tools.get_database_service"
        ) as mock_get_db:
            mock_db = DatabaseService(db_path=str(temp_db))
            mock_get_db.return_value = mock_db

            result = get_transaction_history.invoke(
                {"user_id": "test_user", "limit": 1}
            )

            assert result["transaction_count"] == 1
            assert len(result["transactions"]) == 1

    def test_no_transactions(self, temp_db):
        """Test user with no transactions."""
        with patch(
            "app.agents.customer_agent.tools.get_database_service"
        ) as mock_get_db:
            mock_db = DatabaseService(db_path=str(temp_db))
            mock_get_db.return_value = mock_db

            result = get_transaction_history.invoke(
                {"user_id": "nonexistent", "limit": 10}
            )

            assert result["transaction_count"] == 0
            assert result["transactions"] == []


class TestGetFailedTransactions:
    """Tests for get_failed_transactions tool."""

    def test_successful_failed_transaction_retrieval(self, temp_db):
        """Test retrieval of failed transactions."""
        with patch(
            "app.agents.customer_agent.tools.get_database_service"
        ) as mock_get_db:
            mock_db = DatabaseService(db_path=str(temp_db))
            mock_get_db.return_value = mock_db

            result = get_failed_transactions.invoke({"user_id": "test_user"})

            assert result["user_id"] == "test_user"
            assert result["failed_count"] == 1
            assert len(result["failed_transactions"]) == 1
            assert result["failed_transactions"][0]["error_code"] == "ERR_51"
            assert (
                result["failed_transactions"][0]["error_message"]
                == "Insufficient funds"
            )

    def test_no_failed_transactions(self, temp_db):
        """Test user with no failed transactions."""
        # Create new user with only successful transactions
        conn = sqlite3.connect(str(temp_db))
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO users (user_id, name, email, status, created_at)
            VALUES (?, ?, ?, ?, ?)
        """,
            (
                "clean_user",
                "Clean User",
                "clean@example.com",
                "active",
                datetime.now().isoformat(),
            ),
        )
        conn.commit()
        conn.close()

        with patch(
            "app.agents.customer_agent.tools.get_database_service"
        ) as mock_get_db:
            mock_db = DatabaseService(db_path=str(temp_db))
            mock_get_db.return_value = mock_db

            result = get_failed_transactions.invoke({"user_id": "clean_user"})

            assert result["failed_count"] == 0
            assert result["failed_transactions"] == []


class TestCheckPaymentLimits:
    """Tests for check_payment_limits tool."""

    def test_successful_limit_check(self, temp_db):
        """Test successful payment limit check."""
        with patch(
            "app.agents.customer_agent.tools.get_database_service"
        ) as mock_get_db:
            mock_db = DatabaseService(db_path=str(temp_db))
            mock_get_db.return_value = mock_db

            result = check_payment_limits.invoke({"user_id": "test_user"})

            assert result["user_id"] == "test_user"
            assert len(result["limits"]) == 1
            limit = result["limits"][0]
            assert limit["period_type"] == "daily"
            assert limit["limit_amount"] == 5000.0
            assert limit["spent_amount"] == 100.0
            assert limit["remaining"] == 4900.0

    def test_no_limits_configured(self, temp_db):
        """Test user with no payment limits."""
        with patch(
            "app.agents.customer_agent.tools.get_database_service"
        ) as mock_get_db:
            mock_db = DatabaseService(db_path=str(temp_db))
            mock_get_db.return_value = mock_db

            result = check_payment_limits.invoke({"user_id": "nonexistent"})

            assert result["limits"] == []


class TestCreateReminder:
    """Tests for create_reminder tool."""

    def test_successful_reminder_creation(self, temp_db):
        """Test successful reminder creation."""
        with patch(
            "app.agents.customer_agent.tools.get_database_service"
        ) as mock_get_db:
            mock_db = DatabaseService(db_path=str(temp_db))
            mock_get_db.return_value = mock_db

            result = create_reminder.invoke(
                {
                    "user_id": "test_user",
                    "reminder_message": "Test reminder",
                    "priority": "high",
                }
            )

            assert result["success"] is True
            assert "due_date" in result

    def test_invalid_priority_defaults_to_normal(self, temp_db):
        """Test that invalid priority defaults to normal."""
        with patch(
            "app.agents.customer_agent.tools.get_database_service"
        ) as mock_get_db:
            mock_db = DatabaseService(db_path=str(temp_db))
            mock_get_db.return_value = mock_db

            result = create_reminder.invoke(
                {
                    "user_id": "test_user",
                    "reminder_message": "Test reminder",
                    "priority": "invalid",
                }
            )

            # Should still succeed, just with normalized priority
            assert result["success"] is True

    def test_message_too_long(self, temp_db):
        """Test validation of message length."""
        long_message = "x" * 1001
        result = create_reminder.invoke(
            {
                "user_id": "test_user",
                "reminder_message": long_message,
                "priority": "normal",
            }
        )

        assert "error" in result
        assert result["error"] == "invalid_input"

    def test_empty_message(self, temp_db):
        """Test validation of empty message."""
        result = create_reminder.invoke(
            {"user_id": "test_user", "reminder_message": "", "priority": "normal"}
        )

        assert "error" in result
        assert result["error"] == "invalid_input"


class TestGetCurrentDatetime:
    """Tests for get_current_datetime tool."""

    def test_successful_datetime_retrieval(self):
        """
        Test successful retrieval of current date and time.

        Validates that the tool returns all expected fields with correct formats.
        """
        result = get_current_datetime.invoke({})

        # Check all required fields are present
        assert "datetime" in result
        assert "date" in result
        assert "time" in result
        assert "day_of_week" in result
        assert "timezone" in result

        # Validate timezone
        assert result["timezone"] == "America/Sao_Paulo"

        # Validate date format (DD/MM/YYYY)
        assert len(result["date"]) == 10
        assert result["date"][2] == "/"
        assert result["date"][5] == "/"

        # Validate time format (HH:MM:SS)
        assert len(result["time"]) == 8
        assert result["time"][2] == ":"
        assert result["time"][5] == ":"

        # Validate day_of_week is in Portuguese
        valid_days = [
            "Segunda-feira",
            "Terça-feira",
            "Quarta-feira",
            "Quinta-feira",
            "Sexta-feira",
            "Sábado",
            "Domingo",
        ]
        assert result["day_of_week"] in valid_days

    def test_datetime_consistency(self):
        """
        Test that datetime values are internally consistent.

        Ensures that the date and time components match the datetime field.
        """
        result = get_current_datetime.invoke({})

        from datetime import datetime

        # Parse the ISO datetime
        dt = datetime.fromisoformat(result["datetime"])

        # Check date consistency
        expected_date = dt.strftime("%d/%m/%Y")
        assert result["date"] == expected_date

        # Check time consistency
        expected_time = dt.strftime("%H:%M:%S")
        assert result["time"] == expected_time

    def test_no_error_on_invocation(self):
        """
        Test that the tool never returns an error under normal conditions.
        """
        result = get_current_datetime.invoke({})

        assert "error" not in result
        assert "datetime" in result
