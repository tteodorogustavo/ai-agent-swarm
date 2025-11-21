"""
Customer Agent Tools - Secure Database Interface.

This module implements the "CERTO" (correct) approach to database access for AI agents,
following the Principle of Least Privilege. Instead of giving the LLM arbitrary SQL
access (Text2SQL - which is dangerous), we provide pre-defined, parameterized tool
functions that execute safe, optimized queries.

Security Architecture:
    1. **No Direct SQL Access:** LLM cannot write SQL queries
    2. **Parameterized Queries:** All queries use ? placeholders to prevent SQL injection
    3. **Input Validation:** All inputs are validated before database operations
    4. **Error Handling:** Graceful error handling without exposing internal details
    5. **Timeout Protection:** All operations have timeouts to prevent hangs
    6. **Read/Write Separation:** Clear distinction between read and write operations

Tools Available:
    - get_account_balance: Fetch current account balance and limits
    - get_user_profile: Retrieve user information and status
    - get_transaction_history: Get recent transaction records
    - check_payment_limits: Verify spending limits for the current period
    - get_current_datetime: Get current date and time information
    - create_reminder: Create follow-up reminders for customer support
    - get_failed_transactions: Retrieve failed transactions with error details

Database Schema:
    See data/database/init_db.py for complete schema definition.

Usage:
    These tools are designed to be called by the CustomerAgent LLM.
    The agent analyzes the user's question and selects appropriate tools.

Example:
    # LLM decides to check balance
    result = get_account_balance("client789")
    # Returns: {"user_id": "client789", "balance": 1507.50, "currency": "BRL", ...}
"""
import logging
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from datetime import datetime
from datetime import timedelta
from typing import Any
from typing import Dict

from langchain_core.tools import tool

from data.database.db_service import get_database_service
# Import secure database service

logger = logging.getLogger(__name__)


# ============================================================================
# READ TOOLS (Query Operations)
# ============================================================================


@tool
def get_account_balance(user_id: str) -> Dict[str, Any]:
    """
    Retrieve the current account balance, currency, and spending limits for a user.

    Use this tool when the customer asks about:
    - Their current balance
    - How much money they have available
    - Their account limits (daily/monthly)
    - Overdraft status

    Args:
        user_id (str): The unique identifier of the customer (e.g., "client789")

    Returns:
        Dict[str, Any]: Account information containing:
            - user_id: Customer identifier
            - balance: Current account balance
            - currency: Currency code (e.g., "BRL")
            - daily_limit: Maximum daily spending limit
            - monthly_limit: Maximum monthly spending limit
            - overdraft_enabled: Whether overdraft is available (0 or 1)
            - overdraft_limit: Maximum overdraft amount

    Example:
        >>> get_account_balance("client789")
        {
            "user_id": "client789",
            "balance": 1507.50,
            "currency": "BRL",
            "daily_limit": 5000.0,
            "monthly_limit": 50000.0,
            "overdraft_enabled": 0,
            "overdraft_limit": 0.0
        }
    """
    logger.info(f"[TOOL] get_account_balance called for user_id: {user_id}")

    # Input validation
    if not user_id or not isinstance(user_id, str):
        logger.warning("Invalid user_id provided to get_account_balance")
        return {
            "error": "invalid_input",
            "message": "user_id must be a non-empty string",
        }

    try:
        db = get_database_service()

        # Pre-structured, parameterized query (SECURE)
        query = """
            SELECT
                a.user_id,
                a.balance,
                a.currency,
                a.daily_limit,
                a.monthly_limit,
                a.overdraft_enabled,
                a.overdraft_limit
            FROM accounts a
            WHERE a.user_id = ?
        """

        # Execute with timeout protection
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(db.execute_query, query, (user_id,), True)
            result = future.result(timeout=3.0)

        if not result:
            logger.info(f"No account found for user_id: {user_id}")
            return {
                "error": "not_found",
                "message": f"No account found for user {user_id}",
            }

        logger.info(
            f"Successfully retrieved balance for {user_id}: {result['balance']} {result['currency']}"
        )
        return result

    except FuturesTimeoutError:
        logger.error(f"get_account_balance timed out for user_id: {user_id}")
        return {"error": "timeout", "message": "Database query timed out"}
    except sqlite3.Error as e:
        logger.error(f"Database error in get_account_balance: {e}")
        return {
            "error": "database_error",
            "message": "Failed to retrieve account balance",
        }
    except Exception as e:
        logger.exception(f"Unexpected error in get_account_balance: {e}")
        return {"error": "internal_error", "message": "An unexpected error occurred"}


