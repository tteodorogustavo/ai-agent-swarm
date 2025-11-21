"""
Database Initialization Script for Customer Agent.

This script creates the SQLite database schema and populates it with
realistic sample data for testing and demonstration purposes.

Tables:
    - users: Customer profiles and authentication data
    - accounts: Account balances and limits
    - transactions: Transaction history (PIX, transfers, payments)
    - reminders: Follow-up reminders set by customer support
    - payment_limits: Daily/monthly spending limits

Usage:
    # Run this script to initialize/reset the database
    poetry run python data/database/init_db.py

    # Or import and call programmatically
    from data.database.init_db import initialize_database
    initialize_database()
"""
import logging
import sqlite3
from datetime import datetime
from datetime import timedelta
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_db_path() -> Path:
    """Get the path to the database file."""
    project_root = Path(__file__).parent.parent.parent
    db_path = project_root / "data" / "database" / "customers.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return db_path


def initialize_database(db_path: Path = None) -> None:
    """
    Create database schema and populate with sample data.

    Args:
        db_path (Path, optional): Custom database path. Uses default if None.
    """
    if db_path is None:
        db_path = get_db_path()

    logger.info(f"Initializing database at: {db_path}")

    # Remove existing database to start fresh
    if db_path.exists():
        db_path.unlink()
        logger.info("Removed existing database")

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    try:
        # ===========================
        # 1. CREATE TABLES
        # ===========================

        logger.info("Creating tables...")

        # Users table: Customer profiles
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                phone TEXT,
                cpf TEXT UNIQUE,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                last_login TEXT,
                account_type TEXT DEFAULT 'individual'
            )
        """
        )

        # Accounts table: Balances and limits
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS accounts (
                account_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                balance REAL NOT NULL DEFAULT 0.0,
                currency TEXT DEFAULT 'BRL',
                daily_limit REAL DEFAULT 5000.0,
                monthly_limit REAL DEFAULT 50000.0,
                overdraft_enabled INTEGER DEFAULT 0,
                overdraft_limit REAL DEFAULT 0.0,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """
        )

        # Transactions table: Payment history
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
                transaction_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                type TEXT NOT NULL,
                amount REAL NOT NULL,
                status TEXT NOT NULL,
                description TEXT,
                recipient_name TEXT,
                recipient_cpf TEXT,
                error_code TEXT,
                error_message TEXT,
                created_at TEXT NOT NULL,
                completed_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """
        )

        # Reminders table: Follow-up actions
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS reminders (
                reminder_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                message TEXT NOT NULL,
                priority TEXT DEFAULT 'normal',
                status TEXT DEFAULT 'pending',
                created_at TEXT NOT NULL,
                due_date TEXT,
                completed_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """
        )

        # Payment limits tracking
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS payment_limits (
                limit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                period_type TEXT NOT NULL,
                limit_amount REAL NOT NULL,
                spent_amount REAL DEFAULT 0.0,
                period_start TEXT NOT NULL,
                period_end TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """
        )

        # Create indexes for performance
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_transactions_user ON transactions(user_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_transactions_created ON transactions(created_at)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_reminders_user ON reminders(user_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_accounts_user ON accounts(user_id)"
        )

        # ===========================
        # 2. INSERT SAMPLE DATA
        # ===========================

        logger.info("Inserting sample data...")

        # Sample users
        users_data = [
            (
                "client789",
                "Teodoro Gustavo",
                "teodoro@example.com",
                "+55 11 98765-4321",
                "123.456.789-00",
                "active",
                "2024-01-15 10:00:00",
                "2025-11-18 09:30:00",
                "individual",
            ),
            (
                "client123",
                "Claudio Silva",
                "claudio@example.com",
                "+55 11 91234-5678",
                "987.654.321-00",
                "blocked",
                "2024-03-20 14:30:00",
                "2025-11-10 08:15:00",
                "individual",
            ),
            (
                "client456",
                "Maria Santos",
                "maria@example.com",
                "+55 21 99876-5432",
                "456.789.123-00",
                "active",
                "2024-06-01 16:45:00",
                "2025-11-17 20:00:00",
                "business",
            ),
            (
                "client999",
                "João Oliveira",
                "joao@example.com",
                "+55 31 98888-7777",
                "111.222.333-44",
                "suspended",
                "2023-12-10 11:00:00",
                "2025-10-05 10:00:00",
                "individual",
            ),
        ]

        cursor.executemany(
            """
            INSERT INTO users (user_id, name, email, phone, cpf, status, created_at, last_login, account_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            users_data,
        )

        # Sample accounts
        accounts_data = [
            ("client789", 1507.50, "BRL", 5000.0, 50000.0, 0, 0.0),
            ("client123", 0.00, "BRL", 1000.0, 10000.0, 0, 0.0),
            ("client456", 25340.80, "BRL", 10000.0, 100000.0, 1, 5000.0),
            ("client999", 450.20, "BRL", 2000.0, 20000.0, 0, 0.0),
        ]

        cursor.executemany(
            """
            INSERT INTO accounts (user_id, balance, currency, daily_limit, monthly_limit, overdraft_enabled, overdraft_limit)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            accounts_data,
        )

        # Sample transactions for client789 (Teodoro)
        now = datetime.now()
        transactions_data = [
            # Recent failed transfer (insufficient funds)
            (
                "txn_abc_001",
                "client789",
                "transfer",
                2000.00,
                "failed",
                "Transferência para conta poupança",
                "Maria Santos",
                "456.789.123-00",
                "ERR_51",
                "Saldo insuficiente",
                (now - timedelta(hours=2)).isoformat(),
                None,
            ),
            # Successful PIX today
            (
                "txn_abc_002",
                "client789",
                "pix",
                150.00,
                "completed",
                "PIX para João",
                "João Oliveira",
                "111.222.333-44",
                None,
                None,
                (now - timedelta(hours=5)).isoformat(),
                (now - timedelta(hours=5, minutes=-1)).isoformat(),
            ),
            # Payment yesterday
            (
                "txn_abc_003",
                "client789",
                "payment",
                89.90,
                "completed",
                "Pagamento de conta de luz",
                "Eletropaulo",
                None,
                None,
                None,
                (now - timedelta(days=1)).isoformat(),
                (now - timedelta(days=1, minutes=-2)).isoformat(),
            ),
            # Pending transfer
            (
                "txn_abc_004",
                "client789",
                "transfer",
                500.00,
                "pending",
                "TED para outro banco",
                "Claudio Silva",
                "987.654.321-00",
                None,
                None,
                (now - timedelta(minutes=30)).isoformat(),
                None,
            ),
            # Old successful PIX (1 week ago)
            (
                "txn_abc_005",
                "client789",
                "pix",
                250.00,
                "completed",
                "PIX para aluguel",
                "Imobiliária XYZ",
                None,
                None,
                None,
                (now - timedelta(days=7)).isoformat(),
                (now - timedelta(days=7, minutes=-1)).isoformat(),
            ),
        ]

        # Transactions for client123 (Claudio - blocked account)
        transactions_data.extend(
            [
                (
                    "txn_xyz_001",
                    "client123",
                    "transfer",
                    1000.00,
                    "failed",
                    "Tentativa de saque",
                    None,
                    None,
                    "ERR_BLOCKED",
                    "Conta bloqueada por segurança",
                    (now - timedelta(days=3)).isoformat(),
                    None,
                ),
                (
                    "txn_xyz_002",
                    "client123",
                    "pix",
                    50.00,
                    "failed",
                    "PIX recusado",
                    "João Oliveira",
                    "111.222.333-44",
                    "ERR_BLOCKED",
                    "Conta bloqueada",
                    (now - timedelta(days=2)).isoformat(),
                    None,
                ),
            ]
        )

        # Transactions for client456 (Maria - business account)
        transactions_data.extend(
            [
                (
                    "txn_def_001",
                    "client456",
                    "payment",
                    5000.00,
                    "completed",
                    "Pagamento de fornecedor",
                    "Fornecedor ABC Ltda",
                    None,
                    None,
                    None,
                    (now - timedelta(hours=10)).isoformat(),
                    (now - timedelta(hours=10, minutes=-3)).isoformat(),
                ),
                (
                    "txn_def_002",
                    "client456",
                    "pix",
                    1200.00,
                    "completed",
                    "PIX para funcionário",
                    "Carlos Souza",
                    "222.333.444-55",
                    None,
                    None,
                    (now - timedelta(days=1)).isoformat(),
                    (now - timedelta(days=1, minutes=-1)).isoformat(),
                ),
                (
                    "txn_def_003",
                    "client456",
                    "transfer",
                    15000.00,
                    "completed",
                    "Transferência entre contas",
                    None,
                    None,
                    None,
                    None,
                    (now - timedelta(days=5)).isoformat(),
                    (now - timedelta(days=5, minutes=-5)).isoformat(),
                ),
            ]
        )

        cursor.executemany(
            """
            INSERT INTO transactions (transaction_id, user_id, type, amount, status, description, recipient_name, recipient_cpf, error_code, error_message, created_at, completed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            transactions_data,
        )

        # Sample reminders
        reminders_data = [
            (
                "client789",
                "Verificar documento pendente para aumento de limite",
                "high",
                "pending",
                (now - timedelta(days=1)).isoformat(),
                (now + timedelta(days=2)).isoformat(),
                None,
            ),
            (
                "client123",
                "Entrar em contato para resolver bloqueio da conta",
                "urgent",
                "pending",
                (now - timedelta(days=3)).isoformat(),
                (now + timedelta(days=1)).isoformat(),
                None,
            ),
            (
                "client456",
                "Revisar limites de transação para conta business",
                "normal",
                "completed",
                (now - timedelta(days=10)).isoformat(),
                (now - timedelta(days=5)).isoformat(),
                (now - timedelta(days=6)).isoformat(),
            ),
        ]

        cursor.executemany(
            """
            INSERT INTO reminders (user_id, message, priority, status, created_at, due_date, completed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            reminders_data,
        )

        # Payment limits (current period)
        limits_data = [
            (
                "client789",
                "daily",
                5000.0,
                739.90,
                now.strftime("%Y-%m-%d 00:00:00"),
                (now + timedelta(days=1)).strftime("%Y-%m-%d 00:00:00"),
            ),
            (
                "client789",
                "monthly",
                50000.0,
                3240.80,
                now.replace(day=1).strftime("%Y-%m-%d 00:00:00"),
                (now.replace(day=1) + timedelta(days=32))
                .replace(day=1)
                .strftime("%Y-%m-%d 00:00:00"),
            ),
            (
                "client456",
                "daily",
                10000.0,
                6200.0,
                now.strftime("%Y-%m-%d 00:00:00"),
                (now + timedelta(days=1)).strftime("%Y-%m-%d 00:00:00"),
            ),
            (
                "client456",
                "monthly",
                100000.0,
                45300.0,
                now.replace(day=1).strftime("%Y-%m-%d 00:00:00"),
                (now.replace(day=1) + timedelta(days=32))
                .replace(day=1)
                .strftime("%Y-%m-%d 00:00:00"),
            ),
        ]

        cursor.executemany(
            """
            INSERT INTO payment_limits (user_id, period_type, limit_amount, spent_amount, period_start, period_end)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            limits_data,
        )

        conn.commit()
        logger.info("✅ Database initialized successfully!")
        logger.info(f"📍 Location: {db_path}")
        logger.info(f"👥 Created {len(users_data)} users")
        logger.info(f"💰 Created {len(accounts_data)} accounts")
        logger.info(f"📊 Created {len(transactions_data)} transactions")
        logger.info(f"🔔 Created {len(reminders_data)} reminders")
        logger.info(f"🚦 Created {len(limits_data)} payment limits")

    except sqlite3.Error as e:
        logger.error(f"❌ Database initialization failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    initialize_database()
    print("\n✅ Database ready for use!")
    print("You can now run the Customer Agent with real database tools.")
