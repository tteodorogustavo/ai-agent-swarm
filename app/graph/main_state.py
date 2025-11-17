"""
Defines the Main State Schema for the "CEO" (Main Graph).

This is the "Master Clipboard" for the entire application.
It is kept simple and only contains information relevant for
high-level routing and final response aggregation.

It does NOT contain the internal, complex state of any single agent.
(e.g., it does not know about the KnowledgeAgent's "QC Loop").
"""

from typing import TypedDict, Annotated, List, Optional
from langchain_core.messages import BaseMessage
import operator

# We import the "RAG Analysis Form" because the "CEO" needs to
# pass this form from the "Router" to the "Knowledge Department".
from app.agents.knowledge_agent.query_schema import QueryAnalysis 

class MainState(TypedDict):
    """
    The master state for the main orchestration graph ("The CEO's Clipboard").
    """
    
    # --- 1. Core Conversation (Input/Output) ---
    messages: Annotated[List[BaseMessage], operator.add]
    """
    The master conversation history. This is the single source of truth.
    - Input (from User): The first node (`Router`) reads this.
    - Output (to User): The final `AIMessage` from the `SynthesisAgent` is ADDED here.
    - `operator.add` ensures it's a running history.
    """

    user_id: str
    """
    The unique identifier for the client (e.g., 'client789').
    - Input (from User): Set by the API (`chat_router.py`).
    - Internal: Read by the `MainGraph` and passed as *input* to the `CustomerAgent`.
    """

    # --- 2. Internal Orchestration ---
    route: str
    """
    The "Next Step" decision.
    - Written by: `RouterAgent`.
    - Read by: `builder.py` (the MainGraph's conditional logic) to decide
      which "Department" (Sub-Graph) to call next.
    """

    # --- 3. Evidence Collection (Internal) ---
    final_context: Annotated[List[str], operator.add]
    """
    The final "Evidence Box" for the "Porta-Voz".
    - Written by: The `KnowledgeAgent` AND the `CustomerAgent` (they deposit
      their `final_evidence` here).
    - Read by: `SynthesisAgent`.
    - `operator.add` is CRITICAL: it ensures if *both* agents run,
      their evidence is *combined*, not overwritten.
    """

    # --- 4. Final Output ---
    final_response: str
    """
    The final, polished answer for the user.
    - Written by: `SynthesisAgent`.
    - Read by: `API` (`chat_router.py`) to send the JSON response.
    """