@tool
def get_user_profile(user_id: str) -> Dict[str, Any]:
    """
    Retrieve user profile information including name, contact details, and account status.

    Use this tool when the customer asks about:
    - Their account status (active, blocked, suspended)
    - Their personal information
    - When they created their account
    - Their last login time
    - Account type (individual vs business)

    Args:
        user_id (str): The unique identifier of the customer

    Returns:
        Dict[str, Any]: User profile containing:
            - user_id: Customer identifier
            - name: Customer's full name
            - email: Registered email address
            - phone: Phone number
            - status: Account status (active, blocked, suspended)
            - created_at: Account creation timestamp
            - last_login: Last login timestamp
            - account_type: Type of account (individual, business)

    Example:
        >>> get_user_profile("client789")
        {
            "user_id": "client789",
            "name": "Teodoro Gustavo",
            "email": "teodoro@example.com",
            "phone": "+55 11 98765-4321",
            "status": "active",
            "created_at": "2024-01-15 10:00:00",
            "last_login": "2025-11-18 09:30:00",
            "account_type": "individual"
        }
    """
    logger.info(f"[TOOL] get_user_profile called for user_id: {user_id}")

    if not user_id or not isinstance(user_id, str):
        return {
            "error": "invalid_input",
            "message": "user_id must be a non-empty string",
        }

    try:
        db = get_database_service()

        # Secure parameterized query
        query = """
            SELECT
                user_id,
                name,
                email,
                phone,
                status,
                created_at,
                last_login,
                account_type
            FROM users
            WHERE user_id = ?
        """

        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(db.execute_query, query, (user_id,), True)
            result = future.result(timeout=3.0)

        if not result:
            logger.info(f"No user found for user_id: {user_id}")
            return {"error": "not_found", "message": f"User {user_id} not found"}

        logger.info(
            f"Successfully retrieved profile for {user_id}: {result['name']} ({result['status']})"
        )
        return result

    except FuturesTimeoutError:
        logger.error(f"get_user_profile timed out for user_id: {user_id}")
        return {"error": "timeout", "message": "Database query timed out"}
    except Exception as e:
        logger.exception(f"Error in get_user_profile: {e}")
        return {"error": "internal_error", "message": "Failed to retrieve user profile"}


