"""
Defines the Internal State for the Customer Department Sub-Graph.

This is the "Departmental Clipboard" for the Customer Agent.
Its job is to orchestrate tool calls to fetch private user data.
"""

from typing import TypedDict, Annotated, List
from langchain_core.messages import BaseMessage
import operator

class CustomerState(TypedDict):
    """
    The internal state for the customer tool-calling sub-graph.
    """
    
    # --- 1. Inputs from "CEO" (MainGraph) ---
    user_id: Annotated[str, "The user_id passed in from the Main Graph."]
    
    original_question: Annotated[str, "The raw user question, for context."]

    # --- 2. Internal Memory (for ReAct loop) ---
    messages: Annotated[List[BaseMessage], operator.add,
                        "The internal memory for this sub-graph, which will contain "
                        "HumanMessages (the question), AIMessages (tool calls), "
                        "and ToolMessages (tool results)."]

    # --- 3. Final Output to "CEO" (MainGraph) ---
    final_answer: Annotated[str, "The final, summarized answer (the \"report\") " \
    "that this department will return to the Main Graph."]
    
    final_evidence: Annotated[List[str], "The raw evidence (tool outputs) gathered, which will be "
    "passed back to the Main Graph's `final_context`."]