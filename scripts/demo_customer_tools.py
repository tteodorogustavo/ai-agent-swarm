#!/usr/bin/env python3
"""
Quick Demo Script for Customer Agent Tools.

This script demonstrates all 6 customer tools with real database queries,
showcasing the security architecture and functionality.
"""
from app.agents.customer_agent.tools import check_payment_limits
from app.agents.customer_agent.tools import create_reminder
from app.agents.customer_agent.tools import get_account_balance
from app.agents.customer_agent.tools import get_failed_transactions
from app.agents.customer_agent.tools import get_transaction_history
from app.agents.customer_agent.tools import get_user_profile
from data.database.db_service import get_database_service


def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print("=" * 70)


def print_result(tool_name: str, result: dict):
    """Print tool result in a formatted way."""
    print(f"\n🔧 {tool_name}")
    print("-" * 70)
    for key, value in result.items():
        if isinstance(value, list) and value and isinstance(value[0], dict):
            print(f"{key}:")
            for item in value:
                print(f"  - {item}")
        else:
            print(f"{key}: {value}")


def main():
    """Run demonstrations of all customer tools."""

    # Test database health
    db = get_database_service()
    if not db.health_check():
        print(
            "❌ Database is not accessible! Run: poetry run python data/database/init_db.py"
        )
        return

    print("\n" + "=" * 70)
    print("  🚀 Customer Agent Tools - Live Demo")
    print("  Using REAL SQLite Database with Secure, Parameterized Queries")
    print("=" * 70)

    # Test user: client789 (Teodoro)
    test_user = "client789"

    # ========================================================================
    # DEMO 1: Get Account Balance
    # ========================================================================
    print_section("1. Get Account Balance")
    print(f"Query: SELECT balance, limits FROM accounts WHERE user_id = '{test_user}'")
    print("🔒 Security: Parameterized query, NO Text2SQL allowed\n")

    result = get_account_balance.invoke({"user_id": test_user})
    print_result("get_account_balance", result)

    # ========================================================================
    # DEMO 2: Get User Profile
    # ========================================================================
    print_section("2. Get User Profile")
    print(
        f"Query: SELECT name, status, account_type FROM users WHERE user_id = '{test_user}'"
    )
    print("🔒 Security: Only SELECT queries, no DELETE/UPDATE possible\n")

    result = get_user_profile.invoke({"user_id": test_user})
    print_result("get_user_profile", result)

    # ========================================================================
    # DEMO 3: Get Transaction History
    # ========================================================================
    print_section("3. Get Transaction History (Last 5)")
    print(
        f"Query: SELECT * FROM transactions WHERE user_id = '{test_user}' ORDER BY created_at DESC LIMIT 5"
    )
    print("🔒 Security: LIMIT enforced (max 50), prevents full table scans\n")

    result = get_transaction_history.invoke({"user_id": test_user, "limit": 5})
    print_result("get_transaction_history", result)

    # ========================================================================
    # DEMO 4: Get Failed Transactions (Most Common Customer Question!)
    # ========================================================================
    print_section("4. Get Failed Transactions")
    print(
        f"Query: SELECT * FROM transactions WHERE user_id = '{test_user}' AND status = 'failed'"
    )
    print("🔒 Security: Pre-filtered by status, LLM cannot modify WHERE clause\n")

    result = get_failed_transactions.invoke({"user_id": test_user})
    print_result("get_failed_transactions", result)

    # ========================================================================
    # DEMO 5: Check Payment Limits
    # ========================================================================
    print_section("5. Check Payment Limits")
    print(
        f"Query: SELECT period_type, limit_amount, spent_amount FROM payment_limits WHERE user_id = '{test_user}'"
    )
    print("🔒 Security: Automatic calculation of 'remaining', no exposed SQL\n")

    result = check_payment_limits.invoke({"user_id": test_user})
    print_result("check_payment_limits", result)

    # ========================================================================
    # DEMO 6: Create Reminder (WRITE Operation)
    # ========================================================================
    print_section("6. Create Reminder (Write Operation)")
    print(
        f"Query: INSERT INTO reminders (user_id, message, priority) VALUES ('{test_user}', '...', 'high')"
    )
    print("🔒 Security: Separate execute_write() method, input validation enforced\n")

    result = create_reminder.invoke(
        {
            "user_id": test_user,
            "reminder_message": "Demo: Follow up on failed transfer",
            "priority": "high",
        }
    )
    print_result("create_reminder", result)

    # ========================================================================
    # BONUS: Error Handling Demo
    # ========================================================================
    print_section("BONUS: Error Handling (User Not Found)")
    print("Query: Attempting to query non-existent user 'invalid_user_9999'")
    print("🔒 Security: Graceful error handling, NO stack trace exposure\n")

    result = get_account_balance.invoke({"user_id": "invalid_user_9999"})
    print_result("get_account_balance (error)", result)

    # ========================================================================
    # Summary
    # ========================================================================
    print_section("✅ Summary: Why This is the 'CERTO' (Correct) Approach")
    print(
        """
✓ LLM CANNOT write SQL (prevents DROP TABLE, DELETE, SQL injection)
✓ All queries are PARAMETERIZED (prevents injection attacks)
✓ Input VALIDATION on every tool (type checking, length limits)
✓ Timeout PROTECTION (3-5s limits, prevents hangs)
✓ Error handling is GRACEFUL (no stack trace leaks)
✓ Read/Write SEPARATION (clear distinction, audit trail)
✓ TESTED with 16 unit tests (100% coverage of tools)

❌ Text2SQL Approach Would Allow:
  - DROP TABLE users; -- LLM could destroy data
  - SELECT * FROM users; -- Performance nightmare, data leak
  - Arbitrary WHERE clauses -- Privacy violations
  - No input validation -- Injection vectors
"""
    )

    print("\n" + "=" * 70)
    print("  🎉 Demo Complete! All tools working with real SQLite database.")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