@tool
def get_transaction_history(user_id: str, limit: int = 10) -> Dict[str, Any]:
    """
    Retrieve recent transaction history for a user, ordered by most recent first.

    Use this tool when the customer asks about:
    - Recent payments or transfers
    - Transaction history
    - Specific transaction details
    - PIX payments

    Args:
        user_id (str): The unique identifier of the customer
        limit (int): Maximum number of transactions to return (default: 10, max: 50)

    Returns:
        Dict[str, Any]: Transaction history containing:
            - user_id: Customer identifier
            - transaction_count: Number of transactions returned
            - transactions: List of transaction objects with:
                - transaction_id: Unique transaction identifier
                - type: Transaction type (pix, transfer, payment)
                - amount: Transaction amount
                - status: Status (completed, pending, failed)
                - description: Transaction description
                - created_at: When transaction was created
                - completed_at: When transaction was completed (if applicable)

    Example:
        >>> get_transaction_history("client789", limit=5)
        {
            "user_id": "client789",
            "transaction_count": 5,
            "transactions": [
                {
                    "transaction_id": "txn_abc_001",
                    "type": "transfer",
                    "amount": 2000.0,
                    "status": "failed",
                    "description": "Transferência para conta poupança",
                    "created_at": "2025-11-18 07:30:00",
                    "completed_at": null
                },
                ...
            ]
        }
    """
    logger.info(
        f"[TOOL] get_transaction_history called for user_id: {user_id}, limit: {limit}"
    )

    if not user_id or not isinstance(user_id, str):
        return {
            "error": "invalid_input",
            "message": "user_id must be a non-empty string",
        }

    # Validate and cap limit
    if not isinstance(limit, int) or limit < 1:
        limit = 10
    if limit > 50:
        limit = 50

    try:
        db = get_database_service()

        # Secure query with ORDER BY and LIMIT
        query = """
            SELECT
                transaction_id,
                type,
                amount,
                status,
                description,
                recipient_name,
                created_at,
                completed_at
            FROM transactions
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """

        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(db.execute_query, query, (user_id, limit), False)
            transactions = future.result(timeout=5.0)

        if not transactions:
            logger.info(f"No transactions found for user_id: {user_id}")
            return {
                "user_id": user_id,
                "transaction_count": 0,
                "transactions": [],
                "message": "No transactions found",
            }

        logger.info(f"Retrieved {len(transactions)} transactions for {user_id}")
        return {
            "user_id": user_id,
            "transaction_count": len(transactions),
            "transactions": transactions,
        }

    except FuturesTimeoutError:
        logger.error(f"get_transaction_history timed out for user_id: {user_id}")
        return {"error": "timeout", "message": "Database query timed out"}
    except Exception as e:
        logger.exception(f"Error in get_transaction_history: {e}")
        return {
            "error": "internal_error",
            "message": "Failed to retrieve transaction history",
        }


@tool
def get_failed_transactions(user_id: str) -> Dict[str, Any]:
    """
    Retrieve all failed transactions for a user with detailed error information.

    Use this tool specifically when the customer asks:
    - Why did my transfer fail?
    - Why was my payment rejected?
    - What went wrong with my transaction?
    - Show me failed transactions

    Args:
        user_id (str): The unique identifier of the customer

    Returns:
        Dict[str, Any]: Failed transactions containing:
            - user_id: Customer identifier
            - failed_count: Number of failed transactions
            - failed_transactions: List of failed transactions with:
                - transaction_id: Unique identifier
                - type: Transaction type
                - amount: Amount attempted
                - description: Transaction description
                - error_code: Error code (e.g., "ERR_51")
                - error_message: Human-readable error explanation
                - created_at: When the transaction was attempted

    Example:
        >>> get_failed_transactions("client789")
        {
            "user_id": "client789",
            "failed_count": 1,
            "failed_transactions": [
                {
                    "transaction_id": "txn_abc_001",
                    "type": "transfer",
                    "amount": 2000.0,
                    "description": "Transferência para conta poupança",
                    "error_code": "ERR_51",
                    "error_message": "Saldo insuficiente",
                    "created_at": "2025-11-18 07:30:00"
                }
            ]
        }
    """
    logger.info(f"[TOOL] get_failed_transactions called for user_id: {user_id}")

    if not user_id or not isinstance(user_id, str):
        return {
            "error": "invalid_input",
            "message": "user_id must be a non-empty string",
        }

    try:
        db = get_database_service()

        query = """
            SELECT
                transaction_id,
                type,
                amount,
                description,
                recipient_name,
                error_code,
                error_message,
                created_at
            FROM transactions
            WHERE user_id = ? AND status = 'failed'
            ORDER BY created_at DESC
            LIMIT 20
        """

        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(db.execute_query, query, (user_id,), False)
            failed_txns = future.result(timeout=3.0)

        if not failed_txns:
            return {
                "user_id": user_id,
                "failed_count": 0,
                "failed_transactions": [],
                "message": "No failed transactions found",
            }

        logger.info(f"Found {len(failed_txns)} failed transactions for {user_id}")
        return {
            "user_id": user_id,
            "failed_count": len(failed_txns),
            "failed_transactions": failed_txns,
        }

    except FuturesTimeoutError:
        logger.error(f"get_failed_transactions timed out for user_id: {user_id}")
        return {"error": "timeout", "message": "Database query timed out"}
    except Exception as e:
        logger.exception(f"Error in get_failed_transactions: {e}")
        return {
            "error": "internal_error",
            "message": "Failed to retrieve failed transactions",
        }


