"""
The "Toolbox" for the Customer Department.

These are the "CERTO" (safe) tool functions that the Customer Agent can call.
They accept the *real* `user_id` (passed down from the MainState).

We use specific tools instead of a generic Text2SQL tool to:
1.  **Ensure Security:** Prevent SQL injection or data deletion.
2.  **Ensure Performance:** Use optimized, pre-written queries.
3.  **Ensure Maintainability:** Decouple agent logic from database schema.

(For this challenge, the *backend* logic is stubbed/faked with a dict,
but the *tool interface* is real.)
"""
from langchain_core.tools import tool
import logging

# --- Simulated Database (Our "Stubbed" Backend) ---
FAKE_DB = {
    "client789": {
        "name": "Teodoro",
        "status": "Active",
        "last_login": "2025-11-13",
        "balance": 150.75,
        "recent_transfers": [
            {"id": "t_abc", "status": "Failed (Code 51: Insufficient Funds)"},
            {"id": "t_xyz", "status": "Completed"},
        ]
    },
    "client123": {
        "name": "Claudio",
        "status": "Blocked (Security Check)",
        "balance": 0.00,
        "recent_transfers": []
    }
}
# ---------------------------------------------------


@tool
def get_user_status(user_id: str) -> dict:
    """
    Fetches the account status (e.g., 'Active', 'Blocked') for a given user_id.
    """
    logging.info(f"Tool `get_user_status` called with user_id: {user_id}")
    
    # In production, this would be a secure SQL query:
    # "SELECT name, status FROM users WHERE user_id = :id"
    client_data = FAKE_DB.get(user_id)
    
    if not client_data:
        return {"error": "User ID not found."}
    
    return {
        "user_id": user_id,
        "name": client_data["name"],
        "status": client_data["status"]
    }

@tool
def check_transfer_status(user_id: str) -> dict:
    """
    Checks the status of the most recent transfers for a given user_id.
    Use this to answer why a transfer might have failed.
    """
    logging.info(f"Tool `check_transfer_status` called with user_id: {user_id}")
    
    # In production, this would be a secure SQL query:
    # "SELECT id, status FROM transfers WHERE user_id = :id ORDER BY date DESC LIMIT 3"
    client_data = FAKE_DB.get(user_id)
    
    if not client_data:
        return {"error": "User ID not found."}
    
    if not client_data["recent_transfers"]:
        return {"user_id": user_id, "transfers": "No recent transfers found."}
    
    return {
        "user_id": user_id,
        "recent_transfers": client_data["recent_transfers"]
    }

@tool
def set_reminder(user_id: str, reminder_message: str) -> str:
    """
    Sets a reminder for a follow-up action for a customer.
    Use this if the agent needs to promise a future action.
    """
    logging.info(f"Tool `set_reminder` called for user_id: {user_id}")
    
    # In production, this would write to a message queue or a 'reminders' table.
    
    return f"Success: Reminder set for user {user_id} with message: '{reminder_message}'"


# --- The Final Toolbox ---
# This is the list our Customer Agent's Sub-Graph will use.
customer_agent_tools = [get_user_status, check_transfer_status, set_reminder]