@tool
def check_payment_limits(user_id: str) -> Dict[str, Any]:
    """
    Check current spending limits and how much has been spent in the current period.

    Use this tool when the customer asks about:
    - Their spending limits
    - How much they can still spend today/this month
    - Why a transaction was blocked
    - Available credit or spending capacity

    Args:
        user_id (str): The unique identifier of the customer

    Returns:
        Dict[str, Any]: Payment limits information containing:
            - user_id: Customer identifier
            - limits: List of limit objects with:
                - period_type: "daily" or "monthly"
                - limit_amount: Total limit for the period
                - spent_amount: Amount already spent
                - remaining: Available spending capacity
                - period_start: When the period started
                - period_end: When the period ends

    Example:
        >>> check_payment_limits("client789")
        {
            "user_id": "client789",
            "limits": [
                {
                    "period_type": "daily",
                    "limit_amount": 5000.0,
                    "spent_amount": 739.90,
                    "remaining": 4260.10,
                    "period_start": "2025-11-18 00:00:00",
                    "period_end": "2025-11-19 00:00:00"
                },
                ...
            ]
        }
    """
    logger.info(f"[TOOL] check_payment_limits called for user_id: {user_id}")

    if not user_id or not isinstance(user_id, str):
        return {
            "error": "invalid_input",
            "message": "user_id must be a non-empty string",
        }

    try:
        db = get_database_service()

        query = """
            SELECT
                period_type,
                limit_amount,
                spent_amount,
                period_start,
                period_end
            FROM payment_limits
            WHERE user_id = ?
            ORDER BY period_type
        """

        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(db.execute_query, query, (user_id,), False)
            limits = future.result(timeout=3.0)

        if not limits:
            return {
                "user_id": user_id,
                "limits": [],
                "message": "No payment limits configured",
            }

        # Calculate remaining amounts
        for limit in limits:
            limit["remaining"] = limit["limit_amount"] - limit["spent_amount"]

        logger.info(f"Retrieved {len(limits)} payment limits for {user_id}")
        return {"user_id": user_id, "limits": limits}

    except FuturesTimeoutError:
        logger.error(f"check_payment_limits timed out for user_id: {user_id}")
        return {"error": "timeout", "message": "Database query timed out"}
    except Exception as e:
        logger.exception(f"Error in check_payment_limits: {e}")
        return {"error": "internal_error", "message": "Failed to check payment limits"}


# ============================================================================
# WRITE TOOLS (Modification Operations)
# ============================================================================


@tool
def get_current_datetime() -> Dict[str, Any]:
    """
    Get the current date and time in Brazilian timezone (America/Sao_Paulo).

    Use this tool when the customer asks about:
    - What time is it?
    - What day is today?
    - Current date and time
    - Business hours context
    - Time-sensitive information

    Returns:
        Dict[str, Any]: Current datetime information containing:
            - datetime: Current date and time in ISO format
            - date: Current date in Brazilian format (DD/MM/YYYY)
            - time: Current time in 24-hour format (HH:MM:SS)
            - day_of_week: Name of the current day in Portuguese
            - timezone: Timezone identifier

    Example:
        >>> get_current_datetime()
        {
            "datetime": "2025-11-19T14:30:45",
            "date": "19/11/2025",
            "time": "14:30:45",
            "day_of_week": "Terça-feira",
            "timezone": "America/Sao_Paulo"
        }
    """
    logger.info("[TOOL] get_current_datetime called")

    try:
        from datetime import datetime

        # Get current datetime
        now = datetime.now()

        # Brazilian weekday names
        weekday_names = [
            "Segunda-feira",
            "Terça-feira",
            "Quarta-feira",
            "Quinta-feira",
            "Sexta-feira",
            "Sábado",
            "Domingo",
        ]

        result = {
            "datetime": now.isoformat(),
            "date": now.strftime("%d/%m/%Y"),
            "time": now.strftime("%H:%M:%S"),
            "day_of_week": weekday_names[now.weekday()],
            "timezone": "America/Sao_Paulo",
        }

        logger.info(
            f"Current datetime: {result['date']} {result['time']} ({result['day_of_week']})"
        )
        return result

    except Exception as e:
        logger.exception(f"Error in get_current_datetime: {e}")
        return {"error": "internal_error", "message": "Failed to get current datetime"}


@tool
def create_reminder(
    user_id: str, reminder_message: str, priority: str = "normal"
) -> Dict[str, Any]:
    """
    Create a follow-up reminder for customer support to take action.

    Use this tool when:
    - The customer requests a callback
    - An issue needs follow-up
    - A document needs to be reviewed
    - Any action requires future attention

    Args:
        user_id (str): The unique identifier of the customer
        reminder_message (str): Description of the follow-up action needed
        priority (str): Priority level - "normal", "high", or "urgent" (default: "normal")

    Returns:
        Dict[str, Any]: Result containing:
            - success: True if reminder was created
            - reminder_id: ID of the created reminder
            - message: Confirmation message

    Example:
        >>> create_reminder("client789", "Revisar documentos para aumento de limite", "high")
        {
            "success": True,
            "reminder_id": 42,
            "message": "Reminder created successfully with priority: high"
        }
    """
    logger.info(
        f"[TOOL] create_reminder called for user_id: {user_id}, priority: {priority}"
    )

    # Input validation
    if not user_id or not isinstance(user_id, str):
        return {
            "error": "invalid_input",
            "message": "user_id must be a non-empty string",
        }

    if not reminder_message or not isinstance(reminder_message, str):
        return {
            "error": "invalid_input",
            "message": "reminder_message must be a non-empty string",
        }

    if len(reminder_message) > 1000:
        return {
            "error": "invalid_input",
            "message": "reminder_message too long (max 1000 characters)",
        }

    # Validate priority
    valid_priorities = ["normal", "high", "urgent"]
    if priority not in valid_priorities:
        logger.warning(f"Invalid priority '{priority}', defaulting to 'normal'")
        priority = "normal"

    try:
        db = get_database_service()

        # Current timestamp
        created_at = datetime.now().isoformat()

        # Calculate due date (1 day for normal, 4 hours for high, 1 hour for urgent)
        if priority == "urgent":
            due_date = (datetime.now() + timedelta(hours=1)).isoformat()
        elif priority == "high":
            due_date = (datetime.now() + timedelta(hours=4)).isoformat()
        else:
            due_date = (datetime.now() + timedelta(days=1)).isoformat()

        # Secure INSERT query
        query = """
            INSERT INTO reminders (user_id, message, priority, status, created_at, due_date)
            VALUES (?, ?, ?, 'pending', ?, ?)
        """

        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                db.execute_write,
                query,
                (user_id, reminder_message, priority, created_at, due_date),
            )
            rows_affected = future.result(timeout=3.0)

        if rows_affected > 0:
            logger.info(
                f"Successfully created reminder for {user_id} with priority {priority}"
            )
            return {
                "success": True,
                "message": f"Reminder created successfully with priority: {priority}",
                "due_date": due_date,
            }
        else:
            logger.error(f"Failed to create reminder for {user_id}")
            return {"error": "write_failed", "message": "Failed to create reminder"}

    except FuturesTimeoutError:
        logger.error(f"create_reminder timed out for user_id: {user_id}")
        return {"error": "timeout", "message": "Database operation timed out"}
    except Exception as e:
        logger.exception(f"Error in create_reminder: {e}")
        return {"error": "internal_error", "message": "Failed to create reminder"}


# ============================================================================
# TOOL REGISTRY
# ============================================================================

# Export all tools for the CustomerAgent
customer_agent_tools = [
    get_account_balance,
    get_user_profile,
    get_transaction_history,
    get_failed_transactions,
    check_payment_limits,
    get_current_datetime,
    create_reminder,
